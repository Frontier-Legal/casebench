"""Scoring finishes on a real corpus: the judge matches citations from the corpus's own
description of each document (decision 0037)."""

import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

import httpx2
import pytest
import yaml
from click.testing import CliRunner

from casebench.cli import main
from casebench.config import CasebenchConfig, load_config
from casebench.core.case import Case, Reference, ReferenceSource, Task
from casebench.corpus.binding import Cited, CorpusConfig
from casebench.corpus.corpora import Corpora
from casebench.judge import prompts
from casebench.judge.config import JudgeConfig
from casebench.judge.memo import MEMO_FILE
from casebench.judge.resolve import Resolver
from casebench.metrics.builtin.citation_integrity import CitationIntegrity
from casebench.providers import send
from casebench.providers.interface import HttpRequest
from casebench.report.render import error_lines
from casebench.runs.log import Result, RunInfo, RunLog
from casebench.runs.scoring import score
from casebench.suites.freeze import load
from tests.corpus.document_api import KEY, DocumentApi, start_document_api
from tests.judge.matching import asked, picks
from tests.report.suites import frozen, outcome_case


class RecordingJudge:
    """Lists the citations it is given, takes the first candidate, and keeps every prompt."""

    config = JudgeConfig(provider="anthropic", model="judge")

    def __init__(self, listed: list[dict[str, Any]] | None = None) -> None:
        self.listed = listed or []
        self.matching: list[str] = []

    def ask(self, system: str, user: str) -> Any:
        if system == prompts.LIST_CITATIONS:
            return self.listed
        if system == prompts.MATCH:
            self.matching.append(user)
            return picks(user, lambda citation, candidates: candidates[0]["id"])
        return {"supports": True, "quote": "q", "reason": "r"}


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("DOC_KEY", KEY)
    monkeypatch.chdir(tmp_path)
    server = start_document_api()
    yield f"http://127.0.0.1:{server.server_port}/v1"
    server.shutdown()


def invoke(*args: str):
    return CliRunner().invoke(main, list(args))


def lawyer_case(number: int) -> Case:
    return Case(
        id=f"c{number}",
        task=Task.model_validate({"type": "qa", "question": "Is the dismissal valid?"}),
        reference=Reference(source=ReferenceSource.LAWYER),
        metrics=["citation_integrity"],
    )


def decisions(folder: Path, count: int) -> Path:
    """One decision per docket number, E. 2024/1 to E. 2024/<count>."""
    folder.mkdir()
    for n in range(1, count + 1):
        document = {
            "id": str(n),
            "jurisdiction": "TR",
            "court": "Yargıtay",
            "date": "2024-01-02",
            "text": f"E. 2024/{n} K. 2025/{n}. Fesih geçersizdir.",
        }
        (folder / f"{n}.json").write_text(json.dumps(document), encoding="utf-8")
    return folder


def stored_run(tmp_path: Path, outputs: list[str]) -> tuple[RunLog, list[Case]]:
    cases = [lawyer_case(n) for n in range(1, len(outputs) + 1)]
    log = RunLog.create(
        tmp_path / "runs" / "r", RunInfo(run_id="r", suite_id="s", suite_hash="h", target="t")
    )
    for case, output in zip(cases, outputs, strict=True):
        log.append(Result(case_id=case.id, output=output))
    return log, cases


def judged_config(port: int, store: Path) -> CasebenchConfig:
    options = {"base_url": f"http://127.0.0.1:{port}", "max_tokens": 1024}
    return CasebenchConfig(
        judges=[JudgeConfig(provider="anthropic", model="judge-model", options=options)],
        corpora={"corpus": CorpusConfig(connector="folder", options={"path": str(store)})},
    )


