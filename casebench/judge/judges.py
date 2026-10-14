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
