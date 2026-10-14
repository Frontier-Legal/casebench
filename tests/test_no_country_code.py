"""No country-specific code: any jurisdiction works with no plugin."""

from pathlib import Path

from casebench.corpus.binding import CorpusConfig
from casebench.plugins.kinds import KINDS
from tests.plugins.boundary import plugin_leaks

ROOT = Path(__file__).resolve().parents[1]


def test_no_country_in_the_core():
    assert all("jurisdiction" not in kind.name and "adapter" not in kind.name for kind in KINDS)
    for folder in ("jurisdictions", "adapters"):
        assert not list((ROOT / "casebench" / folder).glob("**/*.py")), folder
    assert set(CorpusConfig.model_fields) == {
        "connector",
        "jurisdictions",  # ISO 3166 codes, the same for every country (decision 0036)
        "holds",
        "options",
        "connector_source",
        "profile",  # which profile file the options came from, by name
        "metered",  # what the provider charges for, so paid searches are kept
        "search_filters",  # per kind of citation the judge names, statute or decision (0037)
        "keep",  # what the provider's terms let Casebench keep on disk (0041)
    }
    assert plugin_leaks(ROOT) == []
