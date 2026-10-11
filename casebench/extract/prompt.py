"""What each extraction model is asked about one decision (decision 0027)."""

OUTCOMES = (
    "upheld",
    "reversed",
    "partly_reversed",
    "remanded",
    "granted",
    "rejected",
    "partly_granted",
    "dismissed",
)

EXTRACT = f"""You read one court decision, in any language and from any country, and return \
what it decided, as JSON only:
{{"outcome": {{"label": one of {list(OUTCOMES)}, "quote": "the sentence that states the \
ruling, copied exactly"}},
"statutes": [{{"citation": "the statute or article as the decision writes it", "quote": "the \
sentence that applies it, copied exactly"}}],
"precedents": [{{"citation": "the earlier decision as the decision writes it", "quote": "the \
sentence that relies on it, copied exactly"}}],
"facts": "the dispute as a lawyer would put it to a colleague: the parties' positions and the \
facts, in the decision's language, without the ruling or anything that reveals it"}}
Copy every quote character for character from the decision; a quote that is not in the text is \
discarded. List only statutes and decisions the court applied or relied on, not ones a party \
cited and the court rejected. Use [] when there are none."""


def decision_prompt(text: str) -> str:
    return f"Decision:\n{text}"
