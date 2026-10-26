---
title: casebench.yaml
description: "Every key of casebench.yaml: the target, the corpora, the judges, the extraction models, capture, the agent's models, keys, the network, the workbench and the team server."
sidebar:
  label: Configuration
  order: 2
---

`casebench.yaml` sits in your agent's project and is meant to be committed. It holds no secrets. Each credential is named by the variable that holds it, `${NAME}` in a header reads that variable at run time, and `keys:` names the `.env` file a variable is read from when the shell does not set it.

`casebench init` writes the file. The workbench's Settings, Jurisdictions and Models pages save the same sections. Every command reads `casebench.yaml` in the current folder, and `--config FILE` names another.

```yaml title="casebench.yaml"
# yaml-language-server: $schema=.casebench/casebench.schema.json
target:
  type: python
  entry: .casebench/target.py:answer
corpora:
  court-api:
    connector: http
    jurisdictions: [GB]
    holds: [decisions]
    probe: unfair dismissal
    link: https://example.com/decisions/{id}
    options:
      base_url: ${COURT_API_URL}
      headers:
        Authorization: Bearer ${COURT_API_KEY}
      search_path: /search
      search_params: { q: "{text}" }
      search_ids: $.results[*].id
      fetch_path: /documents/{id}
      fields: { id: $.id, jurisdiction: $.country, court: $.court, date: $.date, text: $.body }
judge:
  provider: openai
  model: gpt-5.5
  options: { api_key_env: OPENAI_API_KEY, family: gpt }
agent_models:
  - { model: claude-sonnet-5-5, family: claude }
keys:
  OPENAI_API_KEY: .env
  COURT_API_KEY: .env
  COURT_API_URL: .env
network:
  allow: [api.anthropic.com]
workbench:
  try_daily_limit_usd: 5
cloud:
  url: https://casebench.firm.example
```

## Top-level keys

| Key | Holds |
| --- | --- |
| `target` | The AI under test |
| `corpus` or `corpora` | The document stores citations are checked against |
| `judge` or `judges` | The model that grades answers, or two of different families |
| `extract` | The two models that read answer keys out of court decisions |
| `capture` | The recording proxy's port, routes and functions |
| `agent_models` | The models your agent calls, with their family |
| `keys` | Which `.env` file each variable is read from |
| `network` | Hosts a run may call besides the ones the config names |
| `workbench` | What trying a question may spend, and whether golden data needs a second editor |
| `cloud` | The team server `push`, `invite` and `pull` talk to |

Each key is optional, and a command that needs one says so. A key Casebench does not know is an error that names where it is, so a typo fails at once. A script path in `target.entry` or `capture.functions` is read relative to the folder `casebench.yaml` is in.

## Validate in your editor

`casebench init` starts the file with this line:

```yaml
# yaml-language-server: $schema=.casebench/casebench.schema.json
```

It also writes `.casebench/casebench.schema.json`, the JSON Schema of the config as the installed Casebench reads it. An editor with YAML language support reads the first line and checks every key as you type, with completion. When `init` runs again on a file that starts with this line, it rewrites the schema for the version you have installed, so the editor checks against the version that reads the file. When it updates a file that lacks the line, it adds it. The workbench writes the line and the schema each time it saves the file.

## target

The AI under test. `type` selects the shape: `python`, `http`, `command`, or a target plugin's name. `source` names the distribution to load when two installed plugins register the same type.

### `type: python`

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `entry` | string | required | `path/file.py:function` or `package.module:function` |
| `max_concurrency` | integer | `1` | Worker processes, each answering one case at a time |

Casebench adds `root`, the config's folder, and puts it first on the agent's import path, so an adapter such as `.casebench/target.py` imports the project's packages as code at the project's root does.

### `type: http`

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `url` | string | required | The endpoint |
| `method` | string | `POST` | The HTTP method |
| `headers` | map | `{}` | Sent with every request. `${NAME}` reads the shell, then the keys `keys:` names. |
| `body` | any | required | A JSON template for the request body. `"{{name}}"` alone becomes the case input with its JSON type; inside longer text it becomes text. `null` sends no body. |
| `answer` | JSONPath | required | Where the response holds the answer text |
| `citations` | JSONPath | | Where it holds the citations |
| `documents` | JSONPath | | Where it holds the ids of the documents used |
| `start` | string | | A command Casebench starts, then waits on until `url` answers, before the first case. It is stopped after the run. |
| `timeout_s` | number | none | Per request. No timeout unless set. |
| `max_concurrency` | integer | `1` | Requests at once |

### `type: command`

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `run` | string | required | Split like a shell would split it, without starting one. `{name}` in each argument becomes the case input. |
| `max_concurrency` | integer | `1` | Processes at once |

The command prints the answer on standard output. A non-zero exit fails the case, with the last line of standard error as the reason.

