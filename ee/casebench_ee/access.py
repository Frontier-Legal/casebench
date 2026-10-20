# SPDX-License-Identifier: Elastic-2.0
"""Who is calling a team server: a signed-in person by their session, or CI by an API key."""

from fastapi import Request

from casebench.workbench.access import ROLES, Caller
from casebench_ee.models import Key, User
from casebench_ee.team import Team

COOKIE = "casebench_session"


class TeamAccess:
    mode = "team"

    def __init__(self, team: Team) -> None:
        self.team = team

    def _found(self, request: Request) -> Key | User | None:
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            return self.team.key(authorization[7:].strip())
        return self.team.signed_in(request.cookies.get(COOKIE))

    def organisation(self, request: Request) -> str | None:
        """The caller's organisation, which the request is for (decision 0066); before anyone
        signs in, the one a self-hosted server has."""
        found = self._found(request)
        return found.organisation if found is not None else None

    def caller(self, request: Request) -> Caller | None:
        found = self._found(request)
        if isinstance(found, Key):
            return Caller(
                name=f"API key {found.name}",
                key=f"key:{found.id}",
                role=found.role,
                can=ROLES[found.role],
                organisation=found.organisation,
            )
        if found is None:
            return None
        return Caller(
            name=found.name,
            key=found.email,
            role=found.role,
            can=ROLES[found.role],
            organisation=found.organisation,
        )
