"""The guide `casebench guide` prints tells a coding agent only what this version can do (0044)."""

import re
from pathlib import Path

import click
import yaml

from casebench.cli import main
from casebench.config import config_from

GUIDE = Path(__file__).parents[2] / "casebench" / "setup" / "guide.md"
# `casebench` and the words after it, which name a command and, in a group, its subcommands.
NAMED = re.compile(r"\bcasebench((?: [a-z][a-z-]*){1,3})")
YAML_BLOCK = re.compile(r"```yaml\n(.*?)```", re.DOTALL)


def _missing(words: list[str]) -> str | None:
    """The command the words start with, when one of them names none; words after a command
    that takes no subcommand are its arguments or the sentence."""
    command: click.Command = main
    for depth, word in enumerate(words):
        if not isinstance(command, click.Group):
            return None
        found = command.commands.get(word)
        if found is None:
            return " ".join(words[: depth + 1])
        command = found
    return None


def test_the_guide_connects_a_folder_with_what_casebench_has(tmp_path: Path):
    steps = GUIDE.read_text(encoding="utf-8")
    missing = [
        said
        for match in NAMED.finditer(steps)
        if (said := _missing(match.group(1).split())) is not None
    ]
    folder_step = steps.split("For a folder of decisions", 1)[1].split("\n## ", 1)[0]
    [block] = YAML_BLOCK.findall(folder_step)
    written = block.replace("PATH", str(tmp_path)).replace("CODE", "TR")
    config = config_from(yaml.safe_load(written), tmp_path, "casebench.yaml")

    assert NAMED.search(steps)
    assert missing == []  # every command and subcommand it names is one Casebench has
    [corpus] = config.corpora.values()
    assert corpus.connector == "folder" and corpus.options == {"path": str(tmp_path)}


def test_the_guide_writes_no_price_into_casebench_yaml(tmp_path: Path):
    steps = GUIDE.read_text(encoding="utf-8")
    setup = steps.split("## 5. Write the setup", 1)[1].split("\n## ", 1)[0]
    blocks = [yaml.safe_load(block) for block in YAML_BLOCK.findall(setup)]
    [models] = [block["agent_models"] for block in blocks if "agent_models" in block]
    config = config_from({"agent_models": models}, tmp_path, "casebench.yaml")

    # A run looks each price up from where the model is sold (decision 0069).
    assert all(set(model) == {"model", "family"} for model in models)
    assert "price:" not in setup
    assert [model.family for model in config.agent_models] == ["FAMILY"]
