# SPDX-License-Identifier: Elastic-2.0
"""An invited lawyer signs in with an emailed link, or with Google or Microsoft, and lands in their
queue, with no IT ticket (decision 0058)."""

import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx2
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

from casebench_ee.access import COOKIE
from casebench_ee.mail import NoMail, Outbox
from casebench_ee.oidc import PERSONAL_ACCOUNTS, Provider
from team_tests.helpers import HOST, PUBLIC, browser, serve, signed_in

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
CLIENT = "casebench-client"


class Issuer:
    """A stand-in for Google or Microsoft: discovery, signing keys and a token endpoint that
    returns an identity with the claims it is given, for the nonce the app sent."""

    def __init__(self, issuer: str, claims: dict[str, Any]) -> None:
        self.issuer, self.claims, self.nonce = issuer, claims, ""

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        path = request.url.path
        if path.endswith("openid-configuration"):
            return httpx2.Response(
                200,
                json={
                    "issuer": self.issuer,
                    "authorization_endpoint": "https://issuer.test/authorize",
                    "token_endpoint": "https://issuer.test/token",
                    "jwks_uri": "https://issuer.test/keys",
                },
            )
        if path == "/keys":
            public = RSAAlgorithm.to_jwk(KEY.public_key(), as_dict=True)
            return httpx2.Response(200, json={"keys": [{**public, "kid": "k1", "alg": "RS256"}]})
        if path == "/token":
            now = int(time.time())
            claims = {
                "iss": self.issuer.replace("{tenantid}", self.claims.get("tid", "")),
                "aud": CLIENT,
                "iat": now,
                "exp": now + 300,
                "nonce": self.nonce,
                **self.claims,
            }
            token = jwt.encode(claims, KEY, algorithm="RS256", headers={"kid": "k1"})
            return httpx2.Response(200, json={"id_token": token})
        return httpx2.Response(404)


def provider(name: str, issuer: Issuer) -> Provider:
    http = httpx2.Client(transport=httpx2.MockTransport(issuer.handle))
    return Provider(
        name, CLIENT, "secret", "https://issuer.test/.well-known/openid-configuration", http
    )


def sign_in_with(app: TestClient, name: str, issuer: Issuer) -> httpx2.Response:
    """Starts the sign-in, lets the provider answer for the nonce sent, and comes back."""
    started = app.get(f"/auth/{name}/start", follow_redirects=False)
    query = parse_qs(urlsplit(started.headers["location"]).query)
    issuer.nonce = query["nonce"][0]
    return app.get(
        f"/auth/{name}/callback",
        params={"code": "the-code", "state": query["state"][0]},
        follow_redirects=False,
    )


def test_login_without_it(database: str, tmp_path: Path):
    outbox = Outbox()
    google = Issuer(
        "https://accounts.google.com", {"email": "deniz@firm.example", "email_verified": True}
    )
    microsoft = Issuer(
        "https://login.microsoftonline.com/{tenantid}/v2.0",
        {"email": "emre@firm.example", "tid": "0000-work-tenant"},
    )
    server = serve(
        database,
        tmp_path,
        outbox,
        providers={
            "google": provider("google", google),
            "microsoft": provider("microsoft", microsoft),
        },
    )
    admin = signed_in(server, "selin@firm.example", "Selin Kaya", "admin")

    invited = admin.post(
        "/api/team/users",
        json={"email": "ayse@firm.example", "name": "Ayşe Yılmaz", "role": "reviewer"},
    )
    [(to, subject, text)] = outbox.sent
    link = re.search(r"http\S+", text)
    assert link is not None
    lawyer = browser(server)
    opened = lawyer.get(link.group(0).removeprefix(PUBLIC), follow_redirects=False)
    me = lawyer.get("/api/me").json()
    queue = lawyer.get("/api/queue")
    reused = browser(server).get(link.group(0).removeprefix(PUBLIC), follow_redirects=False)

    assert invited.status_code == 200, invited.text
    assert invited.json()["emailed"] is True and invited.json()["link"] is None
    assert to == "ayse@firm.example" and subject == "Sign in to Casebench"
    assert "Selin Kaya invited you" in text and "within 15 minutes" in text
    assert opened.status_code == 303 and opened.headers["location"] == "/"
    assert COOKIE in opened.cookies
    assert (me["name"], me["role"]) == ("Ayşe Yılmaz", "reviewer")
    assert queue.status_code == 200 and queue.json()["items"]
    assert reused.headers["location"] == "/?signin=expired"

    # Google vouches for a verified email of someone invited.
    admin.post(
        "/api/team/users", json={"email": "deniz@firm.example", "name": "Deniz", "role": "editor"}
    )
    by_google = browser(server)
    back = sign_in_with(by_google, "google", google)
    assert back.headers["location"] == "/", back.headers["location"]
    assert by_google.get("/api/me").json()["role"] == "editor"

    # Microsoft does not vouch for a work account's email unless its domain is verified.
    admin.post(
        "/api/team/users", json={"email": "emre@firm.example", "name": "Emre", "role": "engineer"}
    )
    refused = sign_in_with(browser(server), "microsoft", microsoft)
    assert refused.headers["location"].startswith("/?signin=refused")
    microsoft.claims = {"email": "emre@firm.example", "tid": "0000-work-tenant", "xms_edov": True}
    by_work = browser(server)
    assert sign_in_with(by_work, "microsoft", microsoft).headers["location"] == "/"
    assert by_work.get("/api/me").json()["role"] == "engineer"
    microsoft.claims = {"email": "emre@firm.example", "tid": PERSONAL_ACCOUNTS}
    assert sign_in_with(browser(server), "microsoft", microsoft).headers["location"] == "/"

    # No one signs up uninvited.
    google.claims = {"email": "stranger@else.example", "email_verified": True}
    stranger = sign_in_with(browser(server), "google", google)
    assert "not+in+this+team" in stranger.headers["location"]


def test_without_smtp_the_admin_passes_the_link_on(database: str, tmp_path: Path):

    server = serve(database, tmp_path, NoMail())
    admin = signed_in(server, "selin@firm.example", "Selin", "admin")

    invited = admin.post(
        "/api/team/users", json={"email": "a@firm.example", "name": "A", "role": "viewer"}
    ).json()

    assert invited["emailed"] is False
    assert invited["link"].startswith(f"{PUBLIC}/auth/link?token=")
    assert browser(server).get("/api/team/status").json()["mail"] is False
    assert HOST in invited["link"]
