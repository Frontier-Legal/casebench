"""Every citation checked against the corpus: fabricated and misstated citations."""

import json
from pathlib import Path

import pytest

from casebench.core.case import Case, Reference, ReferenceSource, Task
from casebench.core.score import CitationLabel
from casebench.corpus.binding import CorpusConfig
from casebench.corpus.corpora import Corpora
from casebench.judge.client import Judge, read_json
from casebench.judge.config import JudgeConfig
from casebench.metrics.builtin.citation_integrity import CitationIntegrity
from casebench.report.citations import citation_rates
from casebench.runs.log import Result, RunInfo, RunLog
from casebench.runs.rescore import rescore
from tests.corpus.document_api import WORKS
from tests.judge.fake_judge import FakeJudge, start_fake_judge

ANSWER = (
    "The dismissal is invalid: see Yargıtay 9. HD, E. 2023/1234 K. 2024/567 and Yargıtay 22. HD,"
    " E. 2022/77 K. 2023/90. Notice may be waived orally (Yargıtay 3. HD, E. 2021/999 K. 2022/1)."
)


def folder_corpus(tmp_path: Path) -> Corpora:
    store = tmp_path / "decisions"
    store.mkdir()
    for work_id, work in WORKS.items():
        (store / f"{work_id}.json").write_text(
            json.dumps(
                {
                    "id": work_id,
                    "jurisdiction": "TR",
                    "court": work["court"] or "",
                    "date": work["decided"],
                    "text": work["text"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    return Corpora(
        {"corpus": CorpusConfig(connector="folder", options={"path": str(store)})},
        cache_root=tmp_path / "cache",
    )


def test_fabricated_and_misstated_citations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    server = start_fake_judge()
    judge = Judge(
        JudgeConfig(
            provider="anthropic",
            model="claude-sonnet-5-5",
            options={"base_url": f"http://127.0.0.1:{server.server_port}", "max_tokens": 1024},
        )
    )
    metric = CitationIntegrity(judge, folder_corpus(tmp_path), candidates=5)
    case = Case(
        id="c1",
        task=Task.model_validate({"type": "qa", "question": "Valid?"}),
        reference=Reference(source=ReferenceSource.LAWYER),
        metrics=["citation_integrity"],
    )
    log = RunLog.create(
        tmp_path / "run", RunInfo(run_id="r", suite_id="s", suite_hash="h", target="t")
    )
    log.append(Result(case_id="c1", output=ANSWER))
    try:
        [score] = RunLog.read_scores(rescore(log, [case], [metric]))
    finally:
        server.shutdown()

    labels = {c.citation: (c.label, c.document_id) for c in score.citations}
    assert labels == {
        "Yargıtay 9. HD, E. 2023/1234 K. 2024/567": (CitationLabel.VERIFIED, "corpus:101"),
        "Yargıtay 22. HD, E. 2022/77 K. 2023/90": (CitationLabel.MISGROUNDED, "corpus:102"),
        "Yargıtay 3. HD, E. 2021/999 K. 2022/1": (CitationLabel.FABRICATED, None),
    }
    verified = next(c for c in score.citations if c.label is CitationLabel.VERIFIED)
    assert verified.quote == "İşçinin feshi geçersizdir."
    assert score.value == pytest.approx(1 / 3)
    assert score.label == "1 verified, 1 misgrounded, 1 fabricated"
    rates = {r.label: (r.count, r.rate) for r in citation_rates([score])}
    assert rates[CitationLabel.FABRICATED] == (1, pytest.approx(1 / 3))
    assert rates[CitationLabel.MISGROUNDED] == (1, pytest.approx(1 / 3))
    assert rates[CitationLabel.VERIFIED] == (1, pytest.approx(1 / 3))
    assert len(FakeJudge.calls) == 1 + 3 + 2  # list, match each, weigh each found one


def test_a_judge_reply_in_a_fenced_block_is_read():
    assert read_json('Here you are:\n```json\n[{"citation": "x", "claim": "y"}]\n```') == [
        {"citation": "x", "claim": "y"}
    ]
