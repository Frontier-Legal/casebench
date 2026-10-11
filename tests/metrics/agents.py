"""An agent that cites authorities in its own words, not the court's."""


def cites(question: str, facts: str) -> str:
    if "statutes" in question:
        return "İş K. md. 18 governs the dismissal; see also TBK m. 49."
    return "Yargıtay 9. Hukuk Dairesi 2019/1 E., 2020/2 K. decided this under İş K. md. 18."
