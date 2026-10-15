# SPDX-License-Identifier: Elastic-2.0
"""The team's people, sessions, sign-in links, API keys and settings, in the workbench's database.

Each change to them is also an event in the workbench's append-only log (decision 0058).
"""

import hashlib
import secrets
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from importlib import resources
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from casebench.workbench.access import ADMIN, ROLES
from casebench.workbench.store import Event, Store
from casebench.workbench.trying import Limits
from casebench_ee.models import Handshake, Key, Link, Setting, SignedIn, User, aware, now

SESSION = timedelta(days=14)
LINK = timedelta(minutes=15)
HANDSHAKE = timedelta(minutes=10)
KEY_PREFIX = "cbk_"
TEAM_ITEM = "team"
TEAM_LIMIT, PERSON_LIMIT = "try_daily_limit_usd", "try_person_daily_limit_usd"


class TeamError(ValueError):
    """A change the team refuses, such as leaving it with no admin."""


def digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def migrate(engine: Engine) -> None:
    config = Config()
    config.set_main_option("script_location", str(resources.files("casebench_ee") / "migrations"))
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


class Team:
    def __init__(self, store: Store) -> None:
        self.store = store
        migrate(store.engine)
        self.sessions = sessionmaker(store.engine, expire_on_commit=False)

    @contextmanager
    def session(self) -> Iterator[Session]:
        with self.sessions.begin() as session:
            yield session

    def log(self, by: str, action: str, subject: str, **fields: Any) -> None:
        self.store.log([Event(by=by, action=action, item=TEAM_ITEM, subject=subject, **fields)])

    # People.

    def setup_needed(self) -> bool:
        with self.session() as session:
            return not session.scalar(select(func.count()).select_from(User))

    def users(self) -> list[User]:
        with self.session() as session:
            return list(session.scalars(select(User).order_by(User.created_at)))

    def user(self, user_id: int) -> User | None:
        with self.session() as session:
            return session.get(User, user_id)

    def by_email(self, email: str) -> User | None:
        with self.session() as session:
            return session.scalar(select(User).where(User.email == email.strip().lower()))

    def add(
        self,
        email: str,
        name: str,
        role: str,
        by: str,
        password: str | None = None,
    ) -> User:
        email = email.strip().lower()
        if role not in ROLES:
            raise TeamError(f"no role {role}; choose one of {', '.join(ROLES)}")
        if "@" not in email or not name.strip():
            raise TeamError("give the person's name and email")
        if self.by_email(email) is not None:
            raise TeamError(f"{email} is already in the team")
        with self.session() as session:
            user = User(
                email=email,
                name=name.strip(),
                role=role,
                password=password,
                active=True,
                invited_by=by,
            )
            session.add(user)
        self.log(by, "invited", email, after={"name": user.name, "role": role})
        return user

    def change(self, user_id: int, by: str, role: str | None, active: bool | None) -> User:
        """There is always one active admin at least."""
        if role is not None and role not in ROLES:
            raise TeamError(f"no role {role}")
        with self.session() as session:
            user = session.get(User, user_id)
            if user is None:
                raise TeamError("no such person")
            before = {"role": user.role, "active": user.active}
            new_role = role if role is not None else user.role
            new_active = active if active is not None else user.active
            if user.role == ADMIN and user.active and (new_role != ADMIN or not new_active):
                admins = session.scalar(
                    select(func.count())
                    .select_from(User)
                    .where(User.role == ADMIN, User.active.is_(True))
                )
                if (admins or 0) <= 1:
                    raise TeamError("the team needs one admin at least; make someone else admin")
            user.role, user.active = new_role, new_active
            after = {"role": user.role, "active": user.active}
        if not user.active:
            self.end_sessions(user_id)
        self.log(by, "changed person", user.email, before=before, after=after)
        return user

    def seen(self, user_id: int) -> None:
        with self.session() as session:
            user = session.get(User, user_id)
            if user is not None:
                user.last_seen = now()

    # Sessions.

    def start(self, user: User, how: str) -> str:
        token = secrets.token_urlsafe(32)
        with self.session() as session:
            session.add(SignedIn(token=digest(token), user_id=user.id, expires=now() + SESSION))
        self.seen(user.id)
        self.log(user.name, "signed in", user.email, after={"with": how})
        return token

    def signed_in(self, token: str | None) -> User | None:
        if not token:
            return None
        with self.session() as session:
            found = session.get(SignedIn, digest(token))
            if found is None or aware(found.expires) <= now():
                return None
            user = session.get(User, found.user_id)
            return user if user is not None and user.active else None

    def end(self, token: str | None) -> None:
        if not token:
            return
        with self.session() as session:
            found = session.get(SignedIn, digest(token))
            if found is not None:
                session.delete(found)

    def end_sessions(self, user_id: int) -> None:
        with self.session() as session:
            for found in session.scalars(select(SignedIn).where(SignedIn.user_id == user_id)):
                session.delete(found)

    # Sign-in links.

    def link(self, user: User) -> str:
        token = secrets.token_urlsafe(32)
        with self.session() as session:
            session.add(Link(token=digest(token), user_id=user.id, expires=now() + LINK))
        return token

    def use_link(self, token: str) -> User | None:
        """Once, before it expires, by an active person."""
        with self.session() as session:
            found = session.get(Link, digest(token))
            if found is None or found.used_at is not None or aware(found.expires) <= now():
                return None
            found.used_at = now()
            user = session.get(User, found.user_id)
            return user if user is not None and user.active else None

    # API keys.

    def api_keys(self) -> list[Key]:
        with self.session() as session:
            return list(session.scalars(select(Key).order_by(Key.created_at)))

    def new_key(self, name: str, role: str, by: str) -> tuple[Key, str]:
        if role not in ROLES or role == ADMIN:
            raise TeamError("a key has a role below admin")
        token = KEY_PREFIX + secrets.token_urlsafe(32)
        with self.session() as session:
            key = Key(name=name.strip() or "key", role=role, token=digest(token), created_by=by)
            session.add(key)
        self.log(by, "created key", key.name, after={"role": role})
        return key, token

    def key(self, token: str | None) -> Key | None:
        if not token or not token.startswith(KEY_PREFIX):
            return None
        with self.session() as session:
            found = session.scalar(select(Key).where(Key.token == digest(token)))
            return found if found is not None and found.revoked_at is None else None

    def revoke(self, key_id: int, by: str) -> Key:
        with self.session() as session:
            key = session.get(Key, key_id)
            if key is None:
                raise TeamError("no such key")
            key.revoked_at = key.revoked_at or now()
        self.log(by, "revoked key", key.name)
        return key

    # Settings.

    def setting(self, name: str) -> Any:
        with self.session() as session:
            found = session.get(Setting, name)
            return found.value if found is not None else None

    def limits(self) -> Limits:
        return Limits(team=self.setting(TEAM_LIMIT), person=self.setting(PERSON_LIMIT))

    def set_limits(self, team: float | None, person: float | None, by: str) -> Limits:
        before = self.limits()
        with self.session() as session:
            for name, value in ((TEAM_LIMIT, team), (PERSON_LIMIT, person)):
                session.merge(Setting(name=name, value=value))
        self.log(
            by,
            "changed limits",
            "spend limits",
            before={"team": before.team, "person": before.person},
            after={"team": team, "person": person},
        )
        return self.limits()

    # Sign-in with Google or Microsoft.

    def begin(self, provider: str) -> Handshake:
        handshake = Handshake(
            state=secrets.token_urlsafe(24),
            provider=provider,
            nonce=secrets.token_urlsafe(24),
            verifier=secrets.token_urlsafe(64),
        )
        with self.session() as session:
            session.add(handshake)
        return handshake

    def finish(self, state: str, provider: str) -> Handshake | None:
        """Once, within ten minutes, for the provider it began with."""
        with self.session() as session:
            found = session.get(Handshake, state)
            if found is None:
                return None
            session.delete(found)
            fresh = aware(found.created_at) > now() - HANDSHAKE
            return found if fresh and found.provider == provider else None
