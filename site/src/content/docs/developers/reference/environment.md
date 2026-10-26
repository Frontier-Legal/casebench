---
title: Environment variables
description: The variables Casebench reads for keys and settings, how it reads them from .env files, the ones it sets in your agent's environment during a run, and the team server's.
sidebar:
  order: 6
---

## Keys Casebench reads

Casebench reads a credential only from a variable your config names.

| Variable | Read by |
| --- | --- |
| `OPENAI_API_KEY` | The `openai` provider, unless its `api_key_env` names another, such as `OPENROUTER_API_KEY` |
| `ANTHROPIC_API_KEY` | The `anthropic` provider, unless its `api_key_env` names another |
| `CASEBENCH_CLOUD_KEY` | `casebench push`, `invite` and `pull`, and `check` when `cloud:` is set, unless `cloud.key_env` names another |
| any `${NAME}` | The headers of an HTTP target, an HTTP corpus or an MCP corpus; the address of an HTTP target, an HTTP corpus, an MCP corpus or the team server; and a capture route's `upstream`. A variable set nowhere is an error naming it. |

The `google`, `bedrock` and `azure` providers call through the vendor's SDK, which reads its own variables and sign-in from the environment, as your project already set them up.

### From the shell or a `.env` file

A variable the shell sets is read from the shell. When the shell does not set it, Casebench reads it from the `.env` file that `keys:` in `casebench.yaml` names for it:

```yaml title="casebench.yaml"
keys:
  OPENAI_API_KEY: .env
  COURT_API_KEY: research/eval.env
```

A key read from a file is held in Casebench's own memory. It is never set in the environment, so your agent, a command target, a `start` command and every other child process start without it, and the vendor SDKs of the `google`, `bedrock` and `azure` providers do not see it either. An MCP server Casebench starts gets the MCP library's minimal default environment.

`casebench keys NAME` lists the shell and every `.env` file in the project that gives a variable a value. It never prints a value: files that disagree show different fingerprints, the first 8 hex characters of each value's SHA-256. Casebench looks in files named `.env`, `.env.*` or `*.env`, and skips files ending in `.example`, `.sample`, `.template` or `.dist`, virtual environments, `node_modules` and hidden folders.

## Other variables Casebench reads

| Variable | Read by |
| --- | --- |
| `GITHUB_SHA` | `casebench run`, for the commit a run records when `--commit` is not given |
| a capture route's `env`, such as `OPENAI_BASE_URL` | The recording proxy. When the variable already holds a URL, in the shell or a `.env` file `keys:` names, the route forwards to that URL instead of its `upstream`. |

## Variables Casebench sets for your agent

During a run with capture on, in the environment of a Python worker, an HTTP target's `start` command or a command target:

| Variable | Value | When |
| --- | --- | --- |
| `OPENAI_BASE_URL` | `http://127.0.0.1:<port>/openai/v1` | Always, with the exception for Python workers below |
| `ANTHROPIC_BASE_URL` | `http://127.0.0.1:<port>/anthropic` | Always, with the exception for Python workers below |
| `GOOGLE_GEMINI_BASE_URL` | `http://127.0.0.1:<port>/gemini` | Always, with the exception for Python workers below |
| a route's `env` | `http://127.0.0.1:<port>/<route>` plus its `env_suffix` | For each route in `capture.routes` |
| `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` | `http://127.0.0.1:<port>/v1/traces` | Only with `capture.traces: true` |
| `CASEBENCH_FOLLOW` | `http://127.0.0.1:<port>`, and `http://127.0.0.1:<port>/w/<worker>` in a Python worker | Always. A Python worker sends every call through it, to the host the agent chose. |
| `CASEBENCH_PROXY` | `http://127.0.0.1:<port>` | Always. Used by Casebench's workers. |
| `CASEBENCH_PROXY_VARIABLES` | The names of the route variables Casebench set | Always. Used by Casebench's workers. |
| `CASEBENCH_SHADOWED` | The project's own value of each built-in route's variable, as JSON | Always. A Python worker puts those values back. |
| `CASEBENCH_STEP_FUNCTIONS` | `capture.functions`, as JSON | When the config names functions to record |

A Python worker sends each call through `CASEBENCH_FOLLOW` to the host your code chose, so a call and its key never go elsewhere. In the worker, a built-in route's variable that nothing had set stays unset, as your project had it. A route variable that points at the proxy gets the worker's own prefix, `http://127.0.0.1:<port>/w/<worker>/<route>`, so each call is attributed to its worker's case.

A command target also gets `TRACEPARENT`, the case's W3C trace context, per case. An HTTP target receives it as the `traceparent` header of each request.

`casebench proxy env` prints the lines for an agent you start yourself. `--no-capture` starts no proxy and sets none of them.

## The team server

`casebench-team serve` reads its settings from these variables, or from the options of the same names.

| Variable | Sets | Default |
| --- | --- | --- |
| `CASEBENCH_DATABASE_URL` | Postgres for a team, such as `postgresql://user@host/db`; SQLite works for a trial | `sqlite:///.casebench/team.db` |
| `CASEBENCH_PUBLIC_URL` | Where people open the app; sign-in links point here | `http://127.0.0.1:8080` |
| `CASEBENCH_HOST` | The address it listens on | `127.0.0.1`, `0.0.0.0` in the image |
| `CASEBENCH_PORT` | The port it listens on | `8080` |
| `CASEBENCH_RUNS` | The runs folder | `.casebench/runs`, `/data/runs` in the image |
| `CASEBENCH_SUITES` | Folders to look for suites in, separated by the path separator | `.`, `/data/suites` in the image |
| `CASEBENCH_CONFIG` | The `casebench.yaml` it reads | `casebench.yaml`, `/data/casebench.yaml` in the image |
| `CASEBENCH_SMTP_HOST` | The SMTP server that sends sign-in links. Without it, an admin copies each link from the Team page. | none |
| `CASEBENCH_SMTP_PORT` | Its port | `465` with `tls`, else `587` |
| `CASEBENCH_SMTP_SECURITY` | `starttls`, `tls` or `none` | `starttls` |
| `CASEBENCH_SMTP_USERNAME`, `CASEBENCH_SMTP_PASSWORD` | Its sign-in. The password is read from the environment only. | none |
| `CASEBENCH_SMTP_FROM` | The sender | `casebench@<SMTP host>` |
| `CASEBENCH_GOOGLE_CLIENT_ID`, `CASEBENCH_GOOGLE_CLIENT_SECRET` | Sign-in with Google, for invited emails Google has verified | none |
| `CASEBENCH_MICROSOFT_CLIENT_ID`, `CASEBENCH_MICROSOFT_CLIENT_SECRET` | Sign-in with Microsoft | none |

`casebench-team erase` reads `CASEBENCH_DATABASE_URL`, `CASEBENCH_RUNS` and `CASEBENCH_SUITES` the same way. `CASEBENCH_TEST_POSTGRES`, a Postgres server's URL, runs the team server's Postgres tests when you develop it. See [Run a team server](/developers/guides/team/team-server/).
