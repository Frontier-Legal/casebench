"""Where two readings of one decision agree, field by field (decision 0027)."""

from casebench.core.case import Evidence, Fact
from casebench.extract.reading import Item, Reading

FIELDS = ("outcome", "statutes", "precedents", "facts")


def same_items(first: list[Item], second: list[Item]) -> bool:
    """Every item of each reading overlaps the passage of an item of the other."""
    return all(any(a.overlaps(b) for b in second) for a in first) and all(
        any(b.overlaps(a) for a in first) for b in second
    )


def agreed_fields(first: Reading, second: Reading) -> dict[str, bool]:
    outcome = (
        first.outcome is not None
        and second.outcome is not None
        and first.outcome.value == second.outcome.value
    )
    return {
        "outcome": outcome,
        "statutes": same_items(first.statutes, second.statutes),
        "precedents": same_items(first.precedents, second.precedents),
        "facts": bool(first.facts) and not reveals_ruling(first),
    }


def reveals_ruling(reading: Reading) -> bool:
    """Facts that quote the ruling's passage or name its label would give the answer away."""
    if reading.outcome is None:
        return False
    facts = reading.facts.casefold()
    return reading.outcome.quote.casefold() in facts or reading.outcome.value in facts


def key_facts(decision_id: str, reading: Reading, agreed: dict[str, bool]) -> list[Fact]:
    """The first model's items, kept only for the fields both models agreed on."""

    def fact(kind: str, number: int, item: Item) -> Fact:
        evidence = Evidence(doc=decision_id, span=item.span, quote=item.quote)
        return Fact(id=f"{kind}-{number}", kind=kind, value=item.value, evidence=evidence)

    facts: list[Fact] = []
    if agreed["outcome"] and reading.outcome is not None:
        facts.append(fact("outcome", 1, reading.outcome))
    for kind, items in (("statute", reading.statutes), ("precedent", reading.precedents)):
        field = f"{kind}s"
        if agreed[field] and items:
            facts += [fact(kind, n, item) for n, item in enumerate(items, start=1)]
    return facts
