---
title: Allow the hosts your agent calls
description: A run calls only the hosts casebench.yaml names. List the others your agent calls under network allow, read the refusal when a host is missing, and know what the perimeter cannot see.
sidebar:
  order: 4
---

A run calls only the hosts `casebench.yaml` names. Any other host is refused before the request leaves, and the run stops. A host you already chose for the target, a judge or a corpus needs nothing more. A host only your agent's code calls, such as its model provider, goes under `network: allow:`.

## Which hosts a run may call

- Loopback: `localhost`, `127.0.0.0/8` and `::1`.
- The target's `url`, for an HTTP target.
- Each judge's and extraction model's provider address: its `base_url`, or the provider's own default, such as `api.openai.com` for the `openai` provider.
- Each corpus's `base_url` or `url`.
- Each capture route's `upstream` under `capture.routes`.
- The team server's `cloud: url:`.
- Each host under `network: allow:`.

A `${NAME}` in one of these addresses is read as everywhere else, from the shell or a file under `keys:`. Casebench compares hosts in lower case and without their port.

The parsers' built-in routes do not count. If your agent calls `api.anthropic.com` and no judge uses the `anthropic` provider, list it.

## List the hosts your agent calls

```yaml title="casebench.yaml"
network:
  allow:
    - api.anthropic.com
    - "*.search.windows.net"
```

- Write a host alone, with no scheme, port or path. `https://api.anthropic.com` never matches.
- `*.example.com` allows every host under `example.com`, such as `eu.api.example.com`, and not `example.com` itself. List both if the agent calls both.
- Quote an entry that starts with `*`, since YAML reads a bare `*` as an alias.

Add a host when you find the agent calling it in its code or settings. A coding agent that follows `casebench guide` does the same, and shows you each host it added.

## When a host is missing

`casebench check` fails its target part and names the host:

```text frame="terminal"
corpus   passed: 1 document sampled
target   failed: Casebench refused a call to api.anthropic.com, which casebench.yaml does not name; if the run may call it, add it under `network: allow:` in casebench.yaml
```

With `--json`, the part's `next` is "ask the user before allowing it". A host you do not recognise is worth a look in the agent's code before you allow it.

During `casebench run`, the recording proxy answers the agent's call with `403` and the same reason, and the run stops with that error. The case that made the call is not stored, so once you allow the host, running again with the same `--run-id` sends that case again. See [Run a suite and resume it](/developers/guides/runs/run-and-resume/).

## Redirects to another host are refused

A response that redirects to another host stops the run the same way. The error names both hosts:

```text frame="terminal"
Casebench refused a redirect from api.example.com to login.example.net: a run never follows a redirect to another host
```

This holds in every client Casebench sends through, the proxy included. Casebench's own clients follow no redirect at all. The model catalog's client follows a redirect within its own host only.

## Which commands enforce it

These commands hold every call to the perimeter, once they have read `casebench.yaml`:

- `casebench run` and `casebench import`, for a sheet of answers
- `casebench check` and `casebench target check`
- `casebench corpus check`
- `casebench extract` and `casebench generate`
- `casebench case new` and `casebench case resolve`
- the check at the end of `casebench init`
- the workbench, when it checks a setup or tries a question

`casebench init` before that check, `corpus add`, `corpus probe` and `models` run without a perimeter. They call the hosts you name on the command line, or the public model catalog, to build a config that does not exist yet.

`casebench run`, `casebench import` and `casebench extract` also read two public price lists before the perimeter starts: OpenRouter's at `https://openrouter.ai/api/v1/models` and the model catalog at `https://models.dev/api.json`. They send nothing of yours. The last lists read are kept in `.casebench/prices.json` for when the network is out of reach.

## What the perimeter sees

The perimeter covers every request that passes through a Casebench client:

- Casebench's own calls: the judges, the extraction models, the HTTP target, the HTTP and MCP corpora, and the team server.
- A Python agent's calls through httpx2, httpx or requests. The worker sends each one through the recording proxy, which checks the host before it forwards. See [Record model calls](/developers/guides/capture/model-calls/).
- A command or HTTP agent's calls through a route, that is, through a variable that points the agent's client at the proxy.

It cannot see:

- a Python agent's calls through another client, such as aiohttp, gRPC, boto3 or a raw socket;
- a command or HTTP agent's calls that do not go through a route;
- a corpus served by a local MCP server process, which makes its own calls;
- a judge on Azure, Bedrock or Google, which Casebench calls through the vendor's own SDK;
- any agent call in a run with `--no-capture`, since the proxy is off.

For these, your firm's firewall is the control. The perimeter keeps Casebench to the hosts you chose. It does not replace network policy around the agent's process.

## Related

- [The perimeter](/developers/concepts/perimeter/), and why a run has one.
- [Keep keys out of the config](/developers/guides/setup/keys/): how keys are scrubbed from what a run writes.
- [Configuration reference](/developers/reference/configuration/).
