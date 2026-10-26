---
title: Set up with a coding agent
description: Paste one prompt into the coding agent you use in your project. It runs casebench guide, writes casebench.yaml and an adapter under .casebench/, and stops when casebench check passes.
sidebar:
  order: 1
---

The coding agent you already use in your project can set Casebench up for you. It reads the project, so it can answer the questions setup asks: which function answers a legal question, how production loads its settings, which document store the agent searches. You answer one question: which judge model to pay for.

## The prompt

Paste this into the coding agent, in the agent's repository:

```text
Set up Casebench for this project. Run `uvx casebench guide` and follow it.
```

`casebench guide` prints the setup steps for the installed version of Casebench. The coding agent follows them in order. The guide ends when `casebench check` passes, or when the coding agent can say in plain words what cannot pass from this machine.

## What may change

The guide lets the coding agent create two things and nothing else:

- `casebench.yaml`, at the project's root;
- files under `.casebench/`.

It does not touch the agent's code, `pyproject.toml`, a lockfile or `.gitignore`. Casebench runs without being installed into the project. In a uv project every command runs as `uv run --with "casebench==0.5.1" casebench <command>`, so the project's own dependencies are there and its lockfile stays as it is. In a pip project the guide installs Casebench into the project's virtual environment. The guide prints the exact spec for the copy of Casebench you ran: a version from PyPI, or a git URL pinned to its commit.

The guide's last step runs `git status --short`. Only `casebench.yaml` and `.casebench/` should appear. If anything else does, the coding agent broke a rule; revert that file.

The guide also tells the coding agent never to open a `.env` file, and never to read, print or copy a key's value.

## The adapter

The coding agent writes `.casebench/target.py` with one function:

```python title=".casebench/target.py"
def answer(question: str, facts: str | None = None) -> str | dict: ...
```

The function does what production does before it answers, such as loading the same `.env` files or calling the project's settings loader, then calls the function production calls with a user's question. It returns a string, or a mapping with `answer` and, when the agent gives them, `citations` and `documents`.

The file sits under `.casebench/` because a folder named `casebench/` at the project's root would shadow the package. Casebench puts the project's folder first on the import path, so the adapter imports the project's packages as code at the root does.

The adapter leaves the agent's base URLs and keys as its settings set them. Casebench records each model call and search where it goes, without changing where it goes, so a key reaches only the host the agent's own settings chose.

The coding agent also writes `.casebench/.gitignore`:

```text title=".casebench/.gitignore"
*
!.gitignore
!target.py
!casebench.schema.json
```

Runs, caches and keys stay out of git. The adapter, and the schema your editor checks `casebench.yaml` against, are committed.

## Commands the coding agent reads

Every command the guide uses runs without a terminal and never prompts. When a command needs an answer it cannot get, it stops and names the flag that gives it.

| Command | What it prints |
| --- | --- |
| `casebench guide` | The setup steps for the installed version |
| `casebench keys NAME --json` | The `.env` files that set `NAME`, each with a fingerprint, and whether their values agree. Never a value. |
| `casebench models --json` | The model catalog's providers, with the variable each one's key is read from |
| `casebench models PROVIDER --json` | That provider's models, with family, price per million tokens and context window |
| `casebench corpus probe http ...` | One search with `--query`, or one fetch with `--fetch`, as JSON, so the coding agent can map the store's fields |
| `casebench check --json` | Each part's status, the reason and the next step |

`casebench keys` names files, never values:

```text frame="terminal"
$ casebench keys CASEBENCH_CLOUD_KEY --json
[
  {
    "name": "CASEBENCH_CLOUD_KEY",
    "in_shell": false,
    "files": [
      {
        "file": ".env",
        "fingerprint": "d55f0dfd"
      }
    ],
    "values_agree": true
  }
]
```

When `values_agree` is false, two files hold different values. The coding agent asks you which file is current, then passes `--key NAME=FILE` to the commands that need that key. `casebench.yaml` records the name and the file under `keys:`, never the value.

`casebench check --json` gives one object per part:

```json
{
  "passed": false,
  "parts": [
    { "part": "corpus", "status": "passed", "passed": true, "reason": "1 document sampled", "next": "" },
    {
      "part": "target",
      "status": "failed",
      "passed": false,
      "reason": "AgentError: KeyError: 'Hi. How are you?'",
      "next": "make the target answer: its function must run as the project's own start runs it, with the settings the agent reads loaded first"
    }
  ],
  "advice": []
}
```

