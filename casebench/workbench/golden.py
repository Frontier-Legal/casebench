"""Golden data in the workbench, changed only with a second editor's approval (decision 0052).

Cases are listed per suite, a change is proposed, and nothing reaches a suite until another
editor approves it.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from casebench.cases.golden import (
    FieldChange,
    cells_of,
    changes,
    editable,
    fields_of,
    new_case,
    revised,
)
from casebench.cases.sheet import COLUMNS, SheetError, task_names
from casebench.cases.suite import next_id, save
from casebench.core.case import Approval, Case
from casebench.workbench.items import NotFound, Refused
from casebench.workbench.sources import SuiteFolder, Workspace
from casebench.workbench.store import (
    APPROVED,
    CHANGE,
    FINISHED,
    NEW,
    PENDING,
    REJECTED,
    Event,
    Proposal,
    Store,
)

CHANGE_ITEM = "change"


class Waiting(BaseModel):
    id: int
    kind: Literal["new", "change"]
    author: str
    at: datetime
    reason: str | None = None


class CaseRow(BaseModel):
    case_id: str
    title: str
    task: str
    source: str
    approval: str
    editable: bool
    waiting: Waiting | None = None


class GoldenSuite(BaseModel):
    suite_id: str
    cases: list[CaseRow]


class Golden(BaseModel):
    suites: list[GoldenSuite]
    tasks: list[str] = Field(description="The task types a new case may have.")
    second_approval: bool = Field(
        default=False, description="Whether a change waits for a second editor (0053)."
    )


class Form(BaseModel):
    name: str
    value: str
    help: str = Field(default="", description="What the field takes, as the spreadsheet says.")


class CaseDetail(BaseModel):
    suite_id: str
    case_id: str
    title: str
    task: str
    source: str
    approval: str
    author: str | None
    editable: bool
    fields: list[Form]
    waiting: Waiting | None = None


class ChangeItem(BaseModel):
    """A proposal as the second editor sees it: what changed, who, when and why."""

    key: str
    kind: Literal["change"] = "change"
    title: str
    where: str
    task: str
    proposal: Waiting
    changes: list[FieldChange]
    draft: dict | None = None
    held_by: str | None = None
    engineering: None = None


class Proposed(BaseModel):
    """`proposal` is set when the change waits for a second editor."""

    suite_id: str
    case_id: str
    proposal: int | None = None
    message: str


def _help(name: str) -> str:
    """The spreadsheet's help for a field; the form takes a document's text, not its path."""
    return "The document's text." if name == "document" else COLUMNS.get(name, "")


def change_key(number: int) -> str:
    return f"{CHANGE_ITEM}:{number}"


def proposal_number(key: str) -> int:
    kind, _, number = key.partition(":")
    if kind != CHANGE_ITEM or not number.isdigit():
        raise NotFound(f"no item {key}")
    return int(number)


def _title(case: Case) -> str:
    inputs = case.task.inputs
    return str(inputs.get("question") or inputs.get("instruction") or f"{case.task.type} case")


def _waiting(proposal: Proposal | None) -> Waiting | None:
    if proposal is None:
        return None
    kind: Literal["new", "change"] = "new" if proposal.kind == NEW else "change"
    return Waiting(
        id=proposal.id, kind=kind, author=proposal.author, at=proposal.at, reason=proposal.reason
    )


def _pending(store: Store) -> dict[tuple[str, str], Proposal]:
    return {(p.suite_id, p.case_id): p for p in store.proposals(PENDING)}


def golden(workspace: Workspace, store: Store, second: bool = False) -> Golden:
    waiting = _pending(store)
    suites = [
        GoldenSuite(
            suite_id=suite_id,
            cases=[
                CaseRow(
                    case_id=case.id,
                    title=_title(case),
                    task=case.task.type,
                    source=case.reference.source.value,
                    approval=case.approval.value,
                    editable=editable(case),
                    waiting=_waiting(waiting.get((suite_id, case.id))),
                )
                for case in suite.cases
            ],
        )
        for suite_id, suite in sorted(workspace.suites().items())
    ]
    return Golden(suites=suites, tasks=task_names(), second_approval=second)


def _suite(workspace: Workspace, suite_id: str) -> SuiteFolder:
    suite = workspace.suites().get(suite_id)
    if suite is None:
        raise NotFound(f"no suite {suite_id}")
    return suite


def _case(workspace: Workspace, suite_id: str, case_id: str) -> tuple[SuiteFolder, Case]:
    suite = _suite(workspace, suite_id)
    case = suite.case(case_id)
    if case is None:
        raise NotFound(f"no case {case_id} in suite {suite_id}")
    return suite, case


def case_detail(workspace: Workspace, store: Store, suite_id: str, case_id: str) -> CaseDetail:
    _, case = _case(workspace, suite_id, case_id)
    can = editable(case)
    cells = cells_of(case) if can else {}
    return CaseDetail(
        suite_id=suite_id,
        case_id=case.id,
        title=_title(case),
        task=case.task.type,
        source=case.reference.source.value,
        approval=case.approval.value,
        author=case.reference.author,
        editable=can,
        fields=[Form(name=name, value=value, help=_help(name)) for name, value in cells.items()],
        waiting=_waiting(_pending(store).get((suite_id, case_id))),
    )


def blank_form(task: str) -> list[Form]:
    if task not in task_names():
        raise NotFound(f"no task type {task}")
    return [Form(name=name, value="", help=_help(name)) for name in fields_of(task)]


def propose_change(
    workspace: Workspace,
    store: Store,
    suite_id: str,
    case_id: str,
    cells: dict[str, str],
    reason: str,
    person: str,
    second: bool = False,
) -> Proposed:
    """With a second editor's approval on, the suite stays as it is until another editor
    approves the change; off, the change is written into the suite now (decision 0053)."""
    _, case = _case(workspace, suite_id, case_id)
    if not editable(case):
        raise Refused(f"{case.task.type} cases are changed where they were made, not in the form")
    if not reason.strip():
        raise Refused("say why you change the case; the event log keeps it")
    if (suite_id, case_id) in _pending(store):
        raise Refused("a change to this case is already waiting for a second editor")
    if not changes(cells_of(case), cells):
        raise Refused("nothing changed")
    try:
        after = revised(case, cells, person)
    except SheetError as failure:
        raise Refused(str(failure)) from None
    if not second:
        suite = _suite(workspace, suite_id)
        cases = [after if c.id == case_id else c for c in suite.cases]
        _, manifest = save(suite.folder, cases)
        store.log(
            [
                Event(
                    by=person,
                    action="changed",
                    item=f"case:{suite_id}/{case_id}",
                    subject=f"{suite_id}/{case_id}",
                    before=case.model_dump(mode="json"),
                    after=after.model_dump(mode="json"),
                    reason=reason.strip(),
                )
            ]
        )
        return Proposed(
            suite_id=suite_id,
            case_id=case_id,
            message=f"changed; the suite's hash is now {manifest.content_hash}",
        )
    proposal = store.propose(
        Proposal(
            kind=CHANGE,
            suite_id=suite_id,
            case_id=case_id,
            before=case.model_dump(mode="json"),
            after=after.model_dump(mode="json"),
            author=person,
            reason=reason.strip(),
            status=PENDING,
        )
    )
    store.log([_event(proposal, person, "proposed", reason.strip())])
    return Proposed(
        suite_id=suite_id,
        case_id=case_id,
        proposal=proposal.id,
        message="the change waits for a second editor; the case stays as it was until then",
    )


def create_case(
    workspace: Workspace,
    store: Store,
    suite_id: str,
    task: str,
    cells: dict[str, str],
    person: str,
    reason: str | None = None,
    second: bool = False,
) -> Proposed:
    """A new case is approved by its author, or, with a second editor's approval on, enters
    its suite as a draft with a proposal to approve it (decision 0053)."""
    if task not in task_names():
        raise NotFound(f"no task type {task}")
    suite = _suite(workspace, suite_id)
    case_id = next_id(suite.manifest.suite_id, suite.cases)
    try:
        case = new_case(
            task, cells, case_id, person, Approval.DRAFT if second else Approval.APPROVED
        )
    except SheetError as failure:
        raise Refused(str(failure)) from None
    _, manifest = save(suite.folder, [*suite.cases, case])
    if not second:
        store.log(
            [
                Event(
                    by=person,
                    action="created",
                    item=f"case:{suite_id}/{case_id}",
                    subject=f"{suite_id}/{case_id}",
                    after=case.model_dump(mode="json"),
                    reason=(reason or "").strip() or None,
                )
            ]
        )
        return Proposed(
            suite_id=suite_id,
            case_id=case_id,
            message=f"{case_id} is approved in {suite_id}; the suite's hash is now "
            f"{manifest.content_hash}",
        )
    proposal = store.propose(
        Proposal(
            kind=NEW,
            suite_id=suite_id,
            case_id=case_id,
            before=None,
            after=case.model_dump(mode="json"),
            author=person,
            reason=(reason or "").strip() or None,
            status=PENDING,
        )
    )
    store.log([_event(proposal, person, "proposed", proposal.reason)])
    return Proposed(
        suite_id=suite_id,
        case_id=case_id,
        proposal=proposal.id,
        message=f"{case_id} is a draft in {suite_id} until a second editor approves it; "
        f"the suite's hash is now {manifest.content_hash}",
    )


def _event(proposal: Proposal, by: str, action: str, reason: str | None) -> Event:
    return Event(
        by=by,
        action=action,
        item=change_key(proposal.id),
        subject=f"{proposal.suite_id}/{proposal.case_id}",
        before=proposal.before,
        after=proposal.after,
        reason=reason,
    )


def queue_items(store: Store, person: str, held: set[str]) -> list[tuple[str, str, str, str, str]]:
    """Each change waiting for someone other than its author: key, title, where, task, and
    whether it is a new case or a change."""
    out = []
    for proposal in store.proposals(PENDING):
        key = change_key(proposal.id)
        if proposal.author == person or key in held:
            continue
        case = Case.model_validate(proposal.after)
        flag = "new case" if proposal.kind == NEW else "change"
        out.append((key, _title(case), f"suite {proposal.suite_id}", case.task.type, flag))
    return out


def change_item(store: Store, key: str, person: str) -> ChangeItem:
    proposal = store.proposal(proposal_number(key))
    if proposal is None or proposal.status != PENDING:
        raise NotFound(f"no change waiting as {key}")
    after = Case.model_validate(proposal.after)
    before = cells_of(Case.model_validate(proposal.before)) if proposal.before else {}
    waiting = _waiting(proposal)
    assert waiting is not None
    return ChangeItem(
        key=key,
        title=_title(after),
        where=f"suite {proposal.suite_id}",
        task=after.task.type,
        proposal=waiting,
        changes=changes(before, cells_of(after)),
        draft=store.draft(key, person),
        held_by=store.holder(key),
    )


def finish_change(
    workspace: Workspace,
    store: Store,
    key: str,
    person: str,
    decision: Literal["approve", "reject"],
    note: str | None,
) -> str:
    """Approving writes the change into its suite; a rejected new case leaves its suite."""
    proposal = store.proposal(proposal_number(key))
    if proposal is None or proposal.status != PENDING:
        raise NotFound(f"no change waiting as {key}")
    if proposal.author == person:
        raise Refused("a second editor approves a change, not its author")
    if decision == "reject" and not (note or "").strip():
        raise Refused("say why you reject the change; its author reads it")
    suite, case = _case(workspace, proposal.suite_id, proposal.case_id)
    after = Case.model_validate(proposal.after)
    if proposal.kind == CHANGE and case.model_dump(mode="json") != proposal.before:
        raise Refused("the case changed since this was proposed; its author proposes it again")
    cases = list(suite.cases)
    place = [c.id for c in cases].index(case.id)
    message = ""
    if decision == "approve":
        cases[place] = after.model_copy(update={"approval": Approval.APPROVED})
        _, manifest = save(suite.folder, cases)
        message = f"approved; the suite's hash is now {manifest.content_hash}"
    elif proposal.kind == NEW:
        del cases[place]
        _, manifest = save(suite.folder, cases)
        message = f"rejected; {case.id} left the suite"
    else:
        message = "rejected; the case stays as it was"
    status = APPROVED if decision == "approve" else REJECTED
    decided = store.decide(proposal.id, status, person, (note or "").strip() or None)
    store.log(
        [
            _event(decided, person, "approved" if decision == "approve" else "rejected", note),
            Event(
                by=person, action=FINISHED, item=key, subject=f"{suite.manifest.suite_id}/{case.id}"
            ),
        ]
    )
    store.drop_drafts(key)
    store.release(key)
    return message
