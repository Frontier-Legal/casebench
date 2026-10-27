---
title: The perimeter
description: Why a run calls only the hosts casebench.yaml names, refuses redirects to other hosts, and scrubs every key from what it writes.
sidebar:
  order: 9
---

An evaluation sends your agent questions, sends its answers to a judge, and searches your corpus. A setup that quietly called anything else would be hard to approve for client data. So a run has a perimeter: the hosts it may call are the ones your config already names, and nothing else.

## The hosts a run may call

- Loopback: `localhost`, `127.0.0.0/8` and `::1`. A call to the same machine leaves nothing.
- The hosts `casebench.yaml` names for the target, each judge and extraction model (its `base_url`, or the provider's own default), each corpus, each capture route's upstream, and the team server.
- Each host under `network: allow:`. `*.example.com` allows every host under `example.com`, but not `example.com` itself.

A host is compared without its port, in lower case. A host you already chose for a judge or a corpus needs no second listing; a host only your agent's code calls, such as its model provider, does.

## Where it is enforced

In every client Casebench sends through, before the request leaves: the judge and extraction models, the HTTP target, the HTTP and MCP corpora, and the recording proxy, which covers what your agent sends. Every command that calls out for a configured setup enforces it: `run`, `check`, `target check`, `corpus check`, `extract`, `generate`, `case new`, `case resolve`, `import`, and the check that ends `init`.

A refused host stops the run. The proxy answers the agent with 403, the case is not stored, so a resumed run sends it again, and the error names the host and the setting. A response that redirects to another host is refused the same way.

## Keys never reach a file

Every line a run writes, `run.json`, `results.jsonl`, `judge.jsonl`, each score set and `report.json`, is scrubbed before it is written: each key read from a `.env` file and each variable the config names becomes `${NAME}`, and a credential seen only in a header becomes `[credential]`. Recorded calls never hold request headers.

A key read from a `.env` file stays in Casebench's own memory and is never put in the environment, so your agent and every other child process start without it. A model key goes only to its provider's configured address, and a corpus key only in that corpus's configured headers.

## What it does not replace

The perimeter keeps Casebench from calling what you did not choose. It is not a firewall for your agent's own process outside a run, and it does not replace your firm's network controls.

## Related

- [Allow the hosts your agent calls](/developers/guides/setup/network/).
- [Keep keys out of the config](/developers/guides/setup/keys/).
- [Privacy and what leaves your machine](/developers/concepts/privacy/).
