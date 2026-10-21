"""Every test starts with no key named or seen, no perimeter and no price list from the
network, whatever ran before it."""

import pytest

from casebench import keys, network
from casebench.pricing import lookup


def _offline() -> dict:
    raise OSError("tests read no price list from the network")


@pytest.fixture(autouse=True)
def _no_perimeter_or_keys(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(keys, "_named", set())
    monkeypatch.setattr(keys, "_seen", set())
    yield
    network.release()


@pytest.fixture(autouse=True)
def _no_price_lists(monkeypatch: pytest.MonkeyPatch):
    """A test prices its models in its config; a test of the lookup gives its own lists."""
    monkeypatch.setattr(lookup, "_openrouter", _offline)
    monkeypatch.setattr(lookup, "_catalog", _offline)
