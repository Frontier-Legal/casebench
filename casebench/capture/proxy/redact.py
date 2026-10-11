"""Keep secrets out of recorded URLs."""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SECRET_WORDS = ("key", "token", "secret", "signature", "password")
REDACTED = "REDACTED"


def redact_url(url: str) -> str:
    """Replace the value of any query parameter whose name names a secret."""
    parts = urlsplit(url)
    if not parts.query:
        return url
    query = [
        (name, REDACTED if any(word in name.lower() for word in SECRET_WORDS) else value)
        for name, value in parse_qsl(parts.query, keep_blank_values=True)
    ]
    return urlunsplit(parts._replace(query=urlencode(query)))
