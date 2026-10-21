"""The public model catalog, fetched once per workbench and shared by every page that reads it.

A setup page asks for it as it opens, so it is in hand when a model is picked; it is fetched
only for an engineer setting up, never when the workbench starts (decisions 0032, 0065).
"""

import threading
from typing import Any

from casebench.setup import catalog as model_catalog


class CatalogCache:
    def __init__(self) -> None:
        self._held: dict[str, Any] | None = None
        self._lock = threading.Lock()

    def get(self) -> dict[str, Any]:
        """The catalog, fetched now unless it is held; a second caller waits for the first."""
        with self._lock:
            if self._held is None:
                self._held = model_catalog.load()
            return self._held

    def warm(self) -> None:
        """Fetch it in the background; a failure is left for the next `get` to report."""
        if self._held is not None:
            return

        def fetch() -> None:
            try:
                self.get()
            except Exception:
                return

        threading.Thread(target=fetch, daemon=True).start()