The exit code is non-zero when a part fails. The coding agent fixes the adapter or a flag and runs `check` once more.

## What setup spends

The guide limits calls that cost money. These are the only commands it runs that call out:

| Command | Spends |
| --- | --- |
| `casebench corpus probe http` | 1 search for 1 result with `--query`, 1 document with `--fetch` |
| `casebench corpus add http` | 1 search for 1 result, and 1 document |
| `casebench check` | 1 search for 1 result and 1 document, 1 message to the agent ("Hi. How are you?"), and 1 short call to each judge and each extraction model |

The guide forbids `casebench corpus check` and `casebench run` during setup.

## The steps the guide gives

1. Find the function production calls with a legal question, and what production does before it can run.
2. Write `.casebench/target.py` and `.casebench/.gitignore`.
3. Run `casebench keys NAME --json` for each variable Casebench reads itself: the judge's key, the store's key, and the store's URL when the project keeps it in a variable.
4. Propose a judge from a different model family than the agent's models, and two extraction models from two different families, using providers whose keys it found. This is the one question you are asked. Say yes, or name others; the judge is billed on each run, the extraction models once, when the first run builds its suite.
5. Run `casebench init` with flags only:

   ```sh
   casebench init --entry .casebench/target.py:answer --corpus none \
     --judge-provider PROVIDER --judge-model MODEL \
     --extract PROVIDER_1 MODEL_1 --extract PROVIDER_2 MODEL_2 --no-routes --no-live --yes
   ```

   Then it makes sure `agent_models:` lists the agent's own models, with their families from `casebench models PROVIDER --json` and no price. Each run checks the judge's family against them and looks their prices up.
6. Connect the document store: for a document API, `casebench corpus probe http`, then `casebench corpus add http` with the JSONPaths it read from the two responses; for an MCP server, `casebench corpus add mcp`; for a folder of decisions, a `corpora:` block in `casebench.yaml`.
7. Run `casebench check --json` and fix what fails. Each host the agent calls on its own, such as its model API, goes under `network: allow:`, taken from the agent's code. See [Allow the hosts your agent calls](/developers/guides/setup/network/).
8. Run `git status --short` and tell you what it set: the adapter, the judge, the corpus, each allowed host and where the code calls it, and the result of `check`.

## After setup

The coding agent stops at a passing `check`. A first `casebench run` with no suite then builds one from your corpus with the two extraction models, after it says what that costs and you agree; see [Run a suite, and resume one](/developers/guides/runs/run-and-resume/). Lawyers can write cases instead; see [Add lawyer-written cases](/developers/guides/suites/lawyer-cases/).

After a first evaluation, the guide has the coding agent ask once whether lawyers will review on a team server. With an address, it runs `casebench init --team-server URL --no-routes --yes`, asks you to set `CASEBENCH_CLOUD_KEY` yourself, and runs `casebench check`. It never asks for the key. See [Invite lawyers to a team server](/developers/guides/team/invite-lawyers/).

## The setup skill

A coding agent that reads skills from a folder can take the same steps as a skill. Copy `skills/casebench-setup/` from the Casebench repository into the coding agent's skills folder, then ask it to set up Casebench for the agent and run the first evaluation.

The skill runs `casebench guide` and follows it, so the guide stays the one source of the steps. It then goes further than the guide:

1. It runs `casebench run` with no `--suite`. With extraction models in the config, that prints the extraction estimate and stops, because nothing answers its question. Without them, it stops and asks for `extract:`.
2. It shows you the estimate and asks whether to go on. On yes, it runs `casebench run --yes`.
3. It runs `casebench ui` and tells you what the run found: its error rates and the first failed answer.
4. It asks whether lawyers will review on a team server.

## Without a coding agent

Run `casebench init` in the project. It reads the code, then asks whether to set up in the browser or in the terminal. See [Set up in the workbench](/developers/guides/setup/workbench/).

## Related

- [Command line reference](/developers/reference/cli/): `guide`, `keys`, `models`, `corpus probe`, `check`.
- [Keep keys in .env files](/developers/guides/setup/keys/).
- [The perimeter](/developers/concepts/perimeter/).
