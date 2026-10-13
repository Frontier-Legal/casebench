"""Several corpora in one setup: named, kept apart by qualified ids, sharing jurisdiction codes."""

import json
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from casebench.cli import main
from casebench.config import ConfigError, load_config
from casebench.core.jurisdiction import UnknownJurisdiction, code
from casebench.corpus.corpora import Corpora
from casebench.report.funnel import as_corpus_ids
from tests.corpus.profiles import http_options, profile


def store(folder: Path, jurisdiction: str, text: str) -> Path:
    """A folder store whose one document is `101`, as two unrelated providers may both have."""
    folder.mkdir()
    document = {"id": "101", "jurisdiction": jurisdiction, "court": "Court", "date": "2024-01-02"}
    (folder / "101.json").write_text(json.dumps({**document, "text": text}), encoding="utf-8")
    return folder


def two_providers(tmp_path: Path) -> Path:
    config = tmp_path / "casebench.yaml"
    norway = store(tmp_path / "no", "NO", "Høyesterett: anken forkastes.")
    turkey = store(tmp_path / "tr", "TR", "Yargıtay: kararın bozulmasına.")
    config.write_text(
        yaml.safe_dump(
            {
                "corpora": {
                    "no-courts": {
                        "connector": "folder",
                        "jurisdictions": ["no"],
                        "options": {"path": str(norway)},
                    },
                    "tr-courts": {
                        "connector": "folder",
                        "jurisdictions": ["TR"],
                        "options": {"path": str(turkey)},
                    },
                }
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return config


def test_jurisdiction_codes_are_iso_3166_or_eu():
    assert [code(c) for c in ("no", " TR ", "us-ca", "EU")] == ["NO", "TR", "US-CA", "EU"]
    assert [code(c) for c in ("UK", "EL")] == ["GB", "GR"]  # as the ECLI writes them
    for written in ("Norway", "nor", "XK", "EU-FR", "US-CALIF"):
        with pytest.raises(UnknownJurisdiction, match="ISO 3166-1 alpha-2 such as NO"):
            code(written)


def test_two_providers_with_the_same_id_stay_apart(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    config = load_config(two_providers(tmp_path))
    corpora = Corpora(config.corpora)

    assert config.corpora["no-courts"].jurisdictions == ["NO"]
    assert corpora.named("no-courts").decision_ids() == ["no-courts:101"]
    assert corpora.named("tr-courts").decision_ids() == ["tr-courts:101"]
    assert corpora.raw("no-courts:101")["text"].startswith("Høyesterett")
    assert corpora.raw("tr-courts:101")["text"].startswith("Yargıtay")
    decision = corpora.decision("tr-courts:101")
    assert (decision.id, decision.jurisdiction) == ("tr-courts:101", "TR")


def test_a_single_corpus_is_named_corpus(tmp_path: Path):
    config = tmp_path / "casebench.yaml"
    config.write_text("corpus: {connector: folder, options: {path: x}}\n", encoding="utf-8")
    assert list(load_config(config).corpora) == ["corpus"]

    config.write_text(
        "corpus: {connector: folder}\ncorpora: {other: {connector: folder}}\n", encoding="utf-8"
    )
    with pytest.raises(ConfigError, match="not both"):
        load_config(config)

    config.write_text("corpora: {Bad Name: {connector: folder}}\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="corpora"):
        load_config(config)

    config.write_text("corpus: {connector: folder, jurisdictions: [Norway]}\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="not a jurisdiction code"):
        load_config(config)


def test_a_command_that_reads_one_corpus_asks_which(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    two_providers(tmp_path)

    unnamed = CliRunner().invoke(main, ["corpus", "check"])
    named = CliRunner().invoke(main, ["corpus", "check", "--corpus", "tr-courts"])
    unknown = CliRunner().invoke(main, ["corpus", "check", "--corpus", "se-courts"])

    assert unnamed.exit_code == 1
    assert "name the corpus with --corpus; the config has: no-courts, tr-courts" in unnamed.output
    assert named.exit_code == 0, named.output
    assert "sampled 1 documents" in named.output
    assert "no corpus named se-courts (it has: no-courts, tr-courts)" in unknown.output


def test_providers_are_added_one_after_another_with_their_jurisdictions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DOC_KEY", "k")
    first = profile(tmp_path, "http", http_options("http://a.example"), file_name="no-law.yaml")
    second = profile(tmp_path, "http", http_options("http://b.example"), file_name="tr-law.yaml")
    monkeypatch.setattr(
        "casebench.corpus.from_profile._check", lambda profile: "1"
    )  # the live check is the profile tests' subject; here only the writing is

    for path in (first, second):
        added = CliRunner().invoke(main, ["corpus", "add", "profile", str(path)])
        assert added.exit_code == 0, added.output
    written = yaml.safe_load((tmp_path / "casebench.yaml").read_text(encoding="utf-8"))

    assert set(written["corpora"]) == {"no-law", "tr-law"}
    assert written["corpora"]["tr-law"]["jurisdictions"] == ["TR"]
    assert written["corpora"]["no-law"]["profile"] == "no-law.yaml"


def test_a_profile_with_an_unknown_jurisdiction_is_refused(tmp_path: Path):
    path = profile(tmp_path, "http", http_options("http://a.example"), jurisdictions=["Norway"])

    ran = CliRunner().invoke(main, ["validate", str(path)])

    assert ran.exit_code == 1
    assert "not a jurisdiction code" in ran.output


def test_an_agents_own_id_is_matched_to_the_one_corpus_that_holds_it():
    known = {"no-courts:101", "tr-courts:202", "tr-courts:303", "no-courts:303"}

    found = as_corpus_ids({"101", "202", "303", "tr-courts:303", "999"}, known)

    # 101 and 202 are each one corpus's; 303 is in two, so it stays as the agent wrote it.
    assert found == {"no-courts:101", "tr-courts:202", "303", "tr-courts:303", "999"}
