# SPDX-License-Identifier: Elastic-2.0
"""Who is calling a team server: a signed-in person by their session, or CI by an API key."""

from fastapi import Request

from casebench.workbench.access import ROLES, Caller
from casebench_ee.team import Team

COOKIE = "casebench_session"


class TeamAccess:
    mode = "team"

    def __init__(self, team: Team) -> None:
        self.team = team

    def caller(self, request: Request) -> Caller | None:
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            key = self.team.key(authorization[7:].strip())
            if key is None:
                return None
            return Caller(
                name=f"API key {key.name}", key=f"key:{key.id}", role=key.role, can=ROLES[key.role]
            )
        user = self.team.signed_in(request.cookies.get(COOKIE))
        if user is None:
            return None
        return Caller(name=user.name, key=user.email, role=user.role, can=ROLES[user.role])
