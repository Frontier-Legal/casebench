"""One setup across countries: keys kept per corpus, mixed suites, init and the dry run."""

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from click.testing import CliRunner

from casebench.cli import main
from casebench.config import CasebenchConfig
from casebench.core.case import Evidence, Fact
from casebench.extract.run import KEYS_FILE, Extraction, read_keys, write
from casebench.references.court import AnswerKey
from casebench.runs.dry_run import estimate
from casebench.suites.court import cases_for
from casebench.suites.freeze import load
from tests.corpus.profiles import http_options, profile


def key(corpus: str, number: int, place: str) -> AnswerKey:
    decision = f"{corpus}:{number}"
    return AnswerKey(
        decision_id=decision,
        jurisdiction=place,
        inputs={"facts": f"Facts of case {number}."},
        facts=[
            Fact(
                id="outcome",
                kind="outcome",
                value="reversed" if number % 2 else "upheld",
                evidence=Evidence(doc=decision, quote="The court ruled."),
            )
        ],
    )


def extracted(folder: Path, corpus: str, place: str, numbers: range) -> None:
    """What `casebench extract --corpus <corpus>` writes, without reading any decision."""
    result = Extraction(decisions=len(numbers), keys=[key(corpus, n, place) for n in numbers])
    model = SimpleNamespace(
        config=SimpleNamespace(provider="p", model="m"),
        settings={},
        calls=0,
        input_tokens=0,
        output_tokens=0,
        cost=None,
    )
    write(result, [model], folder, corpus)  # type: ignore[list-item]


def test_extracting_from_a_second_corpus_keeps_the_first_ones_keys(tmp_path: Path):
    extracted(tmp_path, "no-law", "NO", range(3))
    extracted(tmp_path, "tr-courts", "TR", range(2))
    extracted(tmp_path, "no-law", "NO", range(10, 12))  # extracting again replaces its own keys

    ids = sorted(k.decision_id for k in read_keys(tmp_path))

    assert ids == ["no-law:10", "no-law:11", "tr-courts:0", "tr-courts:1"]
    assert (tmp_path / KEYS_FILE).is_file()


def test_a_suite_mixes_corpora_in_the_shares_asked_for(tmp_path: Path):
    keys = tmp_path / "keys"
    extracted(keys, "no-law", "NO", range(6))
    extracted(keys, "tr-courts", "TR", range(6))

    made = CliRunner().invoke(
        main,
        [
            "generate",
            "--keys",
            str(keys),
            "--types",
            "outcome",
            "--corpus",
            "no-law=3",
            "--corpus",
            "tr-courts=2",
            "--suite-id",
            "two-countries",
            "--out",
            str(tmp_path / "suite"),
        ],
    )

    assert made.exit_code == 0, made.output
    manifest, cases = load(tmp_path / "suite")
    assert manifest.corpora == {"no-law": 3, "tr-courts": 2}
    assert manifest.jurisdictions == {"NO": 3, "TR": 2}
    assert manifest.generation["corpora"]["no-law"]["requested"] == 3
    assert "from corpora {'no-law': 3, 'tr-courts': 2}" in made.output
    assert len({c.id for c in cases}) == 5


@pytest.mark.parametrize(
    ("flags", "says"),
    [
        ([], "give --n for a suite from every corpus, or --corpus NAME=COUNT"),
        (["--n", "2", "--corpus", "no-law=1"], "give --n for a suite from every corpus"),
        (["--corpus", "se-law=1"], "no answer keys come from corpus se-law"),
        (["--corpus", "no-law"], "give each corpus once, as NAME=COUNT"),
    ],
)
def test_a_mixed_suite_says_what_it_needs(tmp_path: Path, flags: list[str], says: str):
    extracted(tmp_path, "no-law", "NO", range(2))
    args = ["generate", "--keys", str(tmp_path), "--types", "outcome", "--suite-id", "s"]

    made = CliRunner().invoke(main, [*args, "--out", str(tmp_path / "suite"), *flags])

    assert made.exit_code != 0
    assert says in made.output


def test_init_connects_one_provider_per_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DOC_KEY", "k")
    monkeypatch.setattr("casebench.corpus.from_profile._check", lambda profile: "1")
    (tmp_path / "agent.py").write_text("def answer(q: str) -> str:\n    return 'x'\n", "utf-8")
    norway = profile(tmp_path, "http", http_options("http://a.example"), "no-law.yaml")
    turkey = profile(tmp_path, "http", http_options("http://b.example"), "tr-law.yaml")

    setup = ["init", "--target", "python", "--entry", "agent.py:answer", "--no-live", "--yes"]
    ran = CliRunner().invoke(
        main,
        [*setup, "--no-judge", "--no-extract", "--profile", str(norway), "--profile", str(turkey)],
    )

    assert ran.exit_code == 0, ran.output
    written = yaml.safe_load((tmp_path / "casebench.yaml").read_text(encoding="utf-8"))
    assert list(written["corpora"]) == ["no-law", "tr-law"]


def test_the_dry_run_shows_each_providers_share(tmp_path: Path):
    config = CasebenchConfig.model_validate(
        {
            "judge": {"provider": "anthropic", "model": "m"},
            "corpora": {
                "no-law": {"connector": "folder", "jurisdictions": ["NO"]},
                "tr-courts": {"connector": "folder", "jurisdictions": ["TR"]},
            },
        }
    )
    cases = []
    for corpus, place, count in (("no-law", "NO", 3), ("tr-courts", "TR", 1)):
        for number in range(count):
            case = cases_for(key(corpus, number, place), "outcome")
            assert case is not None
            cases.append(case.model_copy(update={"metrics": ["citation_integrity"]}))

    printed = "\n".join(estimate(cases, set(), config, tmp_path).lines())

    assert "no-law: searched for the citations in up to 3 answers" in printed
    assert "tr-courts: searched for the citations in up to 1 answers" in printed
