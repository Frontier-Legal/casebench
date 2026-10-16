# SPDX-License-Identifier: Elastic-2.0
"""The team server's routes: setup, sign-in, the admin's people, keys and limits, and the audit log.

The routes of decision 0058.
"""

import hmac
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode, urlsplit

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from casebench.config import CasebenchConfig
from casebench.workbench import golden, items
from casebench.workbench.access import ADMIN, ENGINEER, ROLES, Can, refuse
from casebench.workbench.app import Who
from casebench.workbench.sources import Workspace
from casebench.workbench.store import Store
from casebench_ee.access import COOKIE
from casebench_ee.mail import Mailer, NoMail
from casebench_ee.models import Key, User
from casebench_ee.oidc import Provider, SignInRefused
from casebench_ee.passwords import WeakPassword, check, hashed, matches
from casebench_ee.team import SESSION, Team, TeamError

# Failed password attempts per email, in this process: five within 15 minutes lock it out.
ATTEMPTS, WINDOW = 5, 15 * 60
AUDIT_PAGE = 200
# Minutes an answer to review, and a court draft or change to approve, take (0059).
ANSWER_MINUTES, DRAFT_MINUTES = 2, 3


@dataclass
class Settings:
    """How this deployment is reached and what it may send. `setup_code` is the one-time
    code printed at start when the team has no one yet."""

    public_url: str
    setup_code: str | None = field(default=None, repr=False)
    config: CasebenchConfig | None = None

    @property
    def secure(self) -> bool:
        return urlsplit(self.public_url).scheme == "https"

    def at(self, path: str) -> str:
        return self.public_url.rstrip("/") + path


class Status(BaseModel):
    setup_needed: bool
    providers: list[dict[str, str]]
    mail: bool = Field(description="Whether this server emails sign-in links.")


class Setup(BaseModel):
    code: str
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(max_length=1000)


class PasswordSignIn(BaseModel):
    email: str
    password: str = Field(max_length=1000)


class LinkRequest(BaseModel):
    email: str


class Invite(BaseModel):
    email: str
    name: str = Field(min_length=1, max_length=200)
    role: str


class PersonChange(BaseModel):
    role: str | None = None
    active: bool | None = None


