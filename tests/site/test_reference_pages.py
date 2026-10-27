"""The site's generated reference pages match the code they describe."""

import importlib.util
import re
from pathlib import Path

import yaml
from starlette.routing import Route

from casebench.capture.proxy.forward import make_app
from casebench.capture.recorder import Recorder
from tests.repository.files import ROOT

SITE = ROOT / "site"


def _script(name: str):
    spec = importlib.util.spec_from_file_location(name, SITE / "scripts" / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_command_line_reference_shows_every_current_option():
    script = _script("cli_reference")
    page: Path = script.PAGE
    assert page.read_text(encoding="utf-8") == script.render(), (
        "the CLI reference is out of date: run `uv run python site/scripts/cli_reference.py`"
    )


def test_the_capture_server_reference_lists_the_routes_the_server_serves():
    spec = yaml.safe_load((SITE / "openapi" / "capture-server.yaml").read_text(encoding="utf-8"))
    app = make_app([], Recorder(), lambda route, url: None)
    served = {
        re.sub(r"\{(\w+):path\}", r"{\1}", route.path): set(route.methods or ())
        for route in app.routes
        if isinstance(route, Route)
    }

    documented = {
        path: {method.upper() for method in item if method != "parameters"}
        for path, item in spec["paths"].items()
    }
    assert documented.keys() == served.keys()
    for path, methods in documented.items():
        assert methods <= served[path], f"{path} documents {methods - served[path]}"
