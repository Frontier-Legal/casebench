"""What only the workbench keeps: people, reservations, drafts and the event log (0050).

Runs and suites stay in their folders.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from importlib import resources
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from sqlalchemy import JSON, DateTime, Engine, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from casebench.workbench.tenancy import current

DEFAULT_DATABASE = Path(".casebench") / "casebench.db"
# How long an opened item stays reserved without being renewed.
HOLD = timedelta(minutes=15)
# The event that marks an item done in the queue.
FINISHED = "finished"


def now() -> datetime:
    return datetime.now(UTC)


def _aware(moment: datetime) -> datetime:
    """SQLite returns times without their zone; every time written here is UTC."""
    return moment if moment.tzinfo else moment.replace(tzinfo=UTC)


class Base(DeclarativeBase):
    pass


def organisation_column(primary_key: bool = False) -> Mapped[str]:
    """The organisation a row belongs to, the request's when it is written (decision 0066)."""
    return mapped_column(String(64), primary_key=primary_key, default=current)


class Person(Base):
    __tablename__ = "people"

    organisation: Mapped[str] = organisation_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), primary_key=True)
    view: Mapped[str] = mapped_column(String(20), default="review")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Reservation(Base):
    __tablename__ = "reservations"

    organisation: Mapped[str] = organisation_column(primary_key=True)
    item: Mapped[str] = mapped_column(String(500), primary_key=True)
    person: Mapped[str] = mapped_column(String(200))
    until: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Draft(Base):
    """A person's unfinished choices on an item, saved as they are made."""

    __tablename__ = "drafts"

    organisation: Mapped[str] = organisation_column(primary_key=True)
    item: Mapped[str] = mapped_column(String(500), primary_key=True)
    person: Mapped[str] = mapped_column(String(200), primary_key=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Event(Base):
    """One decision that reached a run or a suite: who, when, what before and after, and why.
    Rows are only ever added."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    by: Mapped[str] = mapped_column(String(200))
    action: Mapped[str] = mapped_column(String(50))
    item: Mapped[str] = mapped_column(String(500))
    subject: Mapped[str] = mapped_column(String(500))
    before: Mapped[Any] = mapped_column(JSON, nullable=True)
    after: Mapped[Any] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    organisation: Mapped[str] = organisation_column()


PENDING, APPROVED, REJECTED = "pending", "approved", "rejected"
NEW, CHANGE = "new", "change"


class Proposal(Base):
    """A change to golden data, or a new case, waiting for a second editor (decision 0052).
    `before` and `after` are whole cases; a new case has no `before`."""

    __tablename__ = "proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(String(20))
    suite_id: Mapped[str] = mapped_column(String(200))
    case_id: Mapped[str] = mapped_column(String(200))
    before: Mapped[Any] = mapped_column(JSON, nullable=True)
    after: Mapped[Any] = mapped_column(JSON)
    author: Mapped[str] = mapped_column(String(200))
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=PENDING)
    decided_by: Mapped[str | None] = mapped_column(String(200), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    organisation: Mapped[str] = organisation_column()


def url_for(path: Path) -> str:
    return f"sqlite:///{path.resolve().as_posix()}"


def migrate(engine: Engine) -> None:
    """Bring the database to the newest schema, as the app starts."""
    config = Config()
    config.set_main_option(
        "script_location", str(resources.files("casebench.workbench") / "migrations")
    )
    with engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "head")


class Store:
    def __init__(self, url: str) -> None:
        if url.startswith("sqlite:///"):
            Path(url.removeprefix("sqlite:///")).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(url)
        migrate(self.engine)
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    @contextmanager
    def session(self) -> Iterator[Session]:
        with self.sessions.begin() as session:
            yield session

    def person(self, name: str) -> Person | None:
        with self.session() as session:
            return session.get(Person, (current(), name))

    def save_person(self, name: str, view: str) -> Person:
        with self.session() as session:
            person = session.get(Person, (current(), name)) or Person(name=name)
            person.view = view
            session.add(person)
            return person

    def holder(self, item: str) -> str | None:
        """Who holds the item now, if anyone."""
        with self.session() as session:
            held = session.get(Reservation, (current(), item))
            if held is None or _aware(held.until) <= now():
                return None
            return held.person

    def held_by_others(self, person: str) -> set[str]:
        with self.session() as session:
            rows = session.scalars(select(Reservation).where(Reservation.person != person))
            return {r.item for r in rows if _aware(r.until) > now()}

    def reserve(self, item: str, person: str) -> str:
        """Reserves the item for the person, or renews it; returns who holds it after."""
        with self.session() as session:
            held = session.get(Reservation, (current(), item))
            if held is not None and held.person != person and _aware(held.until) > now():
                return held.person
            held = held or Reservation(item=item)
            held.person, held.until = person, now() + HOLD
            session.add(held)
            return person

    def release(self, item: str) -> None:
        with self.session() as session:
            held = session.get(Reservation, (current(), item))
            if held is not None:
                session.delete(held)

    def draft(self, item: str, person: str) -> dict[str, Any] | None:
        with self.session() as session:
            found = session.get(Draft, (current(), item, person))
            return dict(found.payload) if found else None

    def save_draft(self, item: str, person: str, payload: dict[str, Any]) -> None:
        with self.session() as session:
            found = session.get(Draft, (current(), item, person)) or Draft(item=item, person=person)
            found.payload, found.saved_at = payload, now()
            session.add(found)

    def drop_drafts(self, item: str) -> None:
        with self.session() as session:
            for found in session.scalars(select(Draft).where(Draft.item == item)):
                session.delete(found)

    def log(self, events: list[Event]) -> None:
        with self.session() as session:
            session.add_all(events)

    def events(self, item: str | None = None) -> list[Event]:
        with self.session() as session:
            query = select(Event).order_by(Event.id)
            if item is not None:
                query = query.where(Event.item == item)
            return list(session.scalars(query))

    def propose(self, proposal: Proposal) -> Proposal:
        with self.session() as session:
            session.add(proposal)
            session.flush()
            return proposal

    def proposal(self, number: int) -> Proposal | None:
        with self.session() as session:
            return session.get(Proposal, number)

    def proposals(self, status: str | None = PENDING) -> list[Proposal]:
        with self.session() as session:
            query = select(Proposal).order_by(Proposal.id)
            if status is not None:
                query = query.where(Proposal.status == status)
            return list(session.scalars(query))

    def decide(self, number: int, status: str, by: str, note: str | None) -> Proposal:
        with self.session() as session:
            found = session.get(Proposal, number)
            assert found is not None
            found.status, found.decided_by, found.decided_at = status, by, now()
            found.note = note
            return found

    def finished(self) -> set[str]:
        """Items someone finished in the workbench."""
        with self.session() as session:
            return set(session.scalars(select(Event.item).where(Event.action == FINISHED)))
