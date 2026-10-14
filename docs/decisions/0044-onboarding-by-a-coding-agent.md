---
status: accepted
date: 2026-10-14
decision-makers: Casebench maintainers
---

# A coding agent sets Casebench up from one prompt, and only `casebench.yaml` and `.casebench/` change

Amends [0043](0043-guided-onboarding.md) (who answers init's questions), [0040](0040-init-reads-the-code.md) (what happens to a client with a literal base URL) and [0036](0036-several-corpora.md) (what a corpus block holds).

## Context and problem statement

The guided `casebench init` of 0043 was run on a production legal agent on 2026-10-14. It still made a person do Casebench's work:

- it asked which JSON field of the data API was the id, the citation, the type and the passage, once for search results and once for documents;
- it asked which API a model provider speaks;
- it needed a Python function that calls the agent. That function then failed the live check, because the agent reads its own keys from the project's `.env` files, and nothing loaded them when Casebench started it.

Each answer needs knowledge of Casebench's internals or of the project's start-up. The person's own coding agent already reads the project, runs commands and fixes what fails, so it can supply the project knowledge these questions ask for.

Setup must also leave production code alone. A team will not let an evaluation tool edit the code it ships, and a reviewer should see at a glance that nothing it ships changed.

## Considered options

1. The user pastes one prompt into their coding agent. The agent follows a guide that the installed Casebench prints, and writes only `casebench.yaml` and `.casebench/`. Every command the guide uses runs without a terminal and reports in JSON.
2. An SDK called from the user's own code: the evaluation runs in-process, so the agent's environment is already there.
3. Keep the interactive init, and add more detection.

## Decision outcome

Chosen option 1, because it takes the project knowledge from the coding agent, which has it, and changes no file the team ships. Option 2 needs a line in the user's code to start an evaluation; option 1 gets the same environment without that line, through an adapter outside the shipped code. Option 3 was measured on 2026-10-14 and still asked six questions about Casebench's internals.

- **The prompt and the guide.** The README gives a prompt to paste: set up Casebench for this project by running `casebench guide` and following it. `casebench guide` prints the steps for the installed version, with the exact install spec this copy of Casebench came from. That spec is read from the package's install record (PEP 610 `direct_url.json`), so it is a PyPI version or a git URL.
- **What may change.** The guide lets the coding agent create `casebench.yaml` and files under `.casebench/`, and nothing else.
  - Casebench runs through `uv run --with <spec>`, or is installed into the venv of a pip project. So `pyproject.toml` and the lockfile stay as they are.
  - The guide's last step shows `git status`, so the user sees that only those paths appeared.
- **The adapter.** `.casebench/target.py` calls the agent after loading its settings the way the project's production start does. The coding agent reads that start-up from the project.
  - The file sits under `.casebench/`, because a folder named `casebench/` at the project root would shadow the package.
  - The Python target's worker puts the config's folder first on `sys.path`, so the adapter imports the project's packages as the project's root does, whichever folder Casebench runs from.
- **Commands a coding agent reads.**
  - `casebench check --json` gives each part's status, the reason in plain words and the next step. The exit code is non-zero when one part fails.
  - `casebench keys NAME --json` lists the `.env` files that hold a variable, with a fingerprint (0043) when their values differ. It never prints a value.
  - `casebench corpus probe http` runs one search and one fetch, and prints both responses so the coding agent can map the fields. The key is found by name in the shell or the project's `.env` files, as in 0043.
  - `corpus add` and `init` take `--key NAME=FILE`, which records where a key is read from, so a script never exports a key's value.
  - When a key is in several files that disagree, a command with no terminal stops and names the files and the flag. It never waits on a prompt.
- **A corpus keeps its probe.** `corpus add` stores the search it probed with as the corpus block's `probe`. `casebench check` uses it when no `--query` is given.
- **Literal base URLs are recorded.** A client created with a literal base URL now gets a capture route with no variable.
  - In a run, the Python target's worker sends that client's calls through the proxy. It rewrites requests for the route's upstream in httpx and requests, the HTTP libraries of the common model SDKs, and only inside the worker process.
  - Production never loads the worker, so the redirect never reaches it.
  - A command or HTTP target runs in its own process, which Casebench cannot hook. For those, the URL still has to be read from a variable, and init says so.
- **Providers whose package speaks another's API.** The model catalog's OpenRouter entry names its own package, `@openrouter/ai-sdk-provider`. OpenRouter documents its API as compatible with OpenAI's chat completions, and the catalog gives its address. So the OpenAI-compatible provider lists that package among those it speaks, and no API question is asked.
- **The judge.** The guide tells the coding agent to propose a judge from a family other than the agent's, using a key it found. That proposal is the one question the user is asked.

### Consequences

- Good, because a project is set up from one pasted prompt. The answers about the project come from an agent that reads it, and the user approves one judge.
- Good, because nothing the team ships changes. The adapter loads the agent's settings itself, so Casebench never hands its own keys to the agent (0043).
- Good, because every command the guide uses also serves scripts and CI: JSON out, no prompts.
- Bad, because the setup is only as good as the coding agent. `casebench check` is the arbiter: the guide is not finished until it passes, or until it says in plain words what cannot pass from here.
- Bad, because the redirect patches two HTTP libraries inside the worker. A client on another library, or a target outside Python, needs its URL read from a variable.

## Revisit when

- A coding agent following the guide on a real project changes a file outside `casebench.yaml` and `.casebench/`.
- Users ask to set up without a coding agent often enough that the interactive init needs the same reach.
- Learning a corpus from the agent's own traffic, a later step, makes `corpus probe` unnecessary.

## More information

- PEP 610, the `direct_url.json` install record: https://peps.python.org/pep-0610/
- OpenRouter's API reference, which documents its OpenAI-compatible chat completions: https://openrouter.ai/docs/api-reference/overview
