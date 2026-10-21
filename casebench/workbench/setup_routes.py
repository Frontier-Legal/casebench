"""The routes the workbench's setup guide and its Models page call, besides its sources'.

They read the project as `casebench init` reads it, with the agent's models priced from the
model catalog, list the jurisdiction codes casebench.yaml takes, and test one model alone.
Saving goes through the Settings page's sections (decisions 0063, 0065).
"""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx2
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from casebench import keys, network
from casebench.config import CasebenchConfig, ConfigError, config_from
from casebench.core.jurisdiction import COUNTRIES, EU
from casebench.perimeter import enforce
from casebench.setup import catalog as model_catalog
from casebench.setup.checks import SETUP_SAMPLE, live
from casebench.setup.scan import scan
from casebench.workbench.catalog_cache import CatalogCache
from casebench.workbench.settings import Settings
from casebench.workbench.source_routes import Tested, shown


class ScanView(BaseModel):
    """What the code scan found, by name and place; no variable's value is read."""

    said: str
    entries: list[str] = Field(description="Functions Casebench can call with a question.")
    clients: list[str] = Field(description="Each model or search client, as kind at file:line.")
    models: list[str] = Field(description="Model names written in the code.")


class AgentModel(BaseModel):
    model: str
    family: str
    price: dict[str, float] | None = Field(
        default=None, description="US dollars per million input and output tokens."
    )


class ModelTry(BaseModel):
    block: dict[str, Any] = Field(description="A judge or extraction model's block.")


def _refused(error: Exception) -> HTTPException:
    return HTTPException(422, keys.scrub(str(error)))


def router(
    settings: Settings, folder: Path, engineer: Callable[..., str], catalog: CatalogCache
) -> APIRouter:
    """`folder` is the project the workbench was started in; `engineer` names a caller who may
    use the engineering view."""
    routes = APIRouter()

    def config_of(data: dict[str, Any]) -> CasebenchConfig:
        """A part read as casebench.yaml would read it, its paths relative to the file."""
        base = settings.path.resolve().parent if settings.path else folder
        try:
            return config_from(data, base, "casebench.yaml")
        except ConfigError as error:
            raise _refused(error) from None

    def checked(config: CasebenchConfig, queries: list[str] | None = None) -> Tested:
        """The one live check the config calls for, inside its own perimeter (0046)."""
        current = settings.config
        within = config.model_copy(update={"network": current.network if current else None})
        enforce(within)
        try:
            (found,) = live(within, queries, SETUP_SAMPLE)
        finally:
            network.release()
        return shown(found)

    @routes.get("/api/setup/scan")
    def read_project(name: str = Depends(engineer)) -> ScanView:
        found = scan(folder)
        return ScanView(
            said=found.said(),
            entries=found.entries,
            clients=[f"{client.kind} at {client.where}" for client in found.clients],
            models=sorted({model.name for model in found.models}),
        )

    @routes.get("/api/setup/agent-models")
    def agent_models(name: str = Depends(engineer)) -> list[AgentModel]:
        """The models the agent's code names, with the family and price the catalog gives
        them, as `casebench init` writes them (decisions 0047, 0051)."""
        names = [model.name for model in scan(folder).models]
        if not names:
            return []
        try:
            listed = catalog.get()
        except httpx2.HTTPError as error:
            said = f"the model catalog could not be fetched: {error}"
            raise HTTPException(502, said) from None
        return [AgentModel(**found) for found in model_catalog.agent_models(listed, names)]

    @routes.get("/api/setup/jurisdictions")
    def jurisdictions(name: str = Depends(engineer)) -> list[str]:
        """Every code casebench.yaml takes for a whole country, and the Union's."""
        return [*sorted(COUNTRIES), EU]

    @routes.post("/api/setup/models/test")
    def test_model(body: ModelTry, name: str = Depends(engineer)) -> Tested:
        """The model alone, asked once with its settings, as `casebench check` asks it."""
        return checked(config_of({"judges": [body.block]}))

    return routes
