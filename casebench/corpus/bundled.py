"""The profiles bundled with Casebench: listed by name, checked offline, and found by id or file."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from casebench.corpus.from_profile import ProfileProblem, load_profile
from casebench.corpus.mapping import every, record_fields
from casebench.corpus.profile import Profile
from casebench.corpus.record import REQUIRED_FIELDS

PROFILES = Path(__file__).parent / "profiles"
SAMPLES = "samples"


@dataclass(frozen=True)
class Bundled:
    """One bundled profile: its id is its file name without `.yaml`."""

    id: str
    path: Path
    profile: Profile

    @property
    def key_found(self) -> bool:
        return bool(self.profile.key_env and os.environ.get(self.profile.key_env))


def bundled(root: Path | None = None) -> list[Bundled]:
    """Every bundled profile, ordered by name and nothing else (decision 0033)."""
    folder = root or PROFILES
    found = [Bundled(p.stem, p, load_profile(p)[0]) for p in sorted(folder.glob("*.yaml"))]
    return sorted(found, key=lambda item: (item.profile.name.casefold(), item.id))


def resolve(given: str, root: Path | None = None) -> tuple[Path, str]:
    """A profile file, or a bundled profile's id, with what casebench.yaml records for it:
    the file's name, or the bundled id."""
    if Path(given).is_file():
        return Path(given), Path(given).name
    for item in bundled(root):
        if item.id == given:
            return item.path, item.id
    ids = ", ".join(item.id for item in bundled(root)) or "none"
    raise ProfileProblem(f"{given} is not a profile file or a bundled profile (bundled: {ids})")


def _sample(item: Bundled, name: str) -> Any:
    path = item.path.parent / SAMPLES / item.id / f"{name}.json"
    if not path.is_file():
        raise ProfileProblem(f"{item.id} has no recorded {name}: add {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def offline_problems(item: Bundled) -> list[str]:
    """What keeps a bundled profile out: its recorded search must yield an id, and its
    recorded fetch must give every required field through the profile's paths. Runs with
    no network and no key, so review needs neither."""
    try:
        search, document = _sample(item, "search"), _sample(item, "fetch")
    except ProfileProblem as error:
        return [str(error)]
    options = item.profile.options
    problems = []
    if not item.profile.maintainer:
        problems.append(f"{item.id}: a bundled profile names its maintainer")
    if not every(options.get("search_ids", "$"), search):
        problems.append(f"{item.id}: the recorded search gives no id through search_ids")
    mapped = record_fields(document, options.get("fields", {}))
    missing = [name for name in REQUIRED_FIELDS if mapped.get(name) in (None, "")]
    if missing:
        problems.append(f"{item.id}: the recorded fetch gives no {', '.join(missing)}")
    return problems
