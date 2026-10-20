# SPDX-License-Identifier: Elastic-2.0
"""The tables a team adds to the workbench's database: people who sign in, and how (0058)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from casebench.workbench.store import organisation_column


def now() -> datetime:
    return datetime.now(UTC)


def aware(moment: datetime) -> datetime:
    """SQLite returns times without their zone; every time written here is UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


class TeamBase(DeclarativeBase):
    pass


class Organisation(TeamBase):
    """A firm the server serves; a self-hosted server has the one named `local` (0066)."""

    __tablename__ = "team_organisations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class User(TeamBase):
    """A person invited to the team. `password` is a scrypt hash, set only for the first
    admin; everyone else signs in by link or with Google or Microsoft."""

    __tablename__ = "team_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))
    password: Mapped[str | None] = mapped_column(String(300), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    invited_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organisation: Mapped[str] = organisation_column()


class SignedIn(TeamBase):
    """A session: the hash of the token in the person's cookie."""

    __tablename__ = "team_sessions"

    organisation: Mapped[str] = organisation_column()

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Link(TeamBase):
    """A sign-in link sent by email: the hash of its token, usable once before it expires."""

    __tablename__ = "team_links"

    organisation: Mapped[str] = organisation_column()

    token: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer)
    expires: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Key(TeamBase):
    """An API key for CI, with a role: the hash of the key, shown in full only once."""

    __tablename__ = "team_keys"

    organisation: Mapped[str] = organisation_column()

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20))
    token: Mapped[str] = mapped_column(String(64), unique=True)
    created_by: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Setting(TeamBase):
    """A value an admin sets, such as the daily spend limits."""

    __tablename__ = "team_settings"

    organisation: Mapped[str] = organisation_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON, nullable=True)


class Handshake(TeamBase):
    """A sign-in with Google or Microsoft under way: what its return must match."""

    __tablename__ = "team_handshakes"

    organisation: Mapped[str] = organisation_column()

    state: Mapped[str] = mapped_column(String(64), primary_key=True)
    provider: Mapped[str] = mapped_column(String(20))
    nonce: Mapped[str] = mapped_column(String(64))
    verifier: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
