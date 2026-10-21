"""The routes that connect a jurisdiction's source from the workbench and test it.

A document API or an MCP server is mapped from one search and one fetch, each field picked
from real values; a provider's profile is checked and copied; any source is tested alone
(decisions 0033, 0043, 0065).
"""

import os
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import click
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from casebench import keys, network
from casebench.config import CasebenchConfig, ConfigError, config_from
from casebench.corpus.add import name_for
from casebench.corpus.bundled import bundled
from casebench.corpus.from_profile import ProfileProblem, profile_block
from casebench.perimeter import enforce
from casebench.setup.checks import SETUP_SAMPLE, Check, Status, live, unreachable
from casebench.workbench import connect_source
from casebench.workbench.connect_source import Picked
from casebench.workbench.settings import Settings

# The name a source is tested under; it is never saved.
TRIED = "tried"
# A profile file is YAML (decision 0033).
PROFILE_SUFFIXES = (".yaml", ".yml")
# Enough of a value to recognise it in a list; the list scrolls, the value does not wrap.
SHOWN = 160


class Tested(BaseModel):
    part: str
    status: str
    passed: bool
    reason: str
    next: str


class SourceTry(BaseModel):
    block: dict[str, Any] = Field(description="A corpus block, as casebench.yaml writes it.")
    probe: str | None = Field(default=None, description="A search that finds a document.")


class Picks(BaseModel):
    probe: str = Field(min_length=1, description="A search that finds at least one document.")
    jurisdictions: list[str] = Field(default_factory=list)
    result_fields: dict[str, str] = Field(
        default_factory=dict, description="Picked in a search result: id, citation, type, passage."
    )
    fields: dict[str, str] = Field(default_factory=dict, description="Picked in a document.")


class ApiSource(Picks):
    base_url: str = Field(min_length=1)
    search_path: str = Field(min_length=1)
    fetch_path: str = Field(min_length=1, description="With {id} where a document's id goes.")
    query_param: str = "q"
    key_env: str | None = Field(default=None, description="The variable the key is read from.")
    key_header: str = "Authorization"
    search_body: dict[str, Any] | None = Field(
        default=None, description="For a search by POST: its JSON body, with {text}."
    )


class McpReach(BaseModel):
    command: str | None = Field(default=None, description="The command that starts the server.")
    url: str | None = Field(default=None, description="The server's URL.")


class McpSource(McpReach, Picks):
    search_tool: str = Field(min_length=1)
    search_arg: str = "query"
    fetch_tool: str = Field(min_length=1)
    fetch_arg: str = "id"


class Tool(BaseModel):
    name: str
    description: str


class Leaf(BaseModel):
    path: str
    value: str


class Connected(BaseModel):
    name: str = Field(description="A name for the source no other source has.")
    results: str | None = Field(description="Where each result is in a search response.")
    result_choices: list[Leaf] = Field(description="A search result's fields, to pick from.")
    document_choices: list[Leaf] = Field(description="A document's fields, to pick from.")
    fields: dict[str, str] = Field(description="Where the document's fields are, as suggested.")
    missing: list[str] = Field(description="Fields a check needs that no path finds.")
    block: dict[str, Any] | None = Field(description="The corpus block, once a fetch worked.")


class ProfileView(BaseModel):
    id: str
    name: str
    jurisdictions: list[str]
    key_env: str | None
    key_found: bool
    docs: str | None
    terms: str | None


class ProfileAsked(BaseModel):
    given: str = Field(min_length=1, description="A bundled profile's id, or a profile file.")
    jurisdictions: list[str] = Field(default_factory=list)


class FromProfile(BaseModel):
    name: str
    block: dict[str, Any]
    notes: list[str] = Field(description="What the check found, and the provider's terms.")


def shown(check: Check) -> Tested:
    return Tested(
        part=check.name,
        status=check.status.value,
        passed=check.status is Status.PASSED,
        reason=keys.scrub(check.detail),
        next=check.next if check.status is not Status.PASSED else "",
    )


def _leaves(found: list[tuple[str, Any]]) -> list[Leaf]:
    """Each value cut to what a person reads to recognise it."""
    return [Leaf(path=path, value=" ".join(str(value).split())[:SHOWN]) for path, value in found]


@contextmanager
def _reaching(block: dict[str, Any] | None) -> Iterator[None]:
    """Calls to the store alone, inside its own perimeter when its address is known before
    anything is read; a failure says why in plain words."""
    if block is not None:
        enforce(CasebenchConfig.model_validate({"corpora": {TRIED: block}}))
    try:
        yield
    except (click.ClickException, ProfileProblem) as error:
        said = error.format_message() if isinstance(error, click.ClickException) else str(error)
        raise HTTPException(422, keys.scrub(said)) from None
    except Exception as error:
        where = "not reachable from here" if unreachable(error) else "did not answer as expected"
        raise HTTPException(502, keys.scrub(f"the source is {where}: {error}")) from None
    finally:
        network.release()


