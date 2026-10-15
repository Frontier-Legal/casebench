"""Measure the legal accuracy of an AI system against court decisions and lawyers' references."""

from importlib.metadata import version
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from casebench.sdk import arun, instrument, run

__version__ = version("casebench")
__all__ = ["__version__", "arun", "instrument", "run"]


def __getattr__(name: str) -> Any:
    """`instrument`, `run` and `arun`, imported when first used, so `import casebench` stays
    light (decision 0062)."""
    if name in ("instrument", "run", "arun"):
        from casebench import sdk

        return getattr(sdk, name)
    raise AttributeError(f"module 'casebench' has no attribute {name!r}")
