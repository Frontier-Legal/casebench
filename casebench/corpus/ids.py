"""Qualified document ids, `<corpus name>:<id>`, so two providers' ids never collide (0036)."""

NAME = r"^[a-z0-9]+(-[a-z0-9]+)*$"
SEPARATOR = ":"


class UnqualifiedId(ValueError):
    """An id with no corpus name, or one naming a corpus the setup does not have."""


def qualify(corpus: str, document_id: str) -> str:
    return f"{corpus}{SEPARATOR}{document_id}"


def split(qualified: str) -> tuple[str, str]:
    """The corpus name and the id as its provider gives it: everything after the first
    separator, so a provider's own id may contain one."""
    corpus, separator, document_id = qualified.partition(SEPARATOR)
    if not separator or not corpus or not document_id:
        raise UnqualifiedId(f"{qualified!r} names no corpus; ids look like <corpus>:<id>")
    return corpus, document_id
