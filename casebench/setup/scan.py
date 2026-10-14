"""Read a project's Python code, offline, for its model clients, model names and entry points."""

import ast
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from casebench.core.case import INPUTS
from casebench.plugins import registry
from casebench.plugins.kinds import kind_named

# HTTP clients a backend such as a search API is called through (decision 0040).
BACKENDS = ("httpx.Client", "httpx.AsyncClient")
# Folders that hold no code of the project's own.
SKIPPED = {"node_modules", "__pycache__", "site-packages"}
ENVIRON_GETTERS = ("os.environ.get", "os.getenv")


def is_test(relative: Path) -> bool:
    """A file pytest collects as tests, by its documented default patterns (`test_*.py`,
    `*_test.py`) and `conftest.py`: not the agent, and not the models it uses (0043)."""
    name = relative.name
    return name.startswith("test_") or name.endswith("_test.py") or name == "conftest.py"


def callable_by_casebench(function: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Whether a Python target can call it with a case's inputs (`INPUTS`), as the target
    calls every entry point: it takes the question, by name or through `**kwargs`, and every
    parameter it requires is one Casebench gives (decision 0043)."""
    arguments = function.args
    if arguments.posonlyargs or arguments.vararg:
        return False
    named = [*arguments.args, *arguments.kwonlyargs]
    defaults = len(arguments.defaults)
    required = [a.arg for a in arguments.args[: len(arguments.args) - defaults]]
    required += [
        a.arg for a, d in zip(arguments.kwonlyargs, arguments.kw_defaults, strict=True) if d is None
    ]
    takes_question = arguments.kwarg is not None or any(a.arg == INPUTS[0] for a in named)
    return takes_question and all(name in INPUTS for name in required)


@dataclass(frozen=True)
class Source:
    """Where a value comes from: a literal in the code, or a variable it is read from by name,
    with the literal default the code gives. A variable's value is never read."""

    literal: str | None = None
    env: str | None = None


@dataclass(frozen=True)
class Client:
    """One client the code builds: `parser` reads its calls, or None for a backend."""

    kind: str
    parser: str | None
    path: str
    line: int
    base_url: Source | None = None
    api_key: Source | None = None

    @property
    def where(self) -> str:
        return f"{self.path}:{self.line}"


@dataclass(frozen=True)
class ModelName:
    name: str
    path: str
    line: int


@dataclass
class Scan:
    files: int = 0
    clients: list[Client] = field(default_factory=list)
    models: list[ModelName] = field(default_factory=list)
    entries: list[str] = field(default_factory=list)

    def said(self) -> str:
        return (
            f"read {self.files} Python files as text: names and literals only, no variable's "
            "value, and nothing was sent"
        )


def python_files(root: Path) -> list[Path]:
    """The project's own files: what git tracks or would track, else every file outside
    virtual environments and hidden folders."""
    try:
        listed = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", "*.py"],
            cwd=root,
            capture_output=True,
            check=True,
        )
        listed_paths = [Path(name) for name in listed.stdout.decode().split("\0") if name]
        return sorted(root / path for path in listed_paths if not is_test(path))
    except (OSError, subprocess.CalledProcessError):
        pass
    found = []
    for path in sorted(root.rglob("*.py")):
        folders = path.relative_to(root).parts[:-1]
        if any(part.startswith(".") or part in SKIPPED for part in folders):
            continue
        if any(
            (root.joinpath(*folders[: n + 1]) / "pyvenv.cfg").is_file() for n in range(len(folders))
        ):
            continue
        if not is_test(path.relative_to(root)):
            found.append(path)
    return found


def client_kinds() -> dict[str, str | None]:
    """Each client class a capture parser reads, with that parser; backends with none."""
    kinds: dict[str, str | None] = dict.fromkeys(BACKENDS)
    parser_kind = kind_named("parser")
    for item in registry.available(parser_kind):
        for name in getattr(registry.load(parser_kind, item.name, item.source), "clients", []):
            kinds[name] = item.name
    return kinds


