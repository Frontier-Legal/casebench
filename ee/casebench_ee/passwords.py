# SPDX-License-Identifier: Elastic-2.0
"""The first admin's password: refused when weak or a known default, kept as a scrypt hash."""

import base64
import hashlib
import hmac
import secrets

MINIMUM = 12
# Words a default or a guess starts from; a password made mostly of one is refused.
DEFAULTS = (
    "admin",
    "administrator",
    "password",
    "passw0rd",
    "changeme",
    "change-me",
    "casebench",
    "letmein",
    "welcome",
    "default",
    "secret",
    "qwerty",
    "123456",
    "root",
    "test",
)
# scrypt's cost: 2^15 rounds, a block size of 8 and no parallelism, about 32 MB.
N, R, P = 2**15, 8, 1


class WeakPassword(ValueError):
    """Why a password is refused."""


def check(password: str, email: str) -> None:
    lowered = password.lower()
    if len(password) < MINIMUM:
        raise WeakPassword(f"use {MINIMUM} characters at least")
    if len(set(password)) < 4:
        raise WeakPassword("use more than three different characters")
    for word in DEFAULTS:
        if word in lowered and len(lowered.replace(word, "")) < MINIMUM // 2:
            raise WeakPassword(f"{word!r} is a default or a common password; choose another")
    local = email.split("@", 1)[0].lower()
    if len(local) >= 3 and local in lowered:
        raise WeakPassword("do not use your email's name in your password")


def _encode(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def hashed(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P, maxmem=64 * 2**20)
    return f"scrypt${N}${R}${P}${_encode(salt)}${_encode(digest)}"


def matches(password: str, stored: str | None) -> bool:
    if not stored or not stored.startswith("scrypt$"):
        return False
    _, n, r, p, salt, digest = stored.split("$")
    tried = hashlib.scrypt(
        password.encode(),
        salt=base64.b64decode(salt),
        n=int(n),
        r=int(r),
        p=int(p),
        maxmem=64 * 2**20,
    )
    return hmac.compare_digest(tried, base64.b64decode(digest))