## corpus and corpora

`corpus:` is the form for one store. `corpora:` maps names to stores; a name is lower-case letters, digits and hyphens. Give one or the other. `casebench init` and `casebench corpus add` write named entries under `corpora:`. `corpus add` refuses to add a second store to a file that uses `corpus:`, and prints both stores under `corpora:` for you to paste.

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `connector` | string | required | `folder`, `http`, `mcp`, or a connector plugin's name |
| `options` | map | `{}` | The connector's options, below |
| `jurisdictions` | list of codes | every one | ISO 3166-1 alpha-2, ISO 3166-2 or `EU`. `UK` and `EL` are read as `GB` and `GR`. |
| `holds` | list | both | `decisions`, `statutes` |
| `search_filters` | map | `{}` | Per kind of citation, `statute` or `decision`, the parameters a search adds |
| `metered` | string | `none` | `search`, `fetch` or `none`: what the provider charges for |
| `keep` | list | see below | `documents`, `searches`: what may be kept on disk. Left out, documents are kept, and searches when `metered: search`. |
| `probe` | string | | A search known to find a document. `corpus add` stores the one it was added with, and `casebench check` and `corpus check` run it when no `--query` is given. |
| `link` | string | | Where a person reads a document on the provider's site, with `{id}` for its id. A review spreadsheet links each court fact to its decision through it. |
| `profile` | string | | The profile the options came from. Recorded, never read again. |
| `connector_source` | string | | The distribution to load when two register the same connector |

A corpus whose URL is the HTTP target's own endpoint is refused: a system must not confirm its own citations.

### Folder options

| Key | Meaning |
| --- | --- |
| `path` | A folder of JSON files, one [document](/developers/reference/formats/document/) each, relative to the folder that holds `casebench.yaml` |

### HTTP options

| Key | Default | Meaning |
| --- | --- | --- |
| `base_url` | required | The API root. Paths below are relative to it. It may be a variable, such as `${COURT_API_URL}`, read like a header's key. |
| `headers` | `{}` | `${NAME}` reads the shell, then the keys `keys:` names |
| `fetch_path` | required | With `{id}`, such as `/documents/{id}` |
| `search_path` | required | Such as `/search` |
| `search_params` | `{q: "{text}"}` | Query parameters. `{text}` and `{limit}` are filled per call. |
| `search_body` | | A JSON body. With it, a search is a POST of this body with `{text}` and `{limit}` filled, and `search_params` is not sent. |
| `search_ids` | `$` | JSONPath to the ids in a search response |
| `search_results` | | JSONPath to each result, to read `result_fields` from |
| `result_fields` | `{}` | `id`, `citation`, `type` and `passage`, as JSONPath inside one result. `id` is required with `search_results`. |
| `fields` | `{}` | Document fields as JSONPath: `id`, `jurisdiction`, `court`, `date`, `text`, `level` |
| `list_path`, `list_ids` | | For a store that can list its documents: the path, and JSONPath to the ids in its response |
| `timeout_s` | none | Per request |

### MCP options

| Key | Default | Meaning |
| --- | --- | --- |
| `command` | | A list: the program and its arguments, which start the server over stdio |
| `url` | | A Streamable HTTP endpoint. Give `command` or `url`. |
| `headers` | `{}` | Sent over HTTP. `${NAME}` reads the shell, then the keys `keys:` names. |
| `search_tool` | | The tool that searches |
| `search_arguments` | `{query: "{text}"}` | An argument whose whole value is `{text}` or `{limit}` is filled per call |
| `search_ids`, `search_results`, `result_fields` | | As for HTTP |
| `fetch_tool` | | The tool that fetches one document |
| `fetch_arguments` | `{id: "{id}"}` | An argument whose whole value is `{id}` is filled per call |
| `fields` | `{}` | As for HTTP |

A connector plugin takes the options its own constructor takes.

## judge and judges

`judge:` is the form for one. `judges:` lists two, which must be of different model families. A citation or a criterion then passes only when both judges pass it.

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `provider` | string | required | `openai`, `anthropic`, `google`, `bedrock`, `azure`, or a provider plugin's name |
| `model` | string | required | The model id. There is no default model. |
| `options` | map | `{}` | Provider options and model settings, below |
| `candidates` | integer | `5` | Search results the judge may match one citation against |
| `context_window` | integer | | Tokens. `init` takes it from the model catalog. A matching call is split only when it would not fit. |
| `price` | `{input, output}` | | US dollars per million tokens. Leave it out: Casebench looks the price up when a command needs it. Write it for a model no price list has, such as one on your own servers. |
| `provider_source` | string | | The distribution to load when two register the same provider |

