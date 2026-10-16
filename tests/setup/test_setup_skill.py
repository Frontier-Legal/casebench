"""The setup skill a coding agent installs: one prompt sets Casebench up and runs it (0061)."""

import re
from pathlib import Path

import yaml

from casebench.cli import main
from casebench.setup.guide_cli import guide_command

SKILL = Path(__file__).parents[2] / "skills" / "casebench-setup" / "SKILL.md"
GUIDE = Path(__file__).parents[2] / "casebench" / "setup" / "guide.md"
# The Agent Skills format: a lowercase, hyphenated name of at most 64 characters, matching its
# folder, and a description of at most 1024 characters that says when to use the skill.
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def test_one_prompt():
    text = SKILL.read_text(encoding="utf-8")
    _, front, body = text.split("---\n", 2)
    meta = yaml.safe_load(front)
    named = set(re.findall(r"`(?:uvx )?casebench ([a-z]+)", body))

    assert set(meta) == {"name", "description"}
    assert meta["name"] == SKILL.parent.name and NAME.match(meta["name"])
    assert len(meta["name"]) <= 64 and len(meta["description"]) <= 1024
    assert "Use when" in meta["description"]
    # It points to the guide, which holds the steps, so the two never disagree.
    assert "casebench guide" in body and guide_command.name == "guide"
    # Every command it names is one Casebench has.
    assert named and named <= set(main.commands)
    # The user is asked the corpus, the judge and whether to spend on the first suite.
    assert "Ask the user only two things" in body
    assert "casebench run --yes" in body and "casebench ui" in body


def test_the_coding_agent_asks_about_a_team_server():
    _, _, body = SKILL.read_text(encoding="utf-8").split("---\n", 2)
    steps = GUIDE.read_text(encoding="utf-8")
    asked = body.split("## 4. Ask about a team server", 1)[1].split("\n## ", 1)[0]
    told = steps.split("## A team server", 1)[1]
    init = next(p for p in main.commands["init"].params if p.name == "team_server")

    # After the first evaluation, once; with an address, init names it and the key is the
    # user's to set; the agent checks, pushes and offers to invite; it installs nothing itself.
    assert body.index("## 2. Run the first evaluation") < body.index("## 4. Ask about a team")
    assert "will lawyers review on a team server?" in asked
    for said in (asked, told):
        assert "casebench init --team-server URL --no-routes --yes" in said
        assert "CASEBENCH_CLOUD_KEY" in said and "Team page" in said
        assert "casebench check" in said and "casebench push" in said
        assert "casebench invite" in said
        assert "only if the user asks" in said
    assert "pip install casebench-ee" in told and "casebench-team serve" in told
    assert "never read, print or write it" in told
    assert init.opts == ["--team-server"]
