"""Read ids stored before ids named their corpus as the setup's one corpus's (decision 0042)."""

from casebench.core.case import Case
from casebench.corpus.ids import UnqualifiedId, qualify, split


def _named(document_id: str, corpora: list[str]) -> bool:
    try:
        return split(document_id)[0] in corpora
    except UnqualifiedId:
        return False


def as_qualified(cases: list[Case], corpora: list[str]) -> list[Case]:
    """Each id that names no corpus of the setup is the one corpus's; with several corpora an
    old id is left as it is, since nothing says whose it is."""
    if len(corpora) != 1:
        return cases
    [name] = corpora

    def fixed(document_id: str | None) -> str | None:
        if document_id is None or _named(document_id, corpora):
            return document_id
        return qualify(name, document_id)

    out = []
    for case in cases:
        facts = [
            f.model_copy(update={"document_id": fixed(f.document_id)}) for f in case.reference.facts
        ]
        update: dict = {"reference": case.reference.model_copy(update={"facts": facts})}
        if case.provenance is not None:
            source = fixed(case.provenance.source_decision_id)
            update["provenance"] = case.provenance.model_copy(update={"source_decision_id": source})
        out.append(case.model_copy(update=update))
    return out
