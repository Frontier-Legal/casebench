# SPDX-License-Identifier: Elastic-2.0
"""Each organisation's runs and suites in folders of its own, chosen per request (decision 0066).

The organisation a self-hosted server has keeps the folders the server was given; every other
one has `<organisations>/<id>/runs` and `<organisations>/<id>/suites`, which the first never reads.
"""

from pathlib import Path

from casebench.corpus.corpora import Corpora
from casebench.judge.families import AgentModel
from casebench.workbench.sources import Workspace
from casebench.workbench.tenancy import LOCAL, current

RUNS, SUITES = "runs", "suites"


class OrganisationWorkspace(Workspace):
    """A workspace whose folders are the request's organisation's."""

    def __init__(
        self,
        runs_dir: Path,
        suite_dirs: list[Path],
        organisations_dir: Path,
        corpora: Corpora | None = None,
        agent_models: list[AgentModel] | None = None,
    ) -> None:
        self.organisations_dir = organisations_dir
        super().__init__(runs_dir, suite_dirs, corpora, agent_models)

    def folder(self, organisation: str) -> Path:
        return self.organisations_dir / organisation

    @property  # type: ignore[override]
    def runs_dir(self) -> Path:
        organisation = current()
        return self._runs if organisation == LOCAL else self.folder(organisation) / RUNS

    @runs_dir.setter
    def runs_dir(self, value: Path) -> None:
        self._runs = value

    @property  # type: ignore[override]
    def suite_dirs(self) -> list[Path]:
        organisation = current()
        return self._suites if organisation == LOCAL else [self.folder(organisation) / SUITES]

    @suite_dirs.setter
    def suite_dirs(self, value: list[Path]) -> None:
        self._suites = value

    def _manifests(self) -> list[Path]:
        """The first organisation's suite folders may hold the others' folder; it never reads
        a suite from there."""
        others = self.organisations_dir.resolve()
        return [p for p in super()._manifests() if not p.resolve().is_relative_to(others)]

    def folders(self, organisation: str) -> list[Path]:
        """Everything the organisation keeps on disk, for erasing it."""
        if organisation == LOCAL:
            return [self._runs, *self._suites]
        return [self.folder(organisation)]
