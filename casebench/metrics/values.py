"""A field's value against the expected one, exactly or after normalising (decision 0049)."""

import string
import unicodedata
from typing import Any

EXPECTED = "expected"
EXACT, NORMALISED = "exact", "normalised"
# Punctuation dropped from a value's ends, with the typographic quotes a document often has.
ENDS = string.punctuation + "“”‘’«» "  # noqa: RUF001


def normalised(value: str) -> str:
    """NFC, case folded, whitespace collapsed and surrounding punctuation dropped."""
    text = " ".join(unicodedata.normalize("NFC", value).casefold().split())
    return text.strip(ENDS)


def matched(expected: str, given: Any) -> str | None:
    """How the given value matches, or None when it does not."""
    if given is None or isinstance(given, (dict, list)):
        return None
    text = str(given)
    if text == expected:
        return EXACT
    return NORMALISED if normalised(text) == normalised(expected) else None
