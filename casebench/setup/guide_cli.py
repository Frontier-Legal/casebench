"""`casebench guide`: the setup steps a coding agent follows, for the installed version."""

import json
from importlib import metadata, resources

import click

PACKAGE = "casebench"


def install_spec() -> str:
    """What this copy of Casebench was installed from, as a requirement another environment can
    install: a release by version, a git checkout pinned to its commit, or a local folder.
    Read from the install record (PEP 610 `direct_url.json`)."""
    found = metadata.distribution(PACKAGE)
    recorded = found.read_text("direct_url.json")
    if not recorded:
        return f"{PACKAGE}=={found.version}"
    origin = json.loads(recorded)
    vcs = origin.get("vcs_info")
    if vcs:
        return f"{PACKAGE} @ {vcs['vcs']}+{origin['url']}@{vcs['commit_id']}"
    return f"{PACKAGE} @ {origin['url']}"


def guide_text() -> str:
    """The guide, with this version and the spec to install it filled in."""
    template = resources.files("casebench.setup").joinpath("guide.md").read_text("utf-8")
    version = metadata.version(PACKAGE)
    return template.replace("@VERSION@", version).replace("@SPEC@", install_spec())


@click.command(name="guide")
def guide_command() -> None:
    """Print the steps a coding agent follows to set Casebench up in a project, changing
    nothing but casebench.yaml and .casebench/ (decision 0044). Paste into the coding agent:
    "Set up Casebench for this project: run `casebench guide` and follow it"."""
    click.echo(guide_text())
