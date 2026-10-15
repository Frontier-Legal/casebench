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

from casebench.config import CasebenchConfig
from casebench.workbench import comparing, golden, harness, items, reports, trying
from casebench.workbench.golden import CaseDetail, ChangeItem, Form, Golden, Proposed
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
    decision: Literal["approve", "reject"] | None = Field(
        default=None, description="On a change to golden data (decision 0052)."
    )
    note: str | None = None


class Ask(BaseModel):
    question: str = Field(max_length=4000)


class SaveCase(BaseModel):
    fields: dict[str, str]
    reason: str = ""


class NewCase(BaseModel):
    task: str = "qa"
    fields: dict[str, str]
    reason: str | None = None


class Prefer(BaseModel):
    choice: Literal["a", "b", "equal"]
    reason: str = Field(default="", max_length=4000)


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
    config: CasebenchConfig | None = None,
    asker: trying.Asker | None = None,
) -> FastAPI:
    """`role` set to `reviewer` serves the review view only: no response carries engineering
    fields, whatever the browser asks for."""
    app = FastAPI(title="Casebench workbench", docs_url=None, redoc_url=None)
    app.add_middleware(Loopback, hosts=hosts)
    locked = role == REVIEWER
    # Whether a change to golden data waits for a second editor (decision 0053).
    second = bool(config and config.workbench and config.workbench.second_approval)

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

    def editor() -> None:
        """A reviewer reviews answers and proposes no change to golden data (decision 0052)."""
        if locked:
            raise HTTPException(403, "the reviewer role proposes no change to golden data")

    @app.get("/api/queue")
    def queue(name: Person) -> Queue:
        queued = items.queue(workspace, store, name)
        if locked:
            return Queue(items=queued)
        held = store.held_by_others(name)
        waiting = [
            QueueItem(key=key, kind="change", title=title, where=where, task=task, flags=[flag])
            for key, title, where, task, flag in golden.queue_items(store, name, held)
        ]
        drafts = next((n for n, i in enumerate(queued) if i.kind == "draft"), len(queued))
        return Queue(items=[*queued[:drafts], *waiting, *queued[drafts:]])

    @app.get("/api/items/{key}")
    def item(key: str, name: Person) -> AnswerItem | DraftItem | ChangeItem:
        try:
            if key.startswith(f"{golden.CHANGE_ITEM}:"):
                editor()
                return golden.change_item(store, key, name)
            return items.item(workspace, store, key, name, engineering(name))
        except NotFound as missing:
            raise HTTPException(404, str(missing)) from None

    @app.get("/api/runs")
    def runs(name: Person) -> list[reports.RunRow]:
        return reports.runs(workspace)

    @app.get("/api/runs/{run_id}/report")
    def run_report(run_id: str, name: Person) -> reports.RunReport:
        """The run's error rates, each with its failing answers (decision 0054)."""
        try:
            return reports.run_report(workspace, run_id)
        except NotFound as missing:
            raise HTTPException(404, str(missing)) from None

    @app.get("/api/runs/{run_id}/export/{kind}")
    def export_report(run_id: str, kind: str, name: Person) -> Response:
        """The report for partners as HTML, PDF or DOCX, to download (decision 0054)."""
        try:
            content, media, file = reports.export(workspace, run_id, kind)
        except NotFound as missing:
            raise HTTPException(404, str(missing)) from None
        except Refused as refused:
            raise HTTPException(422, str(refused)) from None
        disposition = f'attachment; filename="{file}"'
        return Response(content, media_type=media, headers={"Content-Disposition": disposition})

    @app.get("/api/compare/{first}/{second}")
    def compare_runs(first: str, second: str, name: Person) -> comparing.Comparison:
        """Every pair of answers the two runs share, and the preferences so far (0054)."""
        try:
            return comparing.comparison(workspace, first, second)
        except NotFound as missing:
            raise HTTPException(404, str(missing)) from None
        except Refused as refused:
            raise HTTPException(422, str(refused)) from None

    @app.get("/api/compare/{first}/{second}/{case_id}/{repeat}")
    def compare_pair(
        first: str, second: str, case_id: str, repeat: int, name: Person
    ) -> comparing.Pair:
        try:
            return comparing.pair(workspace, first, second, case_id, repeat)
        except NotFound as missing:
            raise HTTPException(404, str(missing)) from None
        except Refused as refused:
            raise HTTPException(422, str(refused)) from None

    @app.post("/api/compare/{first}/{second}/{case_id}/{repeat}")
    def prefer(
        first: str, second: str, case_id: str, repeat: int, body: Prefer, name: Person
    ) -> comparing.Pair:
        try:
            return comparing.prefer(
                workspace, store, first, second, case_id, repeat, body.choice, body.reason, name
            )
        except NotFound as missing:
            raise HTTPException(404, str(missing)) from None
        except Refused as refused:
            raise HTTPException(422, str(refused)) from None

    @app.get("/api/harness/{run_id}/{case_id}/{repeat}")
    def harness_view(
        run_id: str, case_id: str, repeat: int, name: Person, against: str | None = None
    ) -> harness.Harness:
        """The engineering view's waterfall; the review view is never served it (0056)."""
        if not engineering(name):
            raise HTTPException(403, "the harness view is for the engineering view")
        try:
            return harness.harness(workspace, run_id, case_id, repeat, against)
        except NotFound as missing:
            raise HTTPException(404, str(missing)) from None
        except Refused as refused:
            raise HTTPException(422, str(refused)) from None

    @app.get("/api/try")
    def try_budget(name: Person) -> trying.Budget:
        return trying.budget(config, store)

    @app.post("/api/try")
    async def try_question(body: Ask, name: Person) -> trying.Tried:
        """Asks the configured target within the day's limit; refused, nothing is sent."""
        try:
            return await trying.try_question(
                body.question,
                name,
                config,
                store,
                asker or (trying.ConfiguredAsker(config) if config else None),
            )
        except trying.Refused as refused:
            raise HTTPException(422, str(refused)) from None

    @app.get("/api/golden")
    def golden_data(name: Person) -> Golden:
        return golden.golden(workspace, store, second)

    @app.get("/api/golden/forms/{task}")
    def blank_form(task: str, name: Person) -> list[Form]:
        try:
            return golden.blank_form(task)
        except NotFound as missing:
            raise HTTPException(404, str(missing)) from None

    @app.get("/api/golden/{suite_id}/{case_id}")
    def golden_case(suite_id: str, case_id: str, name: Person) -> CaseDetail:
        try:
            return golden.case_detail(workspace, store, suite_id, case_id)
        except NotFound as missing:
            raise HTTPException(404, str(missing)) from None

    @app.put("/api/golden/{suite_id}/{case_id}")
    def change_case(suite_id: str, case_id: str, body: SaveCase, name: Person) -> Proposed:
        editor()
        try:
            return golden.propose_change(
                workspace, store, suite_id, case_id, body.fields, body.reason, name, second
            )
        except NotFound as missing:
            raise HTTPException(404, str(missing)) from None
        except Refused as refused:
            raise HTTPException(422, str(refused)) from None

    @app.post("/api/golden/{suite_id}")
    def add_case(suite_id: str, body: NewCase, name: Person) -> Proposed:
        editor()
        try:
            return golden.create_case(
                workspace, store, suite_id, body.task, body.fields, name, body.reason, second
            )
        except NotFound as missing:
            raise HTTPException(404, str(missing)) from None
        except Refused as refused:
            raise HTTPException(422, str(refused)) from None

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
            if key.startswith(f"{golden.CHANGE_ITEM}:"):
                editor()
                if body.decision is None:
                    raise Refused("approve or reject the change")
                done = golden.finish_change(workspace, store, key, name, body.decision, body.note)
                return Finished(key=key, message=done)
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

    # The files the build put at the top of the folder, such as the icon, listed once: a
    # request names one of them or gets the app, and never reaches the disk itself.
    top = {f.name: f for f in root.iterdir() if f.is_file()} if root.is_dir() else {}

    @app.get("/{path:path}", include_in_schema=False)
    def web_app(path: str) -> Response:
        if path.startswith("api/"):
            raise HTTPException(404, "no such endpoint")
        if path in top:
            return FileResponse(top[path])
        if index.is_file():
            return FileResponse(index)
        return HTMLResponse(NOT_BUILT)

    return app
