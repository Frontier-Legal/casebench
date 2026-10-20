"""Build the judges a config names, refusing a second judge from the first one's model family."""

from casebench.judge.client import Judge
from casebench.judge.config import JudgeConfig
from casebench.judge.memo import Memo


class SameFamily(ValueError):
    """Two judges of one family share its blind spots, so their agreement proves little."""


def judges_for(configs: list[JudgeConfig], memo: Memo | None = None) -> list[Judge]:
    """Decision 0035: a second judge must come from another model family than the first."""
    judges = [Judge(config, memo=memo) for config in configs]
    families = [judge.family for judge in judges]
    if len(set(families)) < len(families):
        raise SameFamily(
            f"both judges are of the {families[0]} family; pick a second judge from another "
            "model family, or keep one judge"
        )
    return judges


def _family(config: JudgeConfig) -> str | None:
    """The family its options name, else its provider's; None when the provider is not here."""
    named = config.options.get("family")
    if named:
        return str(named)
    try:
        return Judge(config).family
    except Exception:
        return None


def shared_family(configs: list[JudgeConfig]) -> str | None:
    """The family two judges share, read without calling either; None when they differ."""
    families = [_family(config) for config in configs]
    if len(families) == 2 and families[0] is not None and families[0] == families[1]:
        return families[0]
    return None
