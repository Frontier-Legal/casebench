# SPDX-License-Identifier: Elastic-2.0
"""Sign-in with Google or Microsoft: an OpenID Connect code flow with PKCE, for invited emails.

A provider's word on an email counts only where the provider verifies it (decision 0058).
"""

import base64
import hashlib
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

import httpx2
import jwt

from casebench_ee.models import Handshake

GOOGLE = "https://accounts.google.com/.well-known/openid-configuration"
MICROSOFT = "https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration"
# Personal Microsoft accounts sign in through this tenant, whose emails Microsoft verifies.
PERSONAL_ACCOUNTS = "9188040d-6c67-4c5b-b112-36a304b66dad"
TITLES = {"google": "Google", "microsoft": "Microsoft"}


class SignInRefused(ValueError):
    """Why a provider's answer does not sign anyone in."""


def challenge(verifier: str) -> str:
    """PKCE's S256 challenge for a verifier."""
    hashed = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(hashed).rstrip(b"=").decode()


@dataclass
class Provider:
    name: str
    client_id: str
    client_secret: str = field(repr=False)
    discovery: str
    http: httpx2.Client = field(default_factory=lambda: httpx2.Client(timeout=10), repr=False)
    _metadata: dict[str, Any] | None = field(default=None, repr=False)

    @property
    def title(self) -> str:
        return TITLES.get(self.name, self.name)

    def metadata(self) -> dict[str, Any]:
        if self._metadata is None:
            response = self.http.get(self.discovery)
            response.raise_for_status()
            self._metadata = dict(response.json())
        return self._metadata

    def authorize(self, handshake: Handshake, redirect: str) -> str:
        query = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect,
            "scope": "openid email profile",
            "state": handshake.state,
            "nonce": handshake.nonce,
            "code_challenge": challenge(handshake.verifier),
            "code_challenge_method": "S256",
            "prompt": "select_account",
        }
        return f"{self.metadata()['authorization_endpoint']}?{urlencode(query)}"

    def email(self, code: str, handshake: Handshake, redirect: str) -> str:
        """The verified email the provider signs for, lower-cased."""
        meta = self.metadata()
        response = self.http.post(
            meta["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code_verifier": handshake.verifier,
            },
        )
        if response.status_code != 200:
            raise SignInRefused(f"{self.title} did not accept the sign-in")
        token = response.json().get("id_token")
        if not token:
            raise SignInRefused(f"{self.title} returned no identity")
        claims = self._verified(token)
        if claims.get("nonce") != handshake.nonce:
            raise SignInRefused("the sign-in does not match the one started here")
        return self._email(claims)

    def _verified(self, token: str) -> dict[str, Any]:
        meta = self.metadata()
        keys = self.http.get(meta["jwks_uri"]).json()
        kid = jwt.get_unverified_header(token).get("kid")
        found = next((k for k in keys.get("keys", []) if k.get("kid") == kid), None)
        if found is None:
            raise SignInRefused(f"{self.title}'s identity is signed with a key it does not list")
        try:
            claims = jwt.decode(
                token,
                jwt.PyJWK(found).key,
                algorithms=["RS256"],
                audience=self.client_id,
                options={"require": ["exp", "iat", "iss", "aud"], "verify_iss": False},
            )
        except jwt.PyJWTError as failure:
            raise SignInRefused(f"{self.title}'s identity did not verify: {failure}") from None
        issuer = str(meta["issuer"]).replace("{tenantid}", str(claims.get("tid", "")))
        accepted = {issuer, issuer.removeprefix("https://")}
        if claims["iss"] not in accepted:
            raise SignInRefused(f"{self.title}'s identity names another issuer")
        return claims

    def _email(self, claims: dict[str, Any]) -> str:
        email = str(claims.get("email") or "").strip().lower()
        if self.name == "microsoft":
            vouched = claims.get("tid") == PERSONAL_ACCOUNTS or claims.get("xms_edov") is True
            if not email or not vouched:
                raise SignInRefused(
                    "Microsoft does not vouch for this account's email; sign in with the link "
                    "sent to it instead"
                )
            return email
        if not email or claims.get("email_verified") is not True:
            raise SignInRefused(f"{self.title} has not verified this account's email")
        return email
