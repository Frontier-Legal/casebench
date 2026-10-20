"""Who is calling the workbench and what they may do.

The local default names the person from a header; a team server fills the hook with its own
logins (decision 0058).
"""

from enum import StrEnum
from typing import Protocol
from urllib.parse import unquote

from fastapi import HTTPException, Request
from pydantic import BaseModel, Field

from casebench.workbench.tenancy import LOCAL as LOCAL_ORGANISATION

PERSON_HEADER = "X-Casebench-Person"


class Can(StrEnum):
    READ = "read"
    REVIEW = "review"
    COMPARE = "compare"
    TRY = "try"
    EDIT = "edit"
    ENGINEER = "engineer"
    ADMIN = "admin"


# Each role can do what the one before it can, and more.
LADDER: list[tuple[str, set[Can]]] = [
    ("viewer", {Can.READ}),
    ("reviewer", {Can.REVIEW, Can.COMPARE, Can.TRY}),
    ("editor", {Can.EDIT}),
    ("engineer", {Can.ENGINEER}),
    ("admin", {Can.ADMIN}),
]


def _roles() -> dict[str, frozenset[Can]]:
    out: dict[str, frozenset[Can]] = {}
    held: set[Can] = set()
    for role, adds in LADDER:
        held |= adds
        out[role] = frozenset(held)
    return out


ROLES = _roles()
VIEWER, REVIEWER, EDITOR, ENGINEER, ADMIN = (role for role, _ in LADDER)
# Locally the one person at the machine may do everything but administer a team.
LOCAL = ENGINEER


class Caller(BaseModel):
    """`key` names the person for their saved preferences; `name` is how events record them."""

    name: str
    key: str
    role: str
    can: frozenset[Can] = Field(default_factory=frozenset)
    organisation: str = Field(default=LOCAL_ORGANISATION, description="Decision 0066.")

    def may(self, action: Can) -> bool:
        return action in self.can


class Access(Protocol):
    """Who is calling. `mode` is local or team; `caller` returns None when no one is signed
    in, and the request is refused."""

    @property
    def mode(self) -> str: ...

    def caller(self, request: Request) -> Caller | None: ...


class LocalAccess:
    """The person names themselves in a header; `role` limits them, as `casebench ui --role
    reviewer` does."""

    mode = "local"

    def __init__(self, role: str | None = None) -> None:
        self.role = role if role in ROLES else LOCAL

    def caller(self, request: Request) -> Caller | None:
        name = unquote(request.headers.get(PERSON_HEADER) or "").strip()
        if not name:
            return None
        return Caller(name=name, key=name, role=self.role, can=ROLES[self.role])


def refuse(caller: Caller, action: Can) -> None:
    """403 unless the caller may take the action."""
    if not caller.may(action):
        raise HTTPException(403, f"the {caller.role} role cannot {WHAT[action]}")


WHAT = {
    Can.READ: "read results",
    Can.REVIEW: "give verdicts",
    Can.COMPARE: "compare runs",
    Can.TRY: "try questions",
    Can.EDIT: "change golden data",
    Can.ENGINEER: "use the engineering view",
    Can.ADMIN: "administer the team",
}