class ScriptedJudge(BaseHTTPRequestHandler):
    """A judge over the Messages API whose answers a test scripts per prompt."""

    answer: ClassVar[Any] = None

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        reply = type(self).answer(self, body["system"], body["messages"][0]["content"])
        if reply is None:
            return
        text = json.dumps(reply, ensure_ascii=False)
        payload = json.dumps(
            {"content": [{"type": "text", "text": text}], "usage": {}}, ensure_ascii=False
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return None


def serve(answer: Any) -> ThreadingHTTPServer:
    handler = type("Judge", (ScriptedJudge,), {"answer": staticmethod(answer)})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def reasonable(system: str, user: str) -> Any:
    """Lists the docket number the answer cites, picks the first candidate, finds it supported."""
    if system == prompts.LIST_CITATIONS:
        docket = user.split("Answer:\n", 1)[1].split("\n")[0]
        return [{"citation": docket, "claim": "invalid", "kind": "decision"}]
    if system == prompts.MATCH:
        return picks(user, lambda citation, candidates: candidates[0]["id"])
    return {"supports": True, "quote": "Fesih geçersizdir.", "reason": "read it"}


def test_candidates_are_shown_by_the_corpus_s_own_description(api: str, tmp_path: Path):
    config = tmp_path / "casebench.yaml"
    flags = ["--search-path", "/search", "--fetch-path", "/documents/{id}"]
    flags += ["--header", "Authorization=Bearer ${DOC_KEY}", "--probe", "feshi", "--yes"]

    added = invoke("corpus", "add", "http", "--base-url", api, "--config", str(config), *flags)
    checked = invoke("corpus", "check", "--config", str(config), "--query", "feshi")
    checked_statute = invoke("corpus", "check", "--config", str(config), "--query", "Kanunu")
    DocumentApi.fetches.clear()
    judge = RecordingJudge()
    corpora = Corpora(load_config(config).corpora, cache_root=tmp_path / "nothing-cached")
    resolver = Resolver(judge, corpora, candidates=5)  # type: ignore[arg-type]
    resolver.resolve("Yargıtay 9. HD, E. 2023/1234 K. 2024/567")

    assert added.exit_code == 0, added.output
    [corpus] = yaml.safe_load(config.read_text(encoding="utf-8"))["corpora"].values()
    assert corpus["options"]["result_fields"] == {
        "id": "$.work.work_id",
        "citation": "$.citation",
        "type": "$.document_type",
        "passage": "$.highlight",
    }
    assert "the judge sees each result's citation, type, passage" in added.output
    assert "missing in some results" not in checked.output
    assert "missing in some results: citation" in checked_statute.output
    [prompt] = judge.matching
    [cited] = asked(prompt)
    assert cited["candidates"] == [
        {
            "id": "127-0-0-1:101",
            "citation": "Yargıtay 9. Hukuk Dairesi, E. 2023/1234 K. 2024/567, 12.03.2024",
            "type": "case_law",
            "passage": "E. 2023/1234 K. 2024/567. İşçinin feshi geçersizdir. HÜKÜM: Bozulmasına.",
        },
        {
            "id": "127-0-0-1:102",
            "citation": "Yargıtay 22. Hukuk Dairesi, E. 2022/77 K. 2023/90, 02.05.2024",
            "type": "case_law",
            "passage": "E. 2022/77 K. 2023/90. Kıdem tazminatı. HÜKÜM: Onanmasına.",
        },
    ]
    assert DocumentApi.fetches == {}  # matched on the description alone, no document fetched


def test_one_matching_call_per_answer(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    corpus = Corpora(
        {
            "corpus": CorpusConfig(
                connector="folder", options={"path": str(decisions(tmp_path / "d", 29))}
            )
        },
        cache_root=tmp_path / "cache",
    )
    searched: list[str] = []
    search = corpus.search_results
    monkeypatch.setattr(
        corpus, "search_results", lambda text, *rest: searched.append(text) or search(text, *rest)
    )
    listed = [{"citation": f"Yargıtay, E. 2024/{n}", "claim": "c"} for n in range(1, 30)]
    judge = RecordingJudge(listed)

    metric = CitationIntegrity(judge, corpus, candidates=5)  # type: ignore[arg-type]
    verdict = metric.judge(lawyer_case(1), Result(case_id="c1", output="It cites 29 decisions."))

    assert len(verdict.citations) == 29
    assert len(judge.matching) == 1
    assert len(asked(judge.matching[0])) == 29
    assert searched == [item["citation"] for item in listed]


def test_cases_are_scored_in_parallel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)
    log, cases = stored_run(tmp_path, [f"E. 2024/{n}" for n in range(1, 9)])
    # Each listing call waits until four are in flight: one case at a time would never get past.
    together = threading.Barrier(4, timeout=10)
    kept_while_scoring: list[int] = []

    def answer(handler: Any, system: str, user: str) -> Any:
        if system == prompts.LIST_CITATIONS:
            memo = log.folder / MEMO_FILE
            kept_while_scoring.append(len(memo.read_text().splitlines()) if memo.is_file() else 0)
            together.wait()
        return reasonable(system, user)

    server = serve(answer)
    try:
        config = judged_config(server.server_port, decisions(tmp_path / "d", 8))
        scored = score(log, cases, config, "s", concurrency=4)
    finally:
        server.shutdown()

    assert scored.errors == []
    assert [s.case_id for s in scored.scores] == [case.id for case in cases]
    assert all(s.value == 1.0 for s in scored.scores)
    assert max(kept_while_scoring) > 0  # replies were on disk before the last cases were listed


def test_a_dropped_or_stalled_call(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(send, "TIMEOUT", httpx2.Timeout(0.5))
    monkeypatch.setattr(send, "FIRST_WAIT_S", 0.0)
    log, cases = stored_run(tmp_path, ["E. 2024/1", "E. 2024/2 dropped", "E. 2024/3 stalled"])
    broken = {"now": True}
    listed: list[str] = []

    def answer(handler: Any, system: str, user: str) -> Any:
        if system == prompts.LIST_CITATIONS:
            listed.append(user.split("Answer:\n", 1)[1].split("\n")[0])
            if broken["now"] and "dropped" in user:
                handler.connection.shutdown(socket.SHUT_RDWR)
                return None
            if broken["now"] and "stalled" in user:
                time.sleep(1.5)
                return None
        return reasonable(system, user)

    server = serve(answer)
    try:
        config = judged_config(server.server_port, decisions(tmp_path / "d", 3))
        first = score(log, cases, config, "s")
        broken["now"] = False
        asked_first, listed[:] = list(listed), []
        again = score(log, cases, config, "s")
    finally:
        server.shutdown()

    assert asked_first.count("E. 2024/2 dropped") == 1 + send.RETRIES
    assert asked_first.count("E. 2024/3 stalled") == 1 + send.RETRIES
    assert [s.case_id for s in first.scores] == ["c1"]
    assert {(e.case_id, e.metric) for e in first.errors} == {
        ("c2", "citation_integrity"),
        ("c3", "citation_integrity"),
    }
    assert (
        "run again with --run-id r to score only what is missing"
        in error_lines(first.errors, "r")[0]
    )
    assert sorted(listed) == ["E. 2024/2 dropped", "E. 2024/3 stalled"]  # c1 came from the memo
    assert [s.case_id for s in again.scores] == ["c1", "c2", "c3"]
    assert again.errors == []


def test_a_statute_resolves_to_legislation(api: str, tmp_path: Path):
    options = {
        "base_url": api,
        "headers": {"Authorization": "Bearer ${DOC_KEY}"},
        "search_path": "/search",
        "fetch_path": "/documents/{id}",
        "search_results": "$.results[*]",
        "result_fields": {"id": "$.work.work_id", "type": "$.document_type"},
        "fields": {"id": "$.work_id", "text": "$.expressions[0].text"},
    }
    filters: dict[Cited, dict[str, Any]] = {
        "statute": {"type": "legislation"},
        "decision": {"type": "case_law"},
    }
    config = CorpusConfig(connector="http", options=options, search_filters=filters)
    resolver = Resolver(RecordingJudge(), Corpora({"tr": config}), candidates=5)  # type: ignore[arg-type]

    # The statute's words are in a decision too: unfiltered, the decision comes back first.
    statute = resolver.resolve("İş Kanunu madde 18, feshi", kind="statute")
    decision = resolver.resolve("İş Kanunu madde 18, feshi", kind="decision")

    assert statute.document_id == "tr:103"
    assert decision.document_id == "tr:101"
    assert DocumentApi.filtered == ["legislation", "case_law"]


def test_the_first_real_run_reports(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    started = tmp_path / "agent-started"
    agent = tmp_path / "agent.py"
    agent.write_text(
        f"open({str(started)!r}, 'w').close()\n\ndef answer(question, facts):\n    return 'x'\n",
        encoding="utf-8",
    )
    (tmp_path / "casebench.yaml").write_text(
        "target: {type: python, entry: agent.py:answer}\n", encoding="utf-8"
    )
    cases = [outcome_case(n, "upheld", "The lower court weighed it.") for n in range(5)]
    suite = frozen(cases, tmp_path / "suite")
    manifest, _ = load(suite)
    info = RunInfo(
        run_id="first-5", suite_id=manifest.suite_id, suite_hash=manifest.content_hash, target="t"
    )
    log = RunLog.create(tmp_path / ".casebench" / "runs" / "first-5", info)
    for case in cases:
        log.append(Result(case_id=case.id, output="The decision is upheld."))

    ran = invoke("run", "--suite", str(suite), "--run-id", "first-5", "--no-capture")

    assert ran.exit_code == 0, ran.output
    assert "0 cases sent, 5 stored" in ran.output
    assert "outcome · outcome" in ran.output
    assert (log.folder / "report.json").is_file()
    assert not started.exists()  # the agent was never started


def test_a_wait_longer_than_the_vendor_s_sdk_honours_is_not_retried():
    asks: list[str] = []
    body = {"system": "s", "messages": [{"content": "a busy server"}]}

    def busy(handler: Any, system: str, user: str) -> Any:
        asks.append(user)
        handler.send_response(429)
        handler.send_header("retry-after", "300")
        handler.send_header("Content-Length", "2")
        handler.end_headers()
        handler.wfile.write(b"{}")
        return None

    waited: list[float] = []
    server = serve(busy)
    try:
        url = f"http://127.0.0.1:{server.server_port}"
        for longest in (120.0, None):
            request = HttpRequest(method="POST", url=url, body=body, longest_retry_after_s=longest)
            status, _ = send.send(request, sleep=waited.append)
            assert status == 429
    finally:
        server.shutdown()

    # openai's SDK gives up on a five-minute wait; anthropic's waits it out, twice.
    assert len(asks) == 1 + (1 + send.RETRIES)
    assert waited == [300.0, 300.0]