def _profile_in(folder: Path, given: str) -> tuple[Path, str]:
    """A bundled profile by its id, or a profile file inside the project; a request never
    names a file anywhere else on the machine."""
    for item in bundled():
        if item.id == given:
            return item.path, item.id
    root = os.path.realpath(folder)
    found = os.path.realpath(os.path.join(root, given))
    if not found.startswith(root + os.sep) or not found.endswith(PROFILE_SUFFIXES):
        raise HTTPException(422, "a profile is a bundled id, or a .yaml file in this project")
    if not os.path.isfile(found):
        raise HTTPException(422, f"there is no profile file {given} in this project")
    return Path(found), Path(found).name


def _address(kind: str, options: dict[str, Any]) -> dict[str, Any]:
    """The part of a source's block that says which host it calls."""
    named = {key: options[key] for key in ("base_url", "url") if options.get(key)}
    return {"connector": kind, "options": named}


def router(settings: Settings, folder: Path, engineer: Callable[..., str]) -> APIRouter:
    """`folder` is the project the workbench was started in; `engineer` names a caller who may
    use the engineering view."""
    routes = APIRouter()

    def taken() -> list[str]:
        return list((settings.sections().get("corpora") or {}).keys())

    def connected(kind: str, options: dict[str, Any], body: Picks) -> Connected:
        picked = Picked(body.probe, body.jurisdictions, body.result_fields, body.fields)
        with _reaching(_address(kind, options)):
            looked = connect_source.look(kind, options, picked)
        return Connected(
            name=name_for(looked.block or {"connector": kind, "options": options}, taken()),
            results=looked.results,
            result_choices=_leaves(looked.result_choices),
            document_choices=_leaves(looked.document_choices),
            fields=looked.fields,
            missing=looked.missing,
            block=looked.block,
        )

    @routes.post("/api/setup/sources/test")
    def test_source(body: SourceTry, name: str = Depends(engineer)) -> Tested:
        base = settings.path.resolve().parent if settings.path else folder
        try:
            config = config_from({"corpora": {TRIED: body.block}}, base, "casebench.yaml")
        except ConfigError as error:
            raise HTTPException(422, keys.scrub(str(error))) from None
        current = settings.config
        within = config.model_copy(update={"network": current.network if current else None})
        probe = body.probe or config.corpora[TRIED].probe
        enforce(within)
        try:
            (found,) = live(within, [probe] if probe else None, SETUP_SAMPLE)
        finally:
            network.release()
        return shown(found)

    @routes.post("/api/setup/sources/api")
    def connect_api(body: ApiSource, name: str = Depends(engineer)) -> Connected:
        with _reaching(_address("http", {"base_url": body.base_url})):
            options = connect_source.api_options(
                body.base_url,
                body.search_path,
                body.fetch_path,
                body.query_param,
                body.key_env or None,
                body.key_header,
                body.search_body,
            )
        return connected("http", options, body)

    @routes.post("/api/setup/sources/mcp/tools")
    def mcp_tools(body: McpReach, name: str = Depends(engineer)) -> list[Tool]:
        """The server's tools, so a person picks the one that searches and the one that fetches."""
        with _reaching(_address("mcp", {"url": body.url})):
            reached = connect_source.reach(body.command, body.url)
            found = connect_source.tools(reached)
        return [Tool(name=tool, description=said) for tool, said in found]

    @routes.post("/api/setup/sources/mcp")
    def connect_mcp(body: McpSource, name: str = Depends(engineer)) -> Connected:
        with _reaching(None):
            reached = connect_source.reach(body.command, body.url)
        options = connect_source.mcp_options(
            reached, body.search_tool, body.search_arg, body.fetch_tool, body.fetch_arg
        )
        return connected("mcp", options, body)

    @routes.get("/api/setup/profiles")
    def profiles(name: str = Depends(engineer)) -> list[ProfileView]:
        """The profiles bundled with Casebench, by name and nothing else (decision 0033)."""
        return [
            ProfileView(
                id=item.id,
                name=item.profile.name,
                jurisdictions=list(item.profile.jurisdictions),
                key_env=item.profile.key_env,
                key_found=item.key_found,
                docs=item.profile.docs,
                terms=item.profile.terms,
            )
            for item in bundled()
        ]

    @routes.post("/api/setup/sources/profile")
    def from_profile(body: ProfileAsked, name: str = Depends(engineer)) -> FromProfile:
        """One live search and fetch prove the profile works with the key here (0033)."""
        path, recorded = _profile_in(folder, body.given)
        # The profile names its own address, read only once it is loaded (decision 0033).
        with _reaching(None):
            block, notes = profile_block(path, body.jurisdictions or None, recorded)
        return FromProfile(name=name_for(block, taken()), block=block, notes=notes)

    return routes
