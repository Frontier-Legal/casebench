---
title: Connect a Python agent
description: Run a Python function as the target, in worker processes, with an adapter that loads the agent's settings and every model and search call recorded where it goes.
sidebar:
  order: 1
---

Use a Python target when your agent is a function you can import. Casebench calls it once per case, the way your own code would, with no API in front of it.

## Point Casebench at the function

```yaml title="casebench.yaml"
target:
  type: python
  entry: .casebench/target.py:answer   # a file and a function
  max_concurrency: 4                   # cases at once; default 1
```

`entry` takes three forms:

- `path/to/file.py:function`
- `path/to/file.py`, which calls `answer`
- `package.module:function`

A relative path is read from the folder that holds `casebench.yaml`.

To try a function without editing the config, name it on the command line. It replaces the config's target for that run, and its path is read from the current folder:

```sh
casebench run --suite suites/employment --python agent.py
casebench run --suite suites/employment --python agent.py:respond
```

## Load the agent's settings in an adapter

Most agents load their settings before they can answer: a settings class that reads `.env` files, `load_dotenv`, a start script that exports variables. Casebench does not do that for your agent. It reads only the keys its own config names, and it keeps them out of child processes, as [Keep keys out of the config](/developers/guides/setup/keys/) explains. An agent function called bare usually fails on its first model call:

```text frame="terminal"
target   failed: AgentError: TypeError: "Could not resolve authentication method. Expected one of api_key, auth_token, or credentials to be set. Or for one of the `X-Api-Key` or `Authorization` headers to be explicitly omitted"
```

So write a short adapter at `.casebench/target.py`. It does what production does before it answers, then calls the function production calls:

```python title=".casebench/target.py"
from pathlib import Path

from dotenv import load_dotenv

# The same settings production loads, the same way.
load_dotenv(Path(__file__).parent.parent / ".env")

from legal_agent.chat import answer_question  # noqa: E402


def answer(question: str, facts: str | None = None) -> str:
    return answer_question(question, context=facts)
```

- Define `answer` with `def` in the adapter itself. `casebench check` reads the file without running it and fails with `defines no 'answer'` when the name only arrives by `import`.
- Leave the agent's base URLs and keys as its settings set them. Casebench records each call where it goes and changes nowhere it goes.
- The adapter sits under `.casebench/`, never in a folder named `casebench/` at the project's root, which would hide the `casebench` package.

To keep runs and caches out of git and the adapter in it, add `.casebench/.gitignore`:

```text title=".casebench/.gitignore"
*
!.gitignore
!target.py
!casebench.schema.json
```

[Set up with a coding agent](/developers/guides/setup/coding-agent/) has your coding agent write this adapter from the project's own start-up code, and change nothing else.

## How imports resolve

Each worker puts the folder that holds `casebench.yaml` on `sys.path` before it imports the entry, so the adapter imports the project's packages as code at the project's root does, whichever folder you run Casebench from. A file entry also puts its own folder first, so its neighbouring modules import too. A module entry adds the current folder.

## What the function receives

Each case's inputs arrive as keyword arguments, by name: `question`, and depending on the task `facts`, `document` or `instruction`. A function without `**kwargs` receives only the inputs it names, so an existing function usually fits as it is.

```python
def answer(question: str) -> str: ...  # the question only
def answer(question: str, facts: str = "") -> str: ...  # also the facts, when a case has them
async def answer(**inputs) -> dict: ...  # every input
```

Plain functions, async functions, generators and async generators all work. A generator's chunks are joined into one answer. A plain function runs in a thread.

## What it can return

| Return | Casebench does |
| --- | --- |
| `str` | Keeps the text. The judge lists its citations when it grades. |
| `dict` with `answer`, and optionally `citations` and `documents` | Keeps the text, and stores the citations and document ids with the result. |

Casebench shows returned `citations` and `documents` in `target check` and keeps them in `results.jsonl`. The ranked metrics of a research suite, `authority_recall` and `authority_ndcg`, read the returned citations in their order. Citation checks still list the citations from the answer's text, and the [authority funnel](/developers/concepts/authority-funnel/) reads the ids of recorded steps, not returned `documents`.

## Run Casebench in the agent's environment

The workers start with the Python that runs Casebench, so the agent's packages must be importable there. Run Casebench inside the project's environment without adding it to the project's dependencies.

In a uv project:

```sh
uv run --with casebench casebench check
```

In a project that uses pip, install it into the project's virtual environment:

```sh
pip install casebench
```

`casebench guide` prints the exact install spec of the copy you run.

## How the workers behave

- With `max_concurrency: N`, Casebench starts N workers. Each imports your module once and answers one case at a time.
- Each worker sends every call the agent makes through httpx2, httpx or requests to the recording proxy, under the worker's own path. The proxy forwards it to the host the agent's code chose and records it against that worker's case. See [Record model calls](/developers/guides/capture/model-calls/).
- Calls on other HTTP clients, such as aiohttp or gRPC, still go where the agent sends them, but they are not recorded and the [perimeter](/developers/guides/setup/network/) does not see them.
- Your agent's own `print` output goes to standard error, so it never mixes with the answer.
- A worker that crashes fails its case with the exit code and is replaced. The run goes on.
- Every result is stored before the next case starts. Stop a run, run it again with the same `--run-id`, and it resumes after the last stored result.

## Check it

```sh
casebench target check
```

It sends "Hi. How are you?" and shows the parsed answer, the citations and the steps it recorded:

```text frame="terminal"
answer     I'm well, thank you.
citations  none
documents  none
steps      1 captured
  llm claude-sonnet-4-5
took       26 ms
```

Pass `--question` to ask something else. `casebench check` sends the same greeting as one of its parts:

```text frame="terminal"
target   passed: answered "I'm well, thank you.", 1 call recorded (1 llm)
```

If it says Casebench refused a call to a host, the agent calls a host `casebench.yaml` does not name. Add it under `network: allow:`, as [Allow the hosts your agent calls](/developers/guides/setup/network/) explains.

## Related

- [Record model calls](/developers/guides/capture/model-calls/): the follow path, and what each parser reads.
- [Record retrieval steps](/developers/guides/capture/retrieval-steps/): searches of the corpus and of Qdrant, and in-process functions such as a rerank.
- The [configuration reference](/developers/reference/configuration/) lists every target key.
