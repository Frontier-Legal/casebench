"""No country-specific code: any jurisdiction works with no plugin."""

from pathlib import Path

from casebench.corpus.binding import CorpusConfig
from casebench.plugins.kinds import KINDS
from tests.plugins.boundary import plugin_leaks

ROOT = Path(__file__).resolve().parents[1]


def test_no_country_in_the_core():
    assert all("jurisdiction" not in kind.name and "adapter" not in kind.name for kind in KINDS)
    assert not (ROOT / "casebench" / "jurisdictions").exists()
    assert not (ROOT / "casebench" / "adapters").exists()
    assert set(CorpusConfig.model_fields) == {
        "connector",
        "jurisdiction",
        "options",
        "connector_source",
    }
    assert plugin_leaks(ROOT) == []
