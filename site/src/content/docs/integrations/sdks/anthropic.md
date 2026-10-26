---
title: Anthropic SDK
description: Record Messages API calls made with the Anthropic SDK, in Python or TypeScript, with no code change.
sidebar:
  order: 2
---

The `anthropic` parser reads Messages API calls, streamed or not: the model, input and output tokens, latency, and the tool calls the model asked for, paired with their results in the next request. It reads a call whose path ends in `/v1/messages`, whatever the host.

## A Python agent

Nothing to set. The anthropic 1.x SDK sends through httpx2 and earlier versions through httpx, and the Python worker follows both to the host the call names. `ANTHROPIC_BASE_URL` keeps the value your settings give it.

```python
from anthropic import Anthropic

client = Anthropic()  # reads ANTHROPIC_API_KEY and ANTHROPIC_BASE_URL
```

List `api.anthropic.com` under `network: allow:` unless a judge already uses the `anthropic` provider. Otherwise the check stops:

```text frame="terminal"
target   failed: Casebench refused a call to api.anthropic.com, which casebench.yaml does not name; if the run may call it, add it under `network: allow:` in casebench.yaml
```

## A command or HTTP agent

The Python and TypeScript SDKs read `ANTHROPIC_BASE_URL`. During a run, Casebench sets it to `http://127.0.0.1:<port>/anthropic` for a command target or a `start` command. The proxy forwards to the address `ANTHROPIC_BASE_URL` held before, in your shell or a file under `keys:`, and to `https://api.anthropic.com` when it held none.

```ts
import Anthropic from '@anthropic-ai/sdk';

const client = new Anthropic(); // reads ANTHROPIC_API_KEY and ANTHROPIC_BASE_URL
```

A base URL from a variable of another name needs a route with `parser: anthropic`, as for [an OpenAI-compatible provider](/integrations/sdks/openai/#a-command-or-http-agent).

## Where `init` finds it

`casebench init` names the `anthropic` package on PyPI and `@anthropic-ai/sdk` on npm when your dependency files list them, and finds `anthropic.Anthropic` and `anthropic.AsyncAnthropic` in your Python code.

## Not read

Paths that do not end in `/v1/messages`, such as token counting at `/v1/messages/count_tokens`, pass through unchanged and become no step. Claude reached through a cloud provider's own API uses that provider's paths, which this parser does not read.

## The judge

The `anthropic` judge provider calls the Messages API and requires `max_tokens`. See [Choose the judge](/developers/guides/connect/judge/#set-model-options-by-name).

## Related

- [Record model calls](/developers/guides/capture/model-calls/).
- [Your first evaluation](/developers/tutorials/first-evaluation/).
