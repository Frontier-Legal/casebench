"""`casebench proxy env`: the variables that point an already-running agent at the proxy."""

from pathlib import Path

import click

from casebench.capture.config import routes_for
from casebench.capture.proxy.routes import environment
from casebench.capture.session import TRACES_ENDPOINT, traces_endpoint
from casebench.config import DEFAULT_CONFIG, load_config


@click.group()
def proxy() -> None:
    """The recording proxy that captures model and backend calls."""


@proxy.command()
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=DEFAULT_CONFIG,
    show_default=True,
)
def env(config_path: Path) -> None:
    """Print the lines to set in the agent's environment."""
    config = load_config(config_path)
    if config.capture is None or config.capture.port == 0:
        raise click.ClickException(
            "set capture.port in the config so an agent that is already running can reach "
            "the proxy; when Casebench starts the agent it sets these itself"
        )
    for name, value in environment(routes_for(config.capture), config.capture.port).items():
        click.echo(f"{name}={value}")
    click.echo(f"{TRACES_ENDPOINT}={traces_endpoint(config.capture.port)}")
