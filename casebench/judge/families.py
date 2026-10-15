"""Whether a judge shares a model family with the agent it grades (decisions 0029 and 0047)."""

from pydantic import Field

from casebench.core.model import Record

UNLISTED = (
    "the agent's models are not listed under `agent_models:` in casebench.yaml, so whether a "
    "judge shares their family was not checked"
)


class AgentModel(Record):
    """A model the agent calls, with its family as the model catalog gives it."""

    model: str
    family: str = Field(description="The model catalog's family, such as claude or qwen.")


def family_warnings(
    judges: list[tuple[str, str]], agent: list[AgentModel], called: set[str]
) -> list[str]:
    """`judges` are each judge's name and family; `called` the models the agent called during
    the run. Families are compared as the catalog gives them, never read from a name."""
    if not judges:
        return []
    if not agent:
        return [UNLISTED]
    warnings = []
    for name, family in judges:
        same = sorted(model.model for model in agent if model.family == family)
        if same:
            warnings.append(
                f"the judge {name} is of the {family} family, as the agent's {', '.join(same)}; "
                "a model grading its own family's answers favours them (decision 0029). "
                "Pick a judge from another family."
            )
    unlisted = sorted(called - {model.model for model in agent})
    if unlisted:
        warnings.append(
            f"the agent called {', '.join(unlisted)}, which `agent_models:` does not list, so "
            "the family check did not cover them"
        )
    return warnings
