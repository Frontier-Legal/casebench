"""Agents for the workbench's tests: one names the ruling, one answers with citations."""

SPOT_ANSWER = (
    "The dismissal is invalid: see Yargıtay 9. HD, E. 2023/1234 K. 2024/567 and Yargıtay 22. HD,"
    " E. 2022/77 K. 2023/90. Notice may be waived orally (Yargıtay 3. HD, E. 2021/999 K. 2022/1)."
)


def upheld(question: str, facts: str = "") -> str:
    return "The court upheld the decision."


def assistant(question: str) -> str:
    """The team's assistant, asked a question from the workbench."""
    return SPOT_ANSWER
