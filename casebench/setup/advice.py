"""Say what a newer Casebench can use that a setup lacks, and the command that fills it in."""

from casebench.config import CasebenchConfig
from casebench.setup.checks import models_of

DESCRIBED = ("http", "mcp")


def advice(config: CasebenchConfig) -> list[str]:
    """Never a failure: the setup works as it is, and does more with these (decision 0042)."""
    lines = []
    for name, corpus in config.corpora.items():
        if corpus.connector in DESCRIBED and not corpus.options.get("search_results"):
            lines.append(
                f"corpus {name}: its search results are not described, so the judge reads each "
                "candidate from the stored document; `casebench corpus add` suggests where its "
                "results keep their citation, type and passage (search_results, result_fields)"
            )
    for label, model in models_of(config):
        if model.price is None:
            lines.append(
                f"{label}: no price, so costs show as tokens; `casebench init` takes it from the "
                "model catalog"
            )
        if label.endswith("judge") and model.context_window is None:
            lines.append(
                f"{label}: no context window, so a matching call is never split to fit; "
                "`casebench init` takes it from the model catalog"
            )
    return lines
