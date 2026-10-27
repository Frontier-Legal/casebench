---
title: Install Casebench
description: Run Casebench with uvx, add it to your agent's project, or install the team server. Python 3.11 or later.
kind: how-to
sidebar:
  label: Install
  order: 1
---

Casebench is a Python package on PyPI, `casebench`, with a command-line tool and a web app, the workbench. It needs Python 3.11 or later and runs on Linux, macOS and Windows. Your agent can be in any language.

While the version is 0.x, a minor release may change the command line, the file formats or the Python interface. The [changelog](/changelog/) names every break.

## Try it without installing

```sh
uvx casebench demo
```

[uv](https://docs.astral.sh/uv/) downloads Casebench into a cache, runs a small bundled suite with no key and no model calls, and opens the workbench on its results. See [Try the demo](/developers/tutorials/demo/).

## Choose how to run it on your agent

Where Casebench runs depends on how it reaches your agent.

| Your agent is | Run Casebench | Why |
| --- | --- | --- |
| A Python function (`target: python`) | With the project's own dependencies: `uv run --with casebench casebench ...` in a uv project, or `pip install casebench` into the project's virtual environment | Casebench imports and calls the function in worker processes, so the agent's packages must be importable there |
| An HTTP service or a command | As a standalone tool: `uvx casebench ...` or `uv tool install casebench` | Casebench calls the agent from outside, so the two need no shared environment |

`uv run --with` adds Casebench for that command only. Your `pyproject.toml` and lockfile stay as they are, which is how [`casebench guide`](/developers/guides/setup/coding-agent/) sets a project up.

```sh
uv run --with casebench casebench --version
```

To keep it in the project instead:

```sh
uv add --dev casebench
```

## Optional SDKs for the judge

Casebench calls OpenAI-compatible and Anthropic-compatible APIs over HTTP with no extra package. Three providers use the vendor's own SDK, which reads credentials the way your project already set them up. Install the one you use next to Casebench:

| Judge provider | Package |
| --- | --- |
| Google Gemini API or Vertex AI | `google-genai` |
| Amazon Bedrock | `boto3` |
| Azure OpenAI | `openai` |

`casebench init` checks that the chosen SDK imports and says what it found.

## The team server

Lawyers who review on a shared server use the `casebench-ee` package, installed on a machine they can reach. The engineer's machine needs only `casebench`. See [Run a team server](/developers/guides/team/team-server/).

## Next

- New to Casebench? [Try the demo](/developers/tutorials/demo/), then [Your first evaluation](/developers/tutorials/first-evaluation/).
- Using a coding agent? [Set up with a coding agent](/developers/guides/setup/coding-agent/).
