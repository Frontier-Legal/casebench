"""Ask whether lawyers review on a team server, and name it in casebench.yaml (0064)."""

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import click

from casebench.setup.picker import interactive, pick, text
from casebench.setup.update import Addition

NOT_NOW, HAVE, SET_UP = "none", "have", "setup"
CHOICES = [
    ("Not now: lawyers review on this machine, with casebench ui", NOT_NOW),
    ("We have one: name its address", HAVE),
    ("Set one up: show what to run on the server lawyers reach", SET_UP),
]
QUESTION = "Will lawyers review on a team server?"
FLAG = "--team-server URL"


@dataclass(frozen=True)
class TeamServer:
    """The server's address when there is one, and whether to show how to set one up."""

    url: str | None = None
    set_up: bool = False


def address(given: str) -> str:
    """The server's address as `cloud: url:` keeps it: http or https, with a host."""
    url = given.strip().rstrip("/")
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise click.BadParameter(f"{given!r} is not a server's address, such as https://host")
    return url


def ask(given: str | None) -> TeamServer:
    """`--team-server URL` answers without asking. Without a terminal and without it, nothing
    is asked: lawyers review on this machine, and a server can be named later."""
    if given is not None:
        return TeamServer(url=address(given))
    if not interactive():
        return TeamServer()
    chosen = pick(QUESTION, CHOICES, NOT_NOW, flag=FLAG)
    if chosen == HAVE:
        return TeamServer(url=address(text("the team server's address", flag=FLAG)))
    return TeamServer(set_up=chosen == SET_UP)


def cloud_block(url: str) -> dict[str, Any]:
    """Only the address: the key is read from CASEBENCH_CLOUD_KEY, never written here."""
    return {"url": url}


def team_server_addition(data: dict[str, Any], url: str) -> list[Addition]:
    """For an existing casebench.yaml: the server, unless it already names this one. Its key
    variable stays as written."""
    written = data.get("cloud") or {}
    if written.get("url") == url:
        return []
    instead = f", instead of {written['url']}" if written.get("url") else ""

    def name(d: dict[str, Any]) -> None:
        d["cloud"] = {**(d.get("cloud") or {}), "url": url}

    return [Addition(f"team server {url}{instead}", name)]