The provider options are `api_key_env` (the variable holding the key), `base_url`, `family`, and for some providers `region`, `endpoint` and `api_version`. The model settings are `reasoning_effort`, `thinking_budget`, `temperature`, `max_tokens` and `model_fields`. A setting the provider does not take is refused when the model is built, naming the ones it takes. Which provider takes which is in [Judge providers](/integrations/models/judge-providers/).

## extract

```yaml
extract:
  models:
    - { provider: anthropic, model: claude-sonnet-5-5, options: { max_tokens: 8000 } }
    - { provider: openai, model: gpt-5.5 }
```

Exactly two models, in the same shape as a judge, and not the same provider and model twice.

## capture

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `port` | integer | `0` | The proxy's port. `0` lets the system choose. Name one for an agent that is already running, such as an HTTP target. |
| `traces` | boolean | `false` | Point the OpenTelemetry exporter of agents Casebench starts at its receiver |
| `routes` | list | the parsers' routes | Routes to add, or fields laid over a built-in route of the same name |
| `functions` | list | `[]` | In-process Python functions to record as steps |

### A route

| Key | Default | Meaning |
| --- | --- | --- |
| `name` | required | The path prefix: `http://127.0.0.1:<port>/<name>/...` |
| `upstream` | required | Where requests go on to |
| `parser` | | A model API parser, such as `openai`. Without one, the route is a backend. |
| `env` | | The variable that points a client at the route |
| `env_suffix` | `""` | Added after the route's URL in that variable, such as `/v1` |
| `step` | `retrieval` | For a backend, the kind of step a call records, such as `retrieval`, `rerank`, `tool` or `document` |
| `doc_ids` | | JSONPath to document ids in the response |
| `doc_ids_in` | | JSONPath to document ids in the request, for a rerank |
| `fetch_path` | | Such as `/documents/{id}`: matching requests are recorded as fetches of that id |

The built-in routes are `openai`, `anthropic` and `gemini`, through `OPENAI_BASE_URL`, `ANTHROPIC_BASE_URL` and `GOOGLE_GEMINI_BASE_URL`. When a route's variable already holds a URL, in the shell or a `.env` file `keys:` names, the route forwards to that URL instead of its `upstream`, so a call and its key reach the host the project chose. A Python target needs no route for its model clients: its workers send every call through the proxy to the host the agent chose.

### A function

| Key | Default | Meaning |
| --- | --- | --- |
| `function` | required | `path/file.py:function`, or `package.module:Class.method` |
| `step` | `rerank` | The kind of step it records |
| `name` | the function's | The step's name |
| `doc_ids_in` | | JSONPath over `{"arguments": ..., "result": ...}` |
| `doc_ids_out` | | The same, for the ids it returned |

## agent_models

Each model your agent calls, so a run can warn when a judge is of the same family and price the agent's calls.

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `model` | string | required | The model id, as the agent sends it |
| `family` | string | required | The model catalog's family, such as `claude` or `qwen` |
| `price` | `{input, output}` | | US dollars per million tokens. Left out, it is looked up like a judge's. |

Without `agent_models`, a run says that the family check was not made. A model the agent called that the list leaves out is named in the run's warnings.

## keys

A map from a variable's name to the `.env` file it is read from, relative to `casebench.yaml`. It never holds a value.

```yaml
keys:
  OPENAI_API_KEY: .env
  COURT_API_KEY: research/eval.env
```

When the shell sets the variable, the shell's value is used. Otherwise every command reads that one variable from that file and holds it in Casebench's own memory: it is never set in the environment, so the agent and every other child process start without it. `init` and `corpus add` write these entries, and `--key NAME=FILE` gives one by hand.

## network

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `allow` | list of hosts | `[]` | Hosts a run may call besides loopback and the hosts the config names for the target, judges, extraction models, corpora, capture routes and team server. `*.example.com` allows every host under `example.com`, and not `example.com` itself. |

`run`, `import`, `extract`, `generate`, `check`, `corpus check`, `target check` and the case commands refuse a call to any other host, and a redirect to another host. See [Set the network perimeter](/developers/guides/setup/network/).

## workbench

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `try_daily_limit_usd` | number | none | What trying questions in the workbench may spend each day, in US dollars, the agent's and the judge's calls together. Without it, the workbench sends no question. A team server sets its own limits in place of this one. |
| `second_approval` | boolean | `false` | A change to golden data waits for a second editor's approval |

Trying a question also needs a price for every model under `agent_models`, and for the judge when citations are checked.

## cloud

| Key | Type | Default | Meaning |
| --- | --- | --- | --- |
| `url` | string | required | The team server's address |
| `key_env` | string | `CASEBENCH_CLOUD_KEY` | The variable that holds the engineer's API key, in the shell or a `.env` file `keys:` names |

`casebench init --team-server URL` writes this section. The key is never written. See [Run a team server](/developers/guides/team/team-server/).
