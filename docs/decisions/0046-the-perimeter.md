---
status: accepted
date: 2026-10-15
decision-makers: Casebench maintainers
---

# A run calls only the hosts its config names, never follows a redirect to another host, and writes no key

Implements what [0007](0007-no-telemetry.md) and the security rules in [open-source.md](../design/open-source.md) promise: "The runner refuses hosts outside the configured allowlist", "cross-host redirects refused", "auth headers redacted". Amends [0019](0019-recording-proxy.md) and [0044](0044-onboarding-by-a-coding-agent.md) (what the proxy forwards).

## Context and problem statement

A firm's security officer approves a tool near client data only with proof of where its calls go. Until now, Casebench checked no host:

- the proxy's follow path forwarded a Python agent's call to any host the call named;
- a redirect from an upstream reached the agent unchanged, and the agent's client followed it through the proxy to whatever host it named;
- a run wrote a failed case's error, and a scoring error, as the exception said it, so an error that echoed a request could put a key in `results.jsonl` or a score set.

Casebench's own clients (the judge and extraction models, the HTTP target, the HTTP corpus) never followed a redirect, but they would call any host the config gave without a check.

## Considered options

1. The allowlist is the hosts `casebench.yaml` already names, plus the hosts listed under `network: allow:`. A run refuses any other host, and stops.
2. Only the hosts under `network: allow:`, so every host is listed twice: once where it is used, once in the list.
3. An operating-system firewall around the agent's process, set up by Casebench.

## Decision outcome

Chosen option 1, because a host the config names for the target, a judge or a corpus is one the user chose already, and listing it a second time adds nothing a reviewer can read. Option 3 needs privileges a run should not have, differs per operating system, and is the firm's own firewall's job.

- **Which hosts a run may call.**
  - Loopback: `localhost`, `127.0.0.0/8` and `::1`. A call to the same machine leaves nothing.
  - The target's `url`, each judge's and extraction model's provider address (its `base_url`, or the provider's own default), each corpus's `base_url` or `url`, and each capture route's `upstream`, as `casebench.yaml` gives them. A `${NAME}` is read as it is everywhere else.
  - Each host under `network: allow:`. `*.example.com` allows every host under `example.com`, and not `example.com` itself.
  - A host is compared without its port, in lower case.
- **Where it is enforced.** In every client Casebench sends through, before the request leaves: the judge and extraction models, the HTTP target, the HTTP and MCP corpora, and the proxy. The proxy covers what a Python agent sends through httpx2, httpx or requests (0044), and what a command or HTTP agent sends through a route.
- **A refused host stops the run.** The proxy answers the agent with 403 and the reason. The case is not stored, so the run sends it again when it is resumed. The run stops with an error that names the host and says how to allow it: add it under `network: allow:` if the agent may call it. `casebench check` fails its part with the same words.
- **When it applies.** In every command that calls out for a configured setup: `run`, `check`, `target check`, `corpus check`, `extract`, `generate`, `case new`, `case resolve`, and the check that ends `init`. Until that last check, `init`, and `corpus add`, `corpus probe` and `models`, choose hosts or read the public model catalog: they call the hosts the user names on the command line, before there is an allowlist to read.
- **Redirects.** A response that redirects to another host is refused, in every client Casebench sends through, the proxy included, and stops the run as a refused host does. Casebench's own clients follow no redirect. The model catalog's client follows a redirect within its own host only.
- **Setting it up.** The guide has the coding agent list under `network: allow:` the hosts it finds the agent calling in its code and settings, and show them to the user. A host refused during `check` is added only when the agent's code calls it.
- **Keys.** Every line a run writes (`run.json`, `results.jsonl`, each score set, `report.json`, the judge's replies in `judge.jsonl`) is scrubbed before it is written:
  - each key read from a `.env` file (0043);
  - each variable a header or a provider's key names in `casebench.yaml`;
  - each credential a call carried: the value of an `Authorization`, `Proxy-Authorization`, `x-api-key`, `api-key` or `x-goog-api-key` header that Casebench sent or the proxy forwarded, kept in memory for the run.

  A named variable becomes `${NAME}` and a credential seen only in a header becomes `[credential]`. Recorded calls never held headers (0019), and still do not.
- **Output is data.** A model's output is stored as text and shown as text. Nothing evaluates it, expands a template or a variable in it, or reads markup in it. A viewer, when there is one, is held to the same test.

### Consequences

- Good, because a reviewer reads one file to know every host a run may call, and a refusal names the host in plain words.
- Good, because a resumed run sends the refused case again, once the host is allowed.
- Bad, because a Python agent that calls a host through another client (aiohttp, gRPC, a raw socket, boto3), a command or HTTP agent that calls a host directly, and a corpus served by a local MCP server process, and a cloud provider called through its own SDK (Azure, Bedrock, Google) are outside what Casebench can see. Only a firewall binds them, and the documentation says so.
- Bad, because a setup made before this decision stops at the first host its agent calls that the config does not name, until it is listed. The error says which host, and how to list it.

## Revisit when

- A common agent stack sends its calls through a client the proxy does not see, so most of its traffic is outside the allowlist.
- Users ask for a mode that only records the hosts called, without refusing them.

## More information

- RFC 9110 section 15.4 (redirection) and section 11.6.2 (`Authorization`).
- [OWASP LLM05: improper output handling](https://genai.owasp.org/llmrisk/llm052025-improper-output-handling/).
