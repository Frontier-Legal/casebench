"""The Settings page's routes, which read and change casebench.yaml from the workbench.

They save a section or the whole file, set a key, check the setup, and pick a model from the
catalog (decision 0063).
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx2
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from casebench import keys, network
from casebench.perimeter import enforce
from casebench.setup import catalog as model_catalog
from casebench.setup.checks import Status, live, offline
from casebench.workbench import keyfile, settings_view
from casebench.workbench.catalog_cache import CatalogCache
from casebench.workbench.settings import Refused, Settings
from casebench.workbench.sources import Workspace
from casebench.workbench.store import Store


class Section(BaseModel):
    value: Any = Field(description="The section as casebench.yaml writes it; null removes it.")


class FileText(BaseModel):
    text: str = Field(max_length=1_000_000)


class KeyValue(BaseModel):
    value: str = Field(min_length=1, max_length=10_000)


class CheckView(BaseModel):
    part: str
    status: str
    passed: bool
    reason: str
    next: str


class CatalogProvider(BaseModel):
    id: str
    name: str
    models: int


class CatalogModel(BaseModel):
    id: str
    name: str
    family: str | None
    price_input: float | None
    price_output: float | None
    context_window: int | None
    max_output: int | None


class PickModel(BaseModel):
    provider: str
    model: str
    plugin: str | None = None


class Picked(BaseModel):
    block: dict[str, Any] | None = Field(description="The model's settings, ready to save.")
    missing: list[str] = Field(description="Options the catalog lacks, such as base_url.")
    plugins: list[str] = Field(description="When no installed plugin claims the provider's API.")


def router(
    settings: Settings,
    workspace: Workspace,
    store: Store,
    engineer: Callable[..., str],
    catalog: CatalogCache,
) -> APIRouter:
    """`engineer` is the dependency that names a caller who may use the engineering view."""
    routes = APIRouter()

    def shown(name: str) -> settings_view.SettingsView:
        return settings_view.view(settings, workspace, store, name)

    @routes.get("/api/settings")
    def read(name: str = Depends(engineer)) -> settings_view.SettingsView:
        return shown(name)

    @routes.put("/api/settings/sections/{section}")
    def save_section(
        section: str, body: Section, name: str = Depends(engineer)
    ) -> settings_view.SettingsView:
        try:
            settings.save_section(section, body.value)
        except Refused as refused:
            raise HTTPException(422, keys.scrub(str(refused))) from None
        return shown(name)

    @routes.put("/api/settings/file")
    def save_file(body: FileText, name: str = Depends(engineer)) -> settings_view.SettingsView:
        try:
            settings.save_text(body.text)
        except Refused as refused:
            raise HTTPException(422, keys.scrub(str(refused))) from None
        return shown(name)

    @routes.put("/api/settings/keys/{key}")
    def set_key(
        key: str, body: KeyValue, name: str = Depends(engineer)
    ) -> settings_view.SettingsView:
        """The value is written to a git-ignored file and never sent back."""
        if settings.path is None:
            raise HTTPException(422, "this workbench reads no casebench.yaml")
        base = settings.path.resolve().parent
        named = dict(settings.sections().get("keys") or {})
        try:
            file = keyfile.write(key, body.value, named, base)
            if named.get(key) != file:
                settings.save_section("keys", {**named, key: file})
            else:
                settings.reload()
        except (keyfile.Refused, Refused) as refused:
            raise HTTPException(422, str(refused)) from None
        return shown(name)

    @routes.post("/api/settings/check")
    def check(name: str = Depends(engineer)) -> list[CheckView]:
        """`casebench check`: it calls the agent, the judge and the corpus once each."""
        config = settings.config
        if config is None:
            raise HTTPException(422, "there is no casebench.yaml to check; run casebench init")
        enforce(config)
        try:
            root = settings.path.resolve().parent if settings.path else Path(".")
            found = offline(config) or live(config, root=root)
        finally:
            network.release()
        return [
            CheckView(
                part=item.name,
                status=item.status.value,
                passed=item.status is Status.PASSED,
                reason=keys.scrub(item.detail),
                next=item.next if item.status is not Status.PASSED else "",
            )
            for item in found
        ]

    def entries() -> dict[str, Any]:
        """The public model catalog, fetched once and shared with the setup pages (0032)."""
        try:
            return catalog.get()
        except httpx2.HTTPError as error:
            raise HTTPException(502, f"the model catalog could not be fetched: {error}") from None

    @routes.post("/api/settings/catalog/warm", status_code=202)
    def warm(name: str = Depends(engineer)) -> None:
        """A setup page opened: fetch the catalog now, so the picker opens with it (0065)."""
        catalog.warm()

    @routes.get("/api/settings/catalog")
    def providers(name: str = Depends(engineer)) -> list[CatalogProvider]:
        found = [
            CatalogProvider(
                id=key, name=entry.get("name") or key, models=len(entry.get("models") or {})
            )
            for key, entry in entries().items()
        ]
        return sorted(found, key=lambda p: p.name.casefold())

    @routes.get("/api/settings/catalog/{provider}")
    def provider_models(provider: str, name: str = Depends(engineer)) -> list[CatalogModel]:
        entry = entries().get(provider)
        if entry is None:
            raise HTTPException(404, f"the model catalog has no provider {provider!r}")
        found = []
        for key, model in (entry.get("models") or {}).items():
            cost, limit = model.get("cost") or {}, model.get("limit") or {}
            found.append(
                CatalogModel(
                    id=key,
                    name=model.get("name") or key,
                    family=model.get("family"),
                    price_input=cost.get("input"),
                    price_output=cost.get("output"),
                    context_window=limit.get("context"),
                    max_output=limit.get("output"),
                )
            )
        return sorted(found, key=lambda m: m.name.casefold())

    @routes.post("/api/settings/catalog/model")
    def pick(body: PickModel, name: str = Depends(engineer)) -> Picked:
        """A model's settings as init writes them, from its catalog entry (decision 0032)."""
        entry = entries().get(body.provider)
        if entry is None:
            raise HTTPException(404, f"the model catalog has no provider {body.provider!r}")
        provider = {"id": body.provider, **entry}
        model = {"id": body.model, **((entry.get("models") or {}).get(body.model) or {})}
        plugin = body.plugin or next(iter(model_catalog.speakers(provider)), None)
        if plugin is None:
            return Picked(block=None, missing=[], plugins=model_catalog.plugins())
        try:
            serving = model_catalog.offer(plugin, provider, model)
        except Exception as error:
            raise HTTPException(422, str(error)) from None
        block = model_catalog.model_block(plugin, model, dict(serving.options))
        return Picked(block=block, missing=serving.missing, plugins=[])

    return routes
