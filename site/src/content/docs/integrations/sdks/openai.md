---
title: OpenAI SDK
description: Record Chat Completions calls made with the OpenAI SDK, at OpenAI or any provider that speaks its API, such as OpenRouter, with no code change.
sidebar:
  order: 1
---

The `openai` parser reads Chat Completions calls, streamed or not: the model, input and output tokens, latency and the tool calls the model asked for, paired with their results in the next request. It reads a call whose path ends in `/chat/completions`, whatever the host, so it serves OpenAI and every provider that speaks the same API, such as OpenRouter.

## A Python agent

Nothing to set. The openai 3.x SDK sends through httpx2 and earlier versions through httpx, and the Python worker follows both to the host the call names. The client may read its base URL from `OPENAI_BASE_URL`, from a variable of your own, or from a literal:

```python
from openai import OpenAI

client = OpenAI()  # api.openai.com, or OPENAI_BASE_URL as your settings set it
router = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.environ["OPENROUTER_API_KEY"])
```

Both are recorded, each at its own host. List each host the agent calls under `network: allow:`, such as `api.openai.com` and `openrouter.ai`, unless a judge already uses it. See [Allow the hosts your agent calls](/developers/guides/setup/network/).

## A command or HTTP agent

The Python and TypeScript SDKs read `OPENAI_BASE_URL`. During a run, Casebench sets it to `http://127.0.0.1:<port>/openai/v1` for a command target or a `start` command. The proxy forwards to the address `OPENAI_BASE_URL` held before, in your shell or a file under `keys:`, and to `https://api.openai.com` when it held none.

```ts
import OpenAI from 'openai';

const client = new OpenAI(); // reads OPENAI_API_KEY and OPENAI_BASE_URL
```

When your code reads the address from a variable of its own, add a route that points that variable at the proxy:

```python
client = OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"])
```

```yaml title="casebench.yaml"
capture:
  routes:
    - name: llm
      upstream: https://llm.example.com
      parser: openai
      env: LLM_BASE_URL
      env_suffix: /v1
```

For a command or HTTP target, `casebench init` offers this route, named after the host, when it finds a Python client whose base URL comes from a variable with a default in the code, such as `os.environ.get("LLM_BASE_URL", "https://llm.example.com/v1")`. With no default, as above, write the route by hand. A base URL written as a literal cannot be routed for these targets without a code change. `init` says where it is.

## Where `init` finds it

`casebench init` names the `openai` package when your dependency files list it: `pyproject.toml`, `uv.lock`, `requirements.txt` or `package.json`. In Python code it finds `openai.OpenAI`, `openai.AsyncOpenAI`, `openai.AzureOpenAI` and `openai.AsyncAzureOpenAI`, under any import alias.

## Streams report tokens through a route

For a streaming request through a route that does not ask for usage, the proxy adds `stream_options.include_usage`, so the stream reports its tokens. It changes nothing else. A Python agent's followed calls are forwarded as sent, so a stream that does not ask for usage is recorded without token counts.

## Not read

The parser reads Chat Completions only. Calls to other endpoints, such as the Responses API at `/responses` or embeddings, still pass through the proxy unchanged and are held to the perimeter, but they do not become model-call steps.

## The judge

The `openai` judge provider calls Chat Completions too, at OpenAI or at any address you give as `base_url`. `casebench init --judge-provider openrouter` writes it with OpenRouter's address, because OpenRouter documents its API as compatible with OpenAI's chat completions. See [Choose the judge](/developers/guides/connect/judge/) and [Judge providers](/integrations/models/judge-providers/).

## Related

- [Record model calls](/developers/guides/capture/model-calls/).
- [Anthropic SDK](/integrations/sdks/anthropic/) and [Google Gen AI SDK](/integrations/sdks/gemini/).
