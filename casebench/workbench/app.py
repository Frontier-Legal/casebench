"""The workbench's API and its web app, served on the loopback address (decision 0050)."""

from importlib import resources
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import unquote

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from casebench.workbench import items
from casebench.workbench.items import (
    AnswerItem,
    DecisionView,
    DraftItem,
    Finished,
    GivenFact,
    GivenVerdict,
    Highlight,
    NotFound,
    QueueItem,
    Refused,
)
from casebench.workbench.sources import Workspace
from casebench.workbench.store import Store

REVIEWER, ENGINEER = "reviewer", "engineer"
PERSON_HEADER = "X-Casebench-Person"
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
NOT_BUILT = """<!doctype html><meta charset="utf-8"><title>Casebench</title>
<p>The workbench's web app is not built. Run <code>npm ci && npm run build</code> in
<code>workbench/</code>, or install Casebench from PyPI, whose wheel carries it.</p>"""
SECURITY_HEADERS = {
    "Content-Security-Policy": "default-src 'self'; img-src 'self' data:; "
    "style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


def static_root() -> Path:
    return Path(str(resources.files("casebench.workbench") / "static"))


class Loopback(BaseHTTPMiddleware):
    """Answers only requests addressed to the hosts it serves, so a page elsewhere cannot reach
    it through DNS rebinding, and takes writes only from its own origin."""

    def __init__(self, app: Any, hosts: list[str]) -> None:
        super().__init__(app)
        self.hosts = set(hosts)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.headers.get("host") not in self.hosts:
            return JSONResponse({"detail": "this host is not served here"}, status_code=403)
        origin = request.headers.get("origin")
        if (
            request.method in UNSAFE
            and origin is not None
            and origin.removeprefix("http://") not in self.hosts
        ):
            return JSONResponse({"detail": "writes come only from this app"}, status_code=403)
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        return response


class Me(BaseModel):
    name: str
    view: Literal["review", "engineering"]
    role_locked: bool = Field(description="The app serves the review view only.")


class SaveMe(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    view: Literal["review", "engineering"] = "review"


class Session(BaseModel):
    role_locked: bool


class Queue(BaseModel):
    items: list[QueueItem]


class Held(BaseModel):
    held_by: str


class SaveDraft(BaseModel):
    payload: dict[str, Any]


class Finish(BaseModel):
    verdicts: list[GivenVerdict] = Field(default_factory=list)
    facts: list[GivenFact] = Field(default_factory=list)


class Document(DecisionView):
    highlight: Highlight | None = None


def person(named: Annotated[str | None, Header(alias=PERSON_HEADER)] = None) -> str:
    """Who is asking, as the app sends it, percent-encoded so any name fits a header."""
    name = unquote(named or "").strip()
    if not name:
        raise HTTPException(401, "say who you are first")
    return name


Person = Annotated[str, Depends(person)]


def create_app(
    workspace: Workspace,
    store: Store,
    hosts: list[str],
    role: str | None = None,
    static: Path | None = None,
) -> FastAPI:
    """`role` set to `reviewer` serves the review view only: no response carries engineering
    fields, whatever the browser asks for."""
    app = FastAPI(title="Casebench workbench", docs_url=None, redoc_url=None)
    app.add_middleware(Loopback, hosts=hosts)
    locked = role == REVIEWER

    def engineering(name: str) -> bool:
        found = store.person(name)
        return not locked and found is not None and found.view == "engineering"

    @app.get("/api/session")
    def session() -> Session:
        return Session(role_locked=locked)

    @app.get("/api/me")
    def me(name: Person) -> Me:
        found = store.person(name)
        if found is None:
            raise HTTPException(404, "no one by that name yet")
        view = "review" if locked else found.view
        return Me(name=found.name, view=view, role_locked=locked)  # type: ignore[arg-type]

    @app.put("/api/me")
    def save_me(body: SaveMe) -> Me:
        view = "review" if locked else body.view
        saved = store.save_person(body.name.strip(), view)
        return Me(name=saved.name, view=view, role_locked=locked)

    @app.get("/api/queue")
    def queue(name: Person) -> Queue:
        return Queue(items=items.queue(workspace, store, name))

    @app.get("/api/items/{key}")
    def item(key: str, name: Person) -> AnswerItem | DraftItem:
        try:
            return items.item(workspace, store, key, name, engineering(name))
        except NotFound as missing:
            raise HTTPException(404, str(missing)) from None

    @app.post("/api/items/{key}/reserve")
    def reserve(key: str, name: Person) -> Held:
        held = store.reserve(key, name)
        if held != name:
            raise HTTPException(409, f"{held} is working on this item")
        return Held(held_by=held)

    @app.put("/api/items/{key}/draft")
    def save_draft(key: str, body: SaveDraft, name: Person) -> Held:
        held = store.reserve(key, name)
        if held != name:
            raise HTTPException(409, f"{held} is working on this item")
        store.save_draft(key, name, body.payload)
        return Held(held_by=held)

    @app.post("/api/items/{key}/finish")
    def finish(key: str, body: Finish, name: Person) -> Finished:
        holder = store.holder(key)
        if holder is not None and holder != name:
            raise HTTPException(409, f"{holder} is working on this item")
        try:
            if key.startswith(f"{items.ANSWER}:"):
                return items.finish_answer(workspace, store, key, name, body.verdicts)
            return items.finish_draft(workspace, store, key, name, body.facts)
        except NotFound as missing:
            raise HTTPException(404, str(missing)) from None
        except Refused as refused:
            raise HTTPException(422, str(refused)) from None

    @app.get("/api/documents/{document_id}")
    def document(document_id: str, name: Person, quote: str | None = None) -> Document:
        record = workspace.decision(document_id)
        if record is None:
            raise HTTPException(404, "no configured corpus holds this document")
        found = items.find_quote(record.text, quote) if quote else None
        return Document(
            id=document_id,
            court=record.court,
            date=record.date.isoformat(),
            text=record.text,
            highlight=found,
        )

    root = static or static_root()
    index = root / "index.html"
    if (root / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=root / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def web_app(path: str) -> Response:
        if path.startswith("api/"):
            raise HTTPException(404, "no such endpoint")
        shipped = (root / path).resolve()
        if path and shipped.is_file() and shipped.is_relative_to(root.resolve()):
            return FileResponse(shipped)
        if index.is_file():
            return FileResponse(index)
        return HTMLResponse(NOT_BUILT)

    return app
