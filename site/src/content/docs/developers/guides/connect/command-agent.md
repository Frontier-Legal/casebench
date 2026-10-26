---
title: Connect a command
description: Run any script or command-line tool once per case, with the case inputs in its arguments, the answer on standard output, and its model calls recorded through routes.
sidebar:
  order: 3
---

Use a command target when your agent is a script or a command-line tool. Casebench runs it once per case and takes standard output as the answer.

```yaml title="casebench.yaml"
target:
  type: command
  run: node dist/ask.js --question {question}
  max_concurrency: 2
```

`casebench init --target command --run "node dist/ask.js --question {question}"` writes the block without `max_concurrency`, which defaults to 1.

## How the command line is built

- `run` is split into arguments the way a shell would split it, but no shell runs. Pipes, redirects and `$VAR` expansion do not apply. Wrap the command in a script if you need them.
- Each `{name}` is replaced by that case input, inside its own argument, so a question with spaces or quotes arrives intact. An input the case does not have fails that case, so name only inputs every case gives, such as `{question}`. `casebench target check` sends a question alone.
- Standard output, trimmed, is the answer. The judge lists its citations when it grades.
- A non-zero exit fails that case, not the run. The error shows the exit code and the last line the command wrote to standard error.

## Its environment

The command starts with Casebench's environment, plus:

- `TRACEPARENT`, the W3C trace context of the case;
- the variables that point its model clients at the recording proxy, such as `OPENAI_BASE_URL`.

Keys Casebench read from `.env` files are not in it. A key your shell sets is. The command loads its own settings as it does in production.

## Record its model calls

Casebench cannot reach inside the command's process, so its calls are recorded through routes. Each parser's built-in route sets its SDK's variable to the proxy. The proxy forwards each call to the address that variable held before, in your shell or in a file under `keys:`, and to the provider's default host when it held none.

So a script that uses the OpenAI SDK against another provider keeps calling that provider. This was run with `OPENAI_BASE_URL` set to a local stand-in for a model API:

```text frame="terminal"
answer     Fine, thanks.
citations  none
documents  none
steps      1 captured
  llm gpt-5.5
took       502 ms
```

If the code reads its base URL from a variable of its own, add a route for that variable. See [Command and HTTP targets use routes](/developers/guides/capture/model-calls/#command-and-http-targets-use-routes).

A call the command makes without going through a route, such as one to a base URL written in the code, is neither recorded nor held to the [perimeter](/developers/guides/setup/network/).

## Allow the hosts it calls

The proxy refuses a host `casebench.yaml` does not name. A script calling `api.openai.com` with no judge on the `openai` provider stops the check:

```text frame="terminal"
Error: Casebench refused a call to api.openai.com, which casebench.yaml does not name; if the run may call it, add it under `network: allow:` in casebench.yaml
```

Add the host under `network: allow:`. See [Allow the hosts your agent calls](/developers/guides/setup/network/).

## Check it

```sh
casebench target check
```

It sends "Hi. How are you?" as `{question}`. Pass `--question` to ask something else.

## When to choose another target

A command starts a new process per case. For an agent with a slow start, such as one that loads an index, serve it once over HTTP and use an [HTTP target](/developers/guides/connect/http-agent/) with a `start` command instead.
