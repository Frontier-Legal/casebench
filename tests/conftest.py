"""Every test starts with no key named or seen, and no perimeter, whatever ran before it."""

import pytest

from casebench import keys, network


@pytest.fixture(autouse=True)
def _no_perimeter_or_keys(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(keys, "_named", set())
    monkeypatch.setattr(keys, "_seen", set())
    yield
    network.release()
