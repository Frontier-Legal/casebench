"""Entry points are read the same way on every operating system."""

import pytest

from casebench.targets.builtin.python.entry import split_entry


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ("firm.agent:answer", ("firm.agent", "answer", False)),
        ("agent.py", ("agent.py", "answer", True)),
        ("agents/agent.py:respond", ("agents/agent.py", "respond", True)),
        (r"C:\agents\agent.py", (r"C:\agents\agent.py", "answer", True)),
        (r"C:\agents\agent.py:respond", (r"C:\agents\agent.py", "respond", True)),
    ],
)
def test_an_entry_names_its_module_or_file_and_function(entry: str, expected: tuple):
    assert split_entry(entry) == expected


@pytest.mark.parametrize("entry", ["firm.agent", ":answer", "firm.agent:"])
def test_an_entry_without_a_function_is_refused(entry: str):
    with pytest.raises(ValueError, match="must look like"):
        split_entry(entry)
