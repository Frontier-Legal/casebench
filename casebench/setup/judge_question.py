"""Ask for a model Casebench calls itself, find its key, and have it answer before moving on."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from casebench.judge.config import JudgeConfig
from casebench.setup import screen
from casebench.setup.checks import Status, model_check
from casebench.setup.key_question import KeyFound, key_for, use
from casebench.setup.models import choose
from casebench.setup.picker import interactive, pick

AGAIN = [
    ("try again", "retry"),
    ("pick another model", "other"),
    ("keep it, and check later with casebench check", "keep"),
]


def plain(detail: str) -> str:
    """A provider's refusal, in the words a user acts on (decision 0043)."""
    lowered = detail.lower()
    if "401" in detail or "403" in detail or "unauthorized" in lowered:
        return "the provider refused the key"
    if "404" in detail or "not found" in lowered:
        return "the provider does not know this model"
    if "set " in lowered and " to call" in lowered:
        return "its key is not set"
    if "429" in detail:
        return "the provider is limiting requests; try again in a moment"
    return detail


def _key(block: dict[str, Any], root: Path, label: str) -> KeyFound | None:
    """The variable the provider reads, found in the shell or a .env file, and set for this run
    so the model can be asked now; a key chosen under another name renames the variable."""
    expected = (block.get("options") or {}).get("api_key_env")
    if not expected:
        return None
    found = key_for(expected, root, label)
    if found is None:
        screen.warn(f"no key for {expected}; set it before Casebench calls this model")
        return None
    if found.name != expected:
        block["options"]["api_key_env"] = found.name
    use(found)
    screen.ok(f"key {found.said(root)}")
    return found


def ask_model(
    role: str,
    catalog: Callable[[], dict[str, Any]],
    root: Path,
    provider: str | None = None,
    model: str | None = None,
    overrides: dict[str, Any] | None = None,
    live: bool = True,
) -> tuple[dict[str, Any], KeyFound | None, bool]:
    """Picked from the catalog, unless the flags named it; on a failed check, retry, another
    model or keep it, without starting over. Flags never loop: they are a script's answer.
    The last value says whether the model answered here."""
    scripted = provider is not None and model is not None
    while True:
        block, notes = choose(role, catalog(), provider, model, overrides or {})
        for note in notes:
            if not note.startswith("its key is read from"):
                screen.line(note)
        found = _key(block, root, role)
        if not live:
            return block, found, False
        with screen.working(f"Asking the {role} one question"):
            check = model_check(role, JudgeConfig.model_validate(block))
        if check.status is Status.PASSED:
            screen.ok(check.detail)
            return block, found, True
        if check.status is Status.UNREACHABLE:
            screen.warn(f"the {role} is not reachable from here; casebench check asks it there")
            return block, found, False
        reason = check.detail.split(": ", 1)[-1]
        screen.fail(f"the {role} did not answer: {plain(reason)}")
        if scripted or not interactive():
            return block, found, False
        choice = pick(f"The {role} did not answer. What now?", AGAIN)
        if choice == "keep":
            return block, found, False
        if choice == "other":
            provider = model = None
