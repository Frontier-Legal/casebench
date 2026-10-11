"""Mark which known document ids a model call's request carries (decision 0031)."""

import json
import re
from typing import Any


def ids_in(request_body: Any, known: set[str]) -> list[str]:
    """Ids found as whole words, so id 12 is not found inside 2012 or tr-12."""
    if request_body is None or not known:
        return []
    text = (
        request_body
        if isinstance(request_body, str)
        else json.dumps(request_body, ensure_ascii=False)
    )
    return sorted(i for i in known if re.search(rf"(?<![\w-]){re.escape(i)}(?![\w-])", text))