class NewKey(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    role: str


class LimitsBody(BaseModel):
    team: float | None = Field(default=None, ge=0)
    person: float | None = Field(default=None, ge=0)


class PersonView(BaseModel):
    id: int
    email: str
    name: str
    role: str
    active: bool
    invited_by: str | None
    last_seen: str | None
    password: bool


class Invited(BaseModel):
    person: PersonView
    emailed: bool
    link: str | None = Field(
        default=None, description="Shown when this server sends no email, to pass on."
    )
    waiting: int = Field(default=0, description="Items in the queue the person's role acts on.")
    minutes: int = Field(default=0, description="About how long they take (decision 0059).")


class KeyView(BaseModel):
    id: int
    name: str
    role: str
    created_by: str
    created_at: str
    revoked: bool


class NewKeyMade(BaseModel):
    key: KeyView
    token: str = Field(description="Shown this once; only its hash is kept.")


class AuditEntry(BaseModel):
    id: int
    at: str
    by: str
    action: str
    item: str
    subject: str
    before: Any = None
    after: Any = None
    reason: str | None = None


class TargetView(BaseModel):
    target: dict[str, Any] | None
    agent_models: list[dict[str, Any]]
    note: str = "Targets are set in casebench.yaml on the server."


def person_view(user: User) -> PersonView:
    return PersonView(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        active=user.active,
        invited_by=user.invited_by,
        last_seen=user.last_seen.isoformat() if user.last_seen else None,
        password=user.password is not None,
    )


def key_view(key: Key) -> KeyView:
    return KeyView(
        id=key.id,
        name=key.name,
        role=key.role,
        created_by=key.created_by,
        created_at=key.created_at.isoformat(),
        revoked=key.revoked_at is not None,
    )


def waiting_for(workspace: Workspace, store: Store, email: str, role: str) -> tuple[int, int]:
    """The items a role acts on, and about how many minutes they take: an answer two, a court
    draft or a change three (decision 0059)."""
    can = ROLES[role]
    found = items.queue(workspace, store, email) if Can.REVIEW in can else []
    answers = sum(1 for i in found if i.kind == "answer")
    others = 0
    if Can.EDIT in can:
        others = sum(1 for i in found if i.kind != "answer")
        others += len(golden.queue_items(store, email, set()))
    return answers + others, answers * ANSWER_MINUTES + others * DRAFT_MINUTES


def team_routes(
    team: Team,
    mailer: Mailer,
    providers: dict[str, Provider],
    settings: Settings,
    workspace: Workspace,
) -> APIRouter:
    router = APIRouter()
    failures: dict[str, list[float]] = defaultdict(list)

    def signed_in(response: Response, token: str) -> None:
        response.set_cookie(
            COOKIE,
            token,
            max_age=int(SESSION.total_seconds()),
            httponly=True,
            secure=settings.secure,
            samesite="lax",
            path="/",
        )

    def mail_link(
        user: User, by: str | None = None, work: tuple[int, int] = (0, 0)
    ) -> tuple[bool, str]:
        link = settings.at(f"/auth/link?token={team.link(user)}")
        inviter = f"{by} invited you to" if by else "Sign in to"
        waiting, minutes = work
        queue = (
            f"{waiting} item{'' if waiting == 1 else 's'} wait for you in the queue, about "
            f"{minutes} minutes of work.\n\n"
            if waiting
            else ""
        )
        text = (
            f"{inviter} Casebench, where your team reviews its legal AI.\n\n{queue}"
            f"Open this link to sign in. It works once, within 15 minutes:\n\n{link}\n\n"
            "If you did not expect this email, ignore it.\n"
        )
        try:
            sent = mailer.send(user.email, "Sign in to Casebench", text)
        except OSError:
            sent = False
        return sent, link

    @router.get("/api/team/status")
    def status() -> Status:
        return Status(
            setup_needed=team.setup_needed(),
            providers=[{"name": p.name, "title": p.title} for p in providers.values()],
            mail=not isinstance(mailer, NoMail),
        )

    @router.post("/api/team/setup")
    def setup(body: Setup, response: Response) -> PersonView:
        """Once: the code from the server's log, then the first admin, who sets a password
        that is no default."""
        if not team.setup_needed():
            raise HTTPException(409, "the team is set up; sign in instead")
        code = settings.setup_code or ""
        if not code or not hmac.compare_digest(body.code.strip(), code):
            raise HTTPException(403, "that is not the setup code in the server's log")
        try:
            check(body.password, body.email)
        except WeakPassword as weak:
            raise HTTPException(422, str(weak)) from None
        try:
            user = team.add(body.email, body.name, ADMIN, body.name, hashed(body.password))
        except TeamError as refused:
            raise HTTPException(422, str(refused)) from None
        settings.setup_code = None
        signed_in(response, team.start(user, "setup"))
        return person_view(user)

    @router.post("/api/team/signin/password")
    def password_sign_in(body: PasswordSignIn, response: Response) -> PersonView:
        email = body.email.strip().lower()
        recent = [t for t in failures[email] if t > time.time() - WINDOW]
        failures[email] = recent
        if len(recent) >= ATTEMPTS:
            raise HTTPException(429, "too many attempts; try again in 15 minutes")
        user = team.by_email(email)
        if user is None or not user.active or not matches(body.password, user.password):
            failures[email].append(time.time())
            raise HTTPException(401, "that email and password do not match")
        failures.pop(email, None)
        signed_in(response, team.start(user, "password"))
        return person_view(user)

    @router.post("/api/team/signin/link")
    def request_link(body: LinkRequest) -> dict[str, str]:
        """The same answer whether or not the email is in the team."""
        user = team.by_email(body.email)
        if user is not None and user.active:
            mail_link(user)
        return {"message": "If this email is in the team, a sign-in link is on its way."}

    @router.get("/auth/link", include_in_schema=False)
    def follow_link(token: str = "") -> Response:
        user = team.use_link(token)
        if user is None:
            return RedirectResponse("/?signin=expired", status_code=303)
        response = RedirectResponse("/", status_code=303)
        signed_in(response, team.start(user, "link"))
        return response

    @router.get("/auth/{provider}/start", include_in_schema=False)
    def provider_start(provider: str) -> Response:
        found = providers.get(provider)
        if found is None:
            raise HTTPException(404, "this server does not sign in with that provider")
        handshake = team.begin(provider)
        return RedirectResponse(
            found.authorize(handshake, settings.at(f"/auth/{provider}/callback")),
            status_code=303,
        )

    @router.get("/auth/{provider}/callback", include_in_schema=False)
    def provider_callback(provider: str, code: str = "", state: str = "") -> Response:
        found = providers.get(provider)
        handshake = team.finish(state, provider) if found else None
        try:
            if found is None or handshake is None or not code:
                raise SignInRefused("the sign-in expired or did not start here; try again")
            email = found.email(code, handshake, settings.at(f"/auth/{provider}/callback"))
            user = team.by_email(email)
            if user is None or not user.active:
                raise SignInRefused(f"{email} is not in this team; ask your admin to invite it")
        except SignInRefused as refused:
            query = urlencode({"signin": "refused", "why": str(refused)})
            return RedirectResponse(f"/?{query}", status_code=303)
        response = RedirectResponse("/", status_code=303)
        signed_in(response, team.start(user, found.name))
        return response

    @router.post("/api/team/signout")
    def sign_out(request: Request, response: Response) -> dict[str, bool]:
        team.end(request.cookies.get(COOKIE))
        response.delete_cookie(COOKIE, path="/")
        return {"signed_out": True}

    # The admin's pages.

    @router.get("/api/team/users")
    def users(who: Who) -> list[PersonView]:
        refuse(who, Can.ADMIN)
        return [person_view(u) for u in team.users()]

    @router.post("/api/team/users")
    def invite(body: Invite, who: Who) -> Invited:
        """An engineer invites viewers, reviewers and editors; an admin invites anyone."""
        refuse(who, Can.ENGINEER)
        if body.role in (ENGINEER, ADMIN):
            refuse(who, Can.ADMIN)
        try:
            user = team.add(body.email, body.name, body.role, who.name)
        except TeamError as refused:
            raise HTTPException(422, str(refused)) from None
        work = waiting_for(workspace, team.store, user.email, user.role)
        emailed, link = mail_link(user, who.name, work)
        return Invited(
            person=person_view(user),
            emailed=emailed,
            link=None if emailed else link,
            waiting=work[0],
            minutes=work[1],
        )

    @router.post("/api/team/users/{user_id}/link")
    def new_link(user_id: int, who: Who) -> Invited:
        refuse(who, Can.ADMIN)
        user = team.user(user_id)
        if user is None or not user.active:
            raise HTTPException(404, "no such active person")
        emailed, link = mail_link(user, who.name)
        return Invited(person=person_view(user), emailed=emailed, link=None if emailed else link)

    @router.patch("/api/team/users/{user_id}")
    def change_person(user_id: int, body: PersonChange, who: Who) -> PersonView:
        refuse(who, Can.ADMIN)
        try:
            return person_view(team.change(user_id, who.name, body.role, body.active))
        except TeamError as refused:
            raise HTTPException(422, str(refused)) from None

    @router.get("/api/team/keys")
    def keys(who: Who) -> list[KeyView]:
        refuse(who, Can.ADMIN)
        return [key_view(k) for k in team.api_keys()]

    @router.post("/api/team/keys")
    def make_key(body: NewKey, who: Who) -> NewKeyMade:
        refuse(who, Can.ADMIN)
        try:
            key, token = team.new_key(body.name, body.role, who.name)
        except TeamError as refused:
            raise HTTPException(422, str(refused)) from None
        return NewKeyMade(key=key_view(key), token=token)

    @router.post("/api/team/keys/{key_id}/revoke")
    def revoke_key(key_id: int, who: Who) -> KeyView:
        refuse(who, Can.ADMIN)
        try:
            return key_view(team.revoke(key_id, who.name))
        except TeamError as refused:
            raise HTTPException(404, str(refused)) from None

    @router.get("/api/team/limits")
    def limits(who: Who) -> LimitsBody:
        refuse(who, Can.ADMIN)
        found = team.limits()
        return LimitsBody(team=found.team, person=found.person)

    @router.put("/api/team/limits")
    def set_limits(body: LimitsBody, who: Who) -> LimitsBody:
        refuse(who, Can.ADMIN)
        found = team.set_limits(body.team, body.person, who.name)
        return LimitsBody(team=found.team, person=found.person)

    @router.get("/api/team/targets")
    def targets(who: Who) -> TargetView:
        refuse(who, Can.ADMIN)
        config = settings.config
        return TargetView(
            target=config.target if config else None,
            agent_models=[m.model_dump(mode="json") for m in config.agent_models] if config else [],
        )

    # The audit log: every decision and team event, newest first; it is only ever read.

    @router.get("/api/team/audit")
    def audit(who: Who, before: int | None = None, query: str = "") -> list[AuditEntry]:
        refuse(who, Can.EDIT)
        events = sorted(team.store.events(), key=lambda e: e.id, reverse=True)
        needle = query.strip().casefold()
        out = []
        for event in events:
            if before is not None and event.id >= before:
                continue
            entry = AuditEntry(
                id=event.id,
                at=event.at.isoformat(),
                by=event.by,
                action=event.action,
                item=event.item,
                subject=event.subject,
                before=event.before,
                after=event.after,
                reason=event.reason,
            )
            if needle and needle not in entry.model_dump_json().casefold():
                continue
            out.append(entry)
            if len(out) >= AUDIT_PAGE:
                break
        return out

    return router
