---
status: accepted
date: 2026-10-14
decision-makers: Casebench maintainers
---

# Init reads the project's own code, offline, to find its model clients, model names and entry points

Amends [0030](0030-set-up-here-run-there.md) (what `casebench init` asks) and [0019](0019-recording-proxy.md) (what a backend route records).

## Context and problem statement

A legal AI product often calls several providers: one model through an OpenAI-compatible endpoint for the agent, another vendor for embeddings or verification. `casebench init` asked for one provider, and the user typed its base URL, key variable and capture route by hand. Everything it needs is already in the checkout: the lock file names the SDKs, the code names each client's base URL and models, and it reads keys from variables whose names it spells out. The proxy captures a client only through a base-URL variable ([0019](0019-recording-proxy.md)), so init must also say when the code fixes its base URL instead. Rule 5 forbids sending any of this anywhere, and a key's value must never be read.

## Considered options

1. Parse the project's Python files with the standard library's `ast`, offline, reading only names and literals
2. Import the agent's modules and inspect the live objects
3. Ask the user, as before

## Decision outcome

Chosen option 1, because a syntax tree shows what the code calls without running it, and it reads nothing the user did not write.

- **What is read.** The project's own `.py` files: `git ls-files` (tracked and untracked, without ignored ones) inside a git checkout, else every file below the folder outside virtual environments, `node_modules` and hidden folders. Nothing is imported or run, and no request is made. The scan reports how many files it read.
- **Clients.** A call to a client class a capture parser names in its new `clients` list (`openai.OpenAI`, `anthropic.Anthropic`, `google.genai.Client`, …), under any import alias. Its `base_url` is either a literal, kept as written, or a variable read through `os.environ`/`os.getenv`, kept by the variable's name and its literal default. The same goes for `api_key`. A variable's value is never read.
- **Backends.** An `httpx` client, `httpx.Client(base_url=…)` or `AsyncClient`, is found the same way.
- **Model names.** Every string literal passed as `model=`, with its file and line. Their families come from the model catalog init already loads ([0032](0032-provider-catalog-and-sdk-providers.md)). When the chosen judge has one of those families, init warns as `casebench run` does ([0029](0029-statute-and-precedent-scores.md)).
- **Entry points.** The project's functions that reach a model call through other project functions. They are offered as `path:function` targets, those no other project function calls first, since they are nearest the user's question.
- **Routes.** For each client whose base URL is not its parser's default, init offers a capture route named after the host, forwarding to it and pointing the variable the code reads at the proxy. A client whose base URL is a literal cannot be routed without a code change, and init says where. A backend whose host is a configured `http` corpus gets a route that records searches as retrievals, with the corpus's id paths, and requests matching the corpus's `fetch_path` as document fetches, with the id taken from the path. To do that, a route gains `fetch_path`, and route fields may be any YAML value.
- **Python only.** Agents in other languages are reached through the HTTP and command targets with no detection.

### Consequences

- Good, because a two-provider agent is set up with its routes and entry point from what its code already says.
- Good, because the scan cannot leak anything: it opens files, parses them and prints names.
- Bad, because a client built by a helper Casebench cannot see through, such as a factory function or a dependency-injection container, is missed. The user adds its route by hand, as before.
- Bad, because a base URL built at run time from several variables is shown as not found.

## Revisit when

- Agents written in TypeScript or another language ask for the same detection.
- Clients built through a framework (LangChain, LlamaIndex, LiteLLM) are common enough to be listed as clients.

## More information

- Python's [`ast`](https://docs.python.org/3/library/ast.html) module; `git ls-files --cached --others --exclude-standard`.
