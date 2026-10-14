"""Each citation is searched only where it can be found, and one nobody can check is unchecked."""

import json
from pathlib import Path
from typing import Any

from casebench.core.case import Case, Provenance, Reference, ReferenceSource, Task
from casebench.core.score import CitationLabel, Score
from casebench.corpus.binding import CorpusConfig, Holding
from casebench.corpus.corpora import Corpora
from casebench.corpus.routing import Route, covers
from casebench.judge import prompts
from casebench.judge.config import JudgeConfig
from casebench.judge.resolve import Resolver
from casebench.metrics.base import score
from casebench.metrics.builtin.citation_integrity import CitationIntegrity
from casebench.report.render import lines
from casebench.report.tables import build_tables
from casebench.runs.log import Result
from tests.judge.matching import picks


class Judge:
    """Lists the citations it is given, picks the first candidate, and says it supports."""

    config = JudgeConfig(provider="anthropic", model="judge")

    def __init__(self, listed: list[dict[str, Any]]) -> None:
        self.listed = listed
        self.asked: list[str] = []

    def ask(self, system: str, user: str) -> Any:
        self.asked.append(user)
        if system == prompts.LIST_CITATIONS:
            return self.listed
        if system == prompts.MATCH:
            return picks(user, lambda citation, candidates: candidates[0]["id"])
        return {"supports": True, "quote": "q", "reason": "r"}


def store(folder: Path, place: str) -> str:
    folder.mkdir(parents=True)
    # Every test citation shares a word with this text, so whichever store is searched finds it.
    text = "ruling Yargıtay Lov NJA Rt."
    document = {"id": "1", "jurisdiction": place, "court": "C", "date": "2024-01-02", "text": text}
    (folder / "1.json").write_text(json.dumps(document), encoding="utf-8")
    return str(folder)


def corpora(tmp_path: Path, **corpus: tuple[list[str], list[Holding]]) -> Corpora:
    """Named folder corpora, each with the jurisdictions and holdings given."""
    configs = {
        name.replace("_", "-"): CorpusConfig(
            connector="folder",
            jurisdictions=places,
            holds=holds,
            options={"path": store(tmp_path / name, places[0] if places else "GB")},
        )
        for name, (places, holds) in corpus.items()
    }
    return Corpora(configs, cache_root=tmp_path / "cache")


def case(place: str | None = None) -> Case:
    return Case(
        id="c",
        task=Task(type="qa"),
        reference=Reference(source=ReferenceSource.LAWYER),
        metrics=["citation_integrity"],
        provenance=Provenance(builder="lawyer", jurisdiction=place) if place else None,
    )


def checked(judge: Judge, stores: Corpora, place: str | None = None) -> Score:
    metric = CitationIntegrity(judge, stores, candidates=5)  # type: ignore[arg-type]
    return score(metric, case(place), Result(case_id="c", output="An answer."))


def test_a_citation_is_searched_only_in_the_corpus_for_its_jurisdiction(tmp_path: Path):
    stores = corpora(tmp_path, no_law=(["NO"], []), tr_courts=(["TR"], []))
    judge = Judge([{"citation": "Yargıtay 9. HD", "kind": "decision", "jurisdiction": "TR"}])

    result = checked(judge, stores)

    [check] = result.citations
    assert (check.label, check.document_id, check.routed) == (
        CitationLabel.VERIFIED,
        "tr-courts:1",
        Route.CITATION.value,
    )
    assert set(stores.opened) == {"tr-courts"}  # the Norwegian store was never searched


def test_a_citation_from_a_country_nobody_connected_is_unchecked(tmp_path: Path):
    stores = corpora(tmp_path, no_law=(["NO"], []), tr_courts=(["TR"], []))
    judge = Judge(
        [
            {"citation": "NJA 2019 s. 1", "kind": "decision", "jurisdiction": "SE"},
            {"citation": "Rt. 2010 s. 1", "kind": "decision", "jurisdiction": "no"},
        ]
    )

    result = checked(judge, stores)

    labels = {c.citation: c.label for c in result.citations}
    assert labels == {
        "NJA 2019 s. 1": CitationLabel.UNCHECKED,
        "Rt. 2010 s. 1": CitationLabel.VERIFIED,
    }
    assert result.value == 1.0  # the unchecked one does not count against the answer
    assert "no connected corpus holds decision for SE" in str(result.citations[0].reason)
    assert set(stores.opened) == {"no-law"}


def test_a_statute_goes_only_to_the_corpus_that_holds_statutes(tmp_path: Path):
    stores = corpora(
        tmp_path, no_statutes=(["NO"], ["statutes"]), no_courts=(["NO"], ["decisions"])
    )
    judge = Judge([{"citation": "Lov om ... § 15-7", "kind": "statute", "jurisdiction": "NO"}])

    result = checked(judge, stores)

    assert result.citations[0].document_id == "no-statutes:1"
    assert set(stores.opened) == {"no-statutes"}


def test_the_case_places_a_citation_the_judge_cannot(tmp_path: Path):
    stores = corpora(tmp_path, no_law=(["NO"], []), tr_courts=(["TR"], []))
    judge = Judge([{"citation": "the 2019 ruling", "kind": "decision", "jurisdiction": None}])

    result = checked(judge, stores, place="TR")

    assert (result.citations[0].document_id, result.citations[0].routed) == ("tr-courts:1", "case")
    assert set(stores.opened) == {"tr-courts"}


def test_with_no_jurisdiction_anywhere_every_corpus_is_searched(tmp_path: Path):
    stores = corpora(tmp_path, no_law=(["NO"], []), tr_courts=(["TR"], []))
    judge = Judge([{"citation": "the 2019 ruling", "kind": "decision", "jurisdiction": "Mars"}])

    result = checked(judge, stores)

    assert result.citations[0].routed == "all"
    assert set(stores.opened) == {"no-law", "tr-courts"}


def test_the_judge_is_told_which_codes_the_setup_covers(tmp_path: Path):
    two = corpora(tmp_path / "a", no_law=(["NO"], []), tr_courts=(["TR", "EU"], []))
    everywhere = corpora(tmp_path / "b", any_law=([], []))

    assert Resolver(Judge([]), two, 5).jurisdictions() == ["EU", "NO", "TR"]  # type: ignore[arg-type]
    assert prompts.list_citations("A.", ["EU", "NO"]).endswith("Jurisdiction codes: EU, NO")
    assert Resolver(Judge([]), everywhere, 5).jurisdictions() is None  # type: ignore[arg-type]
    assert prompts.list_citations("A.", None) == "Answer:\nA."


def test_a_country_covers_its_parts_but_a_part_covers_only_itself():
    assert covers(["US"], "US-CA") and covers([], "US-CA") and covers(["US-CA"], "US-CA")
    assert not covers(["US-CA"], "US") and not covers(["US-CA"], "US-NY")


def test_scores_are_reported_per_jurisdiction(tmp_path: Path):
    stores = corpora(tmp_path, no_law=(["NO"], []), tr_courts=(["TR"], []))
    judge = Judge([{"citation": "x", "kind": "decision", "jurisdiction": None}])
    scores = [checked(judge, stores, place) for place in ("NO", "TR", "TR", None)]

    [table] = build_tables(scores)

    assert [(row.jurisdiction, row.n) for row in table.rows] == [(None, 1), ("NO", 1), ("TR", 2)]
    printed = "\n".join(lines([table], scores))
    assert (
        "place" in printed and "searched by: 3 the case's jurisdiction, 1 every corpus" in printed
    )