class _Module:
    """One file's imports, module-level string constants, client calls and functions."""

    def __init__(self, tree: ast.Module) -> None:
        self.imports: dict[str, str] = {}
        self.constants: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.imports[alias.asname or alias.name.split(".")[0]] = (
                        alias.name if alias.asname else alias.name.split(".")[0]
                    )
            elif isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    self.imports[alias.asname or alias.name] = f"{node.module}.{alias.name}"
        for node in tree.body:
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)
            ):
                self.constants[node.targets[0].id] = node.value.value

    def dotted(self, node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return self.imports.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            head = self.dotted(node.value)
            return f"{head}.{node.attr}" if head else None
        return None

    def literal(self, node: ast.expr | None) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name):
            return self.constants.get(node.id)
        return None

    def source(self, node: ast.expr) -> Source | None:
        """A literal, or `os.environ.get("X", default)`, `os.getenv("X", default)` or
        `os.environ["X"]`: the variable's name, never its value."""
        if (found := self.literal(node)) is not None:
            return Source(literal=found)
        if isinstance(node, ast.Call) and self.dotted(node.func) in ENVIRON_GETTERS and node.args:
            name = self.literal(node.args[0])
            default = self.literal(node.args[1]) if len(node.args) > 1 else None
            return Source(literal=default, env=name) if name else None
        if isinstance(node, ast.Subscript) and self.dotted(node.value) == "os.environ":
            name = self.literal(node.slice)
            return Source(env=name) if name else None
        return None


def _keyword(call: ast.Call, name: str) -> ast.expr | None:
    return next((k.value for k in call.keywords if k.arg == name), None)


def _calls(node: ast.AST) -> Iterator[ast.Call]:
    yield from (n for n in ast.walk(node) if isinstance(n, ast.Call))


def scan(root: Path) -> Scan:
    """No module is imported or run, and no variable is looked up (decision 0040)."""
    kinds = client_kinds()
    found = Scan()
    reaches: dict[str, bool] = {}
    callees: dict[str, set[str]] = {}
    defined: dict[str, tuple[str, int]] = {}
    fits: dict[str, bool] = {}
    for path in python_files(root):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        found.files += 1
        relative = path.relative_to(root).as_posix()
        module = _Module(tree)
        for call in _calls(tree):
            kind = module.dotted(call.func)
            base, key = _keyword(call, "base_url"), _keyword(call, "api_key")
            # A backend client with no base URL says nothing a route could use (decision 0043).
            if kind in kinds and (kinds[kind] is not None or base is not None):
                found.clients.append(
                    Client(
                        kind=kind,
                        parser=kinds[kind],
                        path=relative,
                        line=call.lineno,
                        base_url=module.source(base) if base is not None else None,
                        api_key=module.source(key) if key is not None else None,
                    )
                )
            model = module.literal(_keyword(call, "model"))
            if model:
                found.models.append(ModelName(model, relative, call.lineno))
        for node in tree.body:
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            calls = list(_calls(node))
            qualified = f"{relative}:{node.name}"
            defined[qualified] = (relative, node.lineno)
            fits[qualified] = callable_by_casebench(node)
            callees[qualified] = {name for c in calls if (name := _callee(c.func)) is not None}
            reaches[qualified] = any(
                _keyword(c, "model") is not None or module.dotted(c.func) in kinds for c in calls
            )
    found.entries = _entries(reaches, callees, defined, fits)
    return found


def _callee(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _entries(
    reaches: dict[str, bool],
    callees: dict[str, set[str]],
    defined: dict[str, tuple[str, int]],
    fits: dict[str, bool],
) -> list[str]:
    """Public functions a Python target can call with a case's inputs and that reach a model
    call through the project's own functions, in the order of the files (decision 0043). Each
    is `path.py:function`; a call by name may reach any of the project's functions of that name,
    as no import is followed."""
    named: dict[str, set[str]] = {}
    for qualified in defined:
        named.setdefault(qualified.rsplit(":", 1)[1], set()).add(qualified)
    changed = True
    while changed:
        changed = False
        for qualified, called in callees.items():
            if reaches[qualified]:
                continue
            others = {other for name in called for other in named.get(name, ())} - {qualified}
            if any(reaches[other] for other in others):
                reaches[qualified] = changed = True
    found = [
        qualified
        for qualified, yes in reaches.items()
        if yes and fits[qualified] and not qualified.rsplit(":", 1)[1].startswith("_")
    ]
    found.sort(key=lambda qualified: defined[qualified])
    return found
