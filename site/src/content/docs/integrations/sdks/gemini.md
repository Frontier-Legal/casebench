---
title: Google Gen AI SDK
description: Record Gemini generateContent calls made with the Google Gen AI SDK, streamed or not, with no code change.
sidebar:
  order: 3
---

The `gemini` parser reads `generateContent` and `streamGenerateContent` calls: the model version, prompt and output token counts, latency, and function calls with their results. It reads a call whose path holds `/models/<model>:generateContent` or `/models/<model>:streamGenerateContent`, whatever the host.

## A Python agent

Nothing to set when the SDK sends through httpx or requests: the Python worker follows each call to the host it names. A call the SDK sends through another library, such as aiohttp, is not recorded. List `generativelanguage.googleapis.com` under `network: allow:`, and any other Google host the agent calls, such as a Vertex AI regional endpoint or the token host its credentials use.

## A command or HTTP agent

During a run Casebench sets `GOOGLE_GEMINI_BASE_URL` to `http://127.0.0.1:<port>/gemini` for a command target or a `start` command. The proxy forwards to the address that variable held before, in your shell or a file under `keys:`, and to `https://generativelanguage.googleapis.com` when it held none.

A Vertex AI endpoint read from a variable of your own needs a route with `parser: gemini`, as for [an OpenAI-compatible provider](/integrations/sdks/openai/#a-command-or-http-agent).

## Where `init` finds it

`casebench init` names `google-genai`, `google-generativeai` and `@google/genai` when your dependency files list them, and finds `google.genai.Client` in your Python code.

## Function calls without ids

Gemini may omit function-call ids. A call without one is paired with its result by the function's name.

## The judge

The `google` judge provider calls Gemini through Google's own SDK, which Casebench does not see. Its calls are outside the [perimeter](/developers/guides/setup/network/#what-the-perimeter-sees). See [Judge providers](/integrations/models/judge-providers/).

## Related

- [Record model calls](/developers/guides/capture/model-calls/).
