---
title: Command line
description: Every casebench command with its arguments and options, from the commands' own help.
sidebar:
  order: 1
---

Every command reads `casebench.yaml` in the current folder unless `--config` names another file.
`casebench COMMAND --help` prints the same text in a terminal.

```sh
casebench [OPTIONS] COMMAND [ARGS]...
```

Measure the legal accuracy of an AI system against court decisions.

| Option | Description |
| --- | --- |
| `--version` | Show the version and exit. |

## `casebench case`

```sh
casebench case [OPTIONS] COMMAND [ARGS]...
```

Write one case and approve it.

### `casebench case new`

```sh
casebench case new [OPTIONS]
```

Find a decision on a topic, let one model draft the case from it, and approve it; or write it by hand.

| Option | Description |
| --- | --- |
| `--suite DIRECTORY` | The suite folder the case joins; it is created when it does not exist. [required] |
| `--topic TEXT` | What the case is about, in your words. |
| `--pick INTEGER` | Which listed decision, by its number. |
| `--manual` | Write the question and answer by hand. |
| `--author TEXT` | Your name, as the case's reviewer. |
| `--practice-area TEXT` | The area of law, such as labour or tax. |
| `--config FILE` | [default: casebench.yaml] |

### `casebench case resolve`

```sh
casebench case resolve [OPTIONS]
```

Resolve the citations lawyers wrote that no corpus document stood for yet.

| Option | Description |
| --- | --- |
| `--suite DIRECTORY` | The suite folder the case joins; it is created when it does not exist. [required] |
| `--config FILE` | [default: casebench.yaml] |

## `casebench check`

```sh
casebench check [OPTIONS]
```

Check the corpus, the target and the judge from here; fail if any does not pass.

| Option | Description |
| --- | --- |
| `--config FILE` | [default: casebench.yaml] |
| `--query TEXT` | A search that finds documents, for a store that cannot list them; the corpus's own probe search is run when none is given. |
| `--size INTEGER RANGE` | Search results to take and documents to fetch; `casebench corpus check` samples more. [default: 1; x>=1] |
| `--json` | Each part's status, reason and next step as JSON, for a script or a coding agent. |

## `casebench compare`

```sh
casebench compare [OPTIONS] FIRST SECOND
```

Each metric before and after, with the interval of the difference, and every setting the two score sets were produced with differently. Given two keys folders, their extractions side by side: settings, agreement, time and cost.

## `casebench corpus`

```sh
casebench corpus [OPTIONS] COMMAND [ARGS]...
```

The documents citations are checked against.

### `casebench corpus add`

```sh
casebench corpus add [OPTIONS] COMMAND [ARGS]...
```

Add the document store citations are checked against.

#### `casebench corpus add http`

```sh
casebench corpus add http [OPTIONS]
```

A document API reached over HTTP.

| Option | Description |
| --- | --- |
| `--base-url TEXT` | The API's root URL, such as https://api.example.com/v1, or a variable that holds it, such as '$\{DOCS_URL\}'. |
| `--search-path TEXT` | Such as /search. |
| `--query-param TEXT` | [default: q] |
| `--search-body TEXT` | For an API that searches by POST: its JSON body, with \{text\} where the words go, such as '\{"query": "\{text\}", "limit": "\{limit\}"\}'. |
| `--fetch-path TEXT` | With \{id\}, such as /documents/\{id\}. |
| `--key-env TEXT` | The environment variable that holds the API key. |
| `--key-header TEXT` | The header that carries the key; Authorization sends it as a bearer token. [default: Authorization] |
| `--header TEXT` | NAME=VALUE; $\{VAR\} reads the environment, such as Authorization=Bearer $\{KEY\}. |
| `--key NAME=FILE` | The .env file a key is read from, relative to the config; found by name if not. |
| `--config FILE` | [default: casebench.yaml] |
| `--probe TEXT` | A search that finds at least one document. |
| `--ids TEXT` | JSONPath to the ids in a search result. |
| `--field TEXT` | NAME=JSONPath, such as text=$.body. |
| `--results TEXT` | JSONPath to each result in a search response. |
| `--result-field TEXT` | NAME=JSONPath inside one result, for id, citation, type or passage. |
| `--jurisdiction TEXT` | A jurisdiction the store covers, such as NO or US-CA; give it once for each. |
| `--name TEXT` | The corpus's name in casebench.yaml, such as frontier-legal; made from the store if not. |
| `--yes` | Ask nothing: take the flags and suggestions. |

#### `casebench corpus add mcp`

```sh
casebench corpus add mcp [OPTIONS]
```

An MCP server with a search tool and a fetch tool.

| Option | Description |
| --- | --- |
| `--command TEXT` | Start the server over stdio. |
| `--url TEXT` | Reach the server over Streamable HTTP. |
| `--search-tool TEXT` |  |
| `--search-arg TEXT` | [default: query] |
| `--fetch-tool TEXT` |  |
| `--fetch-arg TEXT` | [default: id] |
| `--config FILE` | [default: casebench.yaml] |
| `--probe TEXT` | A search that finds at least one document. |
| `--ids TEXT` | JSONPath to the ids in a search result. |
| `--field TEXT` | NAME=JSONPath, such as text=$.body. |
| `--results TEXT` | JSONPath to each result in a search response. |
| `--result-field TEXT` | NAME=JSONPath inside one result, for id, citation, type or passage. |
| `--jurisdiction TEXT` | A jurisdiction the store covers, such as NO or US-CA; give it once for each. |
| `--name TEXT` | The corpus's name in casebench.yaml, such as frontier-legal; made from the store if not. |
| `--yes` | Ask nothing: take the flags and suggestions. |

#### `casebench corpus add profile`

```sh
casebench corpus add profile [OPTIONS] FILE_OR_ID
```

A store described by a provider's profile: a file, or a bundled profile's id. Nothing is asked; one live search and fetch prove it works with your key.

| Option | Description |
| --- | --- |
| `--config FILE` | [default: casebench.yaml] |
| `--jurisdiction TEXT` | Cover only these jurisdictions, instead of the profile's. |
| `--name TEXT` | The corpus's name in casebench.yaml; the profile's id if not. |

### `casebench corpus cache`

```sh
casebench corpus cache [OPTIONS] COMMAND [ARGS]...
```

The local copy of fetched documents.

#### `casebench corpus cache clear`

```sh
casebench corpus cache clear [OPTIONS]
```

Delete every cached document.

### `casebench corpus check`

```sh
casebench corpus check [OPTIONS]
```

Fetch a sample by id and report which required fields are present or missing.

| Option | Description |
| --- | --- |
| `--config FILE` | [default: casebench.yaml] |
| `--query TEXT` | A search that finds documents, for a store that cannot list them; the corpus's probe search when none is given. |
| `--size INTEGER RANGE` | [default: 200; x>=1] |
| `--corpus TEXT` | Which corpus, when the config names several. |

### `casebench corpus probe`

```sh
casebench corpus probe [OPTIONS] COMMAND [ARGS]...
```

Show what a document store answers, so its fields can be mapped by flags (0044).

#### `casebench corpus probe http`

```sh
casebench corpus probe http [OPTIONS]
```

One search, one fetch, or both, printed as JSON with the key used by name and never shown. Map the fields with `casebench corpus add http` and its field flags after.

| Option | Description |
| --- | --- |
| `--base-url TEXT` | The API's root URL, or a variable that holds it, such as '$\{DOCS_URL\}'. [required] |
| `--search-path TEXT` | [default: /search] |
| `--query-param TEXT` | [default: q] |
| `--fetch-path TEXT` | [default: /documents/\{id\}] |
| `--key-env TEXT` | The variable that holds the API key, found by name. |
| `--key-header TEXT` | [default: Authorization] |
| `--header TEXT` | NAME=VALUE; $\{VAR\} names a key. |
| `--key NAME=FILE` |  |
| `--query TEXT` | Search for this and print the response. |
| `--fetch TEXT` | Fetch this document and print it. |
| `--config FILE` | Its folder is the project whose .env files hold the key. [default: casebench.yaml] |

## `casebench demo`

```sh
casebench demo [OPTIONS]
```

Run a bundled suite with no key and no data, and open the workbench. Like every run, it reads two public price lists; nothing of yours is sent, and no model is asked.

| Option | Description |
| --- | --- |
| `--dir DIRECTORY` | Where to keep the demo; a new temporary folder when not given. |
| `--no-serve` | Stop after the run; do not open the workbench. |
| `--port INTEGER RANGE` | [default: 7462; 1024\<=x\<=65535] |

## `casebench export`

```sh
casebench export [OPTIONS]
```

Write a run's criteria to a spreadsheet lawyers review with no server and no login, or a suite's questions as CSV for a tool Casebench cannot reach.

| Option | Description |
| --- | --- |
| `--review DIRECTORY` | The run whose answers lawyers review in the spreadsheet. |
| `--suite DIRECTORY` | With --format csv: the suite whose questions a closed tool answers (decision 0061). |
| `--format [csv]` | With --suite: csv. |
| `--out FILE` |  |
| `--all` | Also the criteria already reviewed. |
| `--suites DIRECTORY` | Where to look for the run's suite; the current folder by default. |
| `--config FILE` | Its corpora's link: settings link each court fact to its decision. [default: casebench.yaml] |

## `casebench extract`

```sh
casebench extract [OPTIONS]
```

Two different models read each decision; only the fields they agree on become keys.

| Option | Description |
| --- | --- |
| `--sample INTEGER RANGE` | How many decisions to read. [x>=1; required] |
| `--config FILE` | [default: casebench.yaml] |
| `--query TEXT` | A search that finds decisions, for a store that cannot list them. |
| `--out DIRECTORY` | [default: .casebench/keys] |
| `--max-concurrency INTEGER RANGE` | [default: 1; x>=1] |
| `--corpus TEXT` | Which corpus, when the config names several. |
| `--set NAME=VALUE` | A model setting for both models in this run, such as reasoning_effort=low. |
| `--dry-run` | Say what it would cost; send nothing. |

## `casebench gate`

```sh
casebench gate [OPTIONS] BASELINE RUN
```

Compare a run with a saved baseline of the same suite. Exits 1 when a metric falls significantly, 2 when the two runs were measured differently, 0 otherwise.

| Option | Description |
| --- | --- |
| `--include-unreviewed` | Gate cases no lawyer has approved yet too, such as court-derived ones. |
| `--markdown FILE` | Write the pull request comment here. |

## `casebench generate`

```sh
casebench generate [OPTIONS]
```

Turn answer keys into cases and freeze them as a suite.

| Option | Description |
| --- | --- |
| `--keys DIRECTORY` | [default: .casebench/keys] |
| `--types TEXT` | Comma-separated case types. [default: outcome,statute,precedent] |
| `--n INTEGER RANGE` | How many cases, from every corpus. [x>=1] |
| `--corpus NAME=COUNT` | How many cases from one corpus; give it once for each corpus the suite mixes. |
| `--after [%Y-%m-%d]` | Only decisions dated after this day, such as a model's training cutoff. |
| `--stratify [court]` | Balance across court levels. |
| `--suite-id TEXT` | The suite's name; it also seeds its order. [required] |
| `--out DIRECTORY` | [required] |
| `--config FILE` | [default: casebench.yaml] |

## `casebench guide`

```sh
casebench guide [OPTIONS]
```

Print the steps a coding agent follows to set Casebench up in a project, changing nothing but casebench.yaml and .casebench/ (decision 0044). Paste into the coding agent: "Set up Casebench for this project: run `casebench guide` and follow it".

## `casebench import`

```sh
casebench import [OPTIONS] PATH
```

Add a spreadsheet's rows to a suite as cases approved by the lawyer who wrote them, or read a review sheet's verdicts back into its run (decisions 0049, 0055).

| Option | Description |
| --- | --- |
| `--suite DIRECTORY` | The suite folder cases join; it is created when it does not exist. |
| `--by TEXT` | The lawyer who wrote the cases, or who reviewed the rows naming no reviewer. |
| `--task [drafting\|editing\|extraction\|outcome\|qa\|research]` | The task of a CSV's rows. |
| `--runs-dir DIRECTORY` | Where the run a review sheet reviews is; .casebench/runs by default. |
| `--database TEXT` | The workbench's database, whose event log keeps verdicts. |
| `--config FILE` | [default: casebench.yaml] |

## `casebench init`

```sh
casebench init [OPTIONS]
```

Set Casebench up for the agent in this folder, or bring an existing setup up to date.

| Option | Description |
| --- | --- |
| `--config FILE` | [default: casebench.yaml] |
| `--target [python\|command\|http]` |  |
| `--entry TEXT` | A Python target's function, as path.py:function. |
| `--run TEXT` | A command target's command line. |
| `--url TEXT` | An HTTP target's endpoint. |
| `--corpus [folder\|http\|mcp\|none]` |  |
| `--corpus-path TEXT` | A folder corpus's path. |
| `--profile FILE_OR_ID` | A data provider's profile, a file or a bundled id; give it once for each provider. |
| `--judge-provider TEXT` | The judge's provider, as the model catalog names it. |
| `--judge-model TEXT` |  |
| `--judge-option TEXT` | NAME=VALUE, over the catalog's. |
| `--no-judge` | Set no judge; outcome suites need none. |
| `--extract PROVIDER MODEL` | An extraction model; give it twice, for two different models. |
| `--no-extract` | Set no extraction models. |
| `--catalog FILE` | A saved copy of the model catalog, instead of fetching it. |
| `--no-live` | Only the checks that need no network. |
| `--routes / --no-routes` | Write a capture route for every client found, or for none, without asking. |
| `--custom / --quick` | Choose every part, or take what was found and ask only what is missing. |
| `--key NAME=FILE` | The .env file a key is read from, relative to the config; give it once for each. |
| `--team-server URL` | The team server lawyers review on; its key is read from CASEBENCH_CLOUD_KEY. |
| `--yes` | Write casebench.yaml without asking after the review. |
| `--details` | List everything the code scan found. |
| `--ui / --no-ui` | Open the workbench when done; the default at a terminal, never without one. |

## `casebench invite`

```sh
casebench invite [OPTIONS] EMAIL
```

Invite a person to the team server by email, with a role.

| Option | Description |
| --- | --- |
| `--role [viewer\|reviewer\|editor\|engineer\|admin]` | [default: reviewer] |
| `--name TEXT` | How the person is shown; the email's name when not given. |
| `--config FILE` | [default: casebench.yaml] |

## `casebench keys`

```sh
casebench keys [OPTIONS] NAMES...
```

Where each named variable is kept: the shell, and the project's .env files that give it a value. No value is printed; files that disagree show different fingerprints.

| Option | Description |
| --- | --- |
| `--root DIRECTORY` | The project's folder, whose .env files are read. [default: .] |
| `--json` | The same as JSON. |

## `casebench models`

```sh
casebench models [OPTIONS] [PROVIDER_ID]
```

The providers in the public model catalog, or one provider's models, with the ids `casebench init --judge-provider ID --judge-model ID` takes (decision 0044).

| Option | Description |
| --- | --- |
| `--json` | The same as JSON. |
| `--catalog FILE` | A saved copy of the model catalog, instead of fetching it. |

## `casebench plugin`

```sh
casebench plugin [OPTIONS] COMMAND [ARGS]...
```

Add a data provider, a model provider, a capture parser or any other plugin.

### `casebench plugin kinds`

```sh
casebench plugin kinds [OPTIONS]
```

Every plugin kind: its entry-point group, its interface and its conformance command.

### `casebench plugin new`

```sh
casebench plugin new [OPTIONS] {connector|exporter|metric|parser|provider|reference|target|task}
```

Write a plugin skeleton with stubs, a conformance test and a samples folder.

| Option | Description |
| --- | --- |
| `--name TEXT` | Lowercase name, such as a provider's. [required] |
| `--built-in` | Write a folder inside the core instead. |
| `--root DIRECTORY` | Where to write: the parent folder of the package, or the core's root. [default: .] |

### `casebench plugin test`

```sh
casebench plugin test [OPTIONS] PATH
```

Run the plugin's conformance suite on its own samples.

## `casebench proxy`

```sh
casebench proxy [OPTIONS] COMMAND [ARGS]...
```

The recording proxy that captures model and backend calls.

### `casebench proxy env`

```sh
casebench proxy env [OPTIONS]
```

Print the lines to set in the agent's environment.

| Option | Description |
| --- | --- |
| `--config FILE` | [default: casebench.yaml] |

## `casebench pull`

```sh
casebench pull [OPTIONS]
```

Bring back what lawyers decided on the team server: approved cases into their suites, and verdicts and preferences into their runs.

| Option | Description |
| --- | --- |
| `--runs-dir DIRECTORY` | [default: .casebench/runs] |
| `--suites DIRECTORY` | Where to look for suites; the current folder when none is given. |
| `--config FILE` | [default: casebench.yaml] |

## `casebench push`

```sh
casebench push [OPTIONS] [RUN_IDS]...
```

Send runs and the suites they ran to the team server; every run when none is named. The agent, the corpus, full decision texts, the judge's replies and keys stay here.

| Option | Description |
| --- | --- |
| `--runs-dir DIRECTORY` | [default: .casebench/runs] |
| `--suites DIRECTORY` | Where to look for suites; the current folder when none is given. |
| `--traces` | Also send each answer's steps, as ids and numbers only, never their content. |
| `--config FILE` | [default: casebench.yaml] |

## `casebench report`

```sh
casebench report [OPTIONS] RUN_DIR
```

Print a scored run's report again, or export it for partners.

| Option | Description |
| --- | --- |
| `--export FILE` | Write the report for partners to this .html, .pdf or .docx file. |
| `--suites DIRECTORY` | Where to look for the run's suite when exporting; the current folder by default. |

## `casebench review`

```sh
casebench review [OPTIONS] COMMAND [ARGS]...
```

Record a lawyer's verdict beside the judge's.

### `casebench review criterion`

```sh
casebench review criterion [OPTIONS] RUN_DIR
```

Give a lawyer's verdict on one criterion of a scored run. It is counted against the judge's in the run's report; the scores stay the judge's.

| Option | Description |
| --- | --- |
| `--case TEXT` | The case's id. [required] |
| `--criterion TEXT` | The criterion's id. [required] |
| `--repeat INTEGER RANGE` | [default: 0; x>=0] |
| `--verdict [pass\|fail]` | Whether the answer passes this criterion, in the lawyer's view. [required] |
| `--by TEXT` | Who gives the verdict. [required] |
| `--note TEXT` | Why; required when the verdict overrules the judge's. |

## `casebench run`

```sh
casebench run [OPTIONS]
```

Send every case of a frozen suite to the target, store each result and score the run. With no --suite, the first run builds one from the corpus, and a later run resumes it.

| Option | Description |
| --- | --- |
| `--suite DIRECTORY` | The frozen suite; without it, .casebench/suites/first, built on the first run (decision 0061). |
| `--config FILE` | [default: casebench.yaml] |
| `--python AGENT.PY[:FUNCTION]` | Run a Python agent in worker processes, with the config's folder first on its import path; FUNCTION defaults to answer. |
| `--max-concurrency INTEGER RANGE` | Cases at once; overrides the target's setting. [x>=1] |
| `--run-id TEXT` | Name the run; an existing run of that name resumes. |
| `--runs-dir DIRECTORY` | [default: .casebench/runs] |
| `--no-capture` | Do not start the recording proxy. |
| `--dry-run` | Count what the run would send; send nothing. |
| `--commit TEXT` | The commit the agent's code is at; else GITHUB_SHA, else the folder's checkout. |
| `--sample INTEGER RANGE` | With no suite yet: how many decisions the first run reads. [default: 20; x>=1] |
| `--cases INTEGER RANGE` | With no suite yet: how many cases the first run makes. [default: 10; x>=1] |
| `--yes` | With no suite yet: build it without asking. |

## `casebench schema`

```sh
casebench schema [OPTIONS] COMMAND [ARGS]...
```

The JSON Schemas of Casebench's formats.

### `casebench schema export`

```sh
casebench schema export [OPTIONS]
```

Write every format's schema at its current version, one file per version.

| Option | Description |
| --- | --- |
| `--into DIRECTORY` | The folder to write into; one subfolder per format. [default: (the schemas shipped with Casebench)] |

## `casebench target`

```sh
casebench target [OPTIONS] COMMAND [ARGS]...
```

Connect and check the AI under test.

### `casebench target check`

```sh
casebench target check [OPTIONS]
```

Send one sample case and show the parsed answer, citations and captured steps.

| Option | Description |
| --- | --- |
| `--config FILE` | [default: casebench.yaml] |
| `--question TEXT` | What to ask; "Hi. How are you?" when not given. |

## `casebench template`

```sh
casebench template [OPTIONS] COMMAND [ARGS]...
```

Write a file for someone to fill in.

### `casebench template lawyer`

```sh
casebench template lawyer [OPTIONS]
```

A spreadsheet a lawyer fills with one case per row: XLSX, or CSV when --out ends in .csv.

| Option | Description |
| --- | --- |
| `--task [drafting\|editing\|extraction\|outcome\|qa\|research]` | [default: qa] |
| `--out FILE` |  |

## `casebench ui`

```sh
casebench ui [OPTIONS]
```

Open the review queue: answers to review and court drafts to approve.

| Option | Description |
| --- | --- |
| `--runs-dir DIRECTORY` | [default: .casebench/runs] |
| `--suites DIRECTORY` | Where to look for suites; the current folder when none is given. |
| `--config FILE` | Its corpus shows each passage in its decision. [default: casebench.yaml] |
| `--database TEXT` | A database URL; SQLite under .casebench/ when not given. |
| `--port INTEGER RANGE` | [default: 7462; 1024\<=x\<=65535] |
| `--role [reviewer\|engineer]` | reviewer serves the review view only, with no way to show engineering detail. |
| `--no-open` | Do not open the browser. |

## `casebench validate`

```sh
casebench validate [OPTIONS] PATH
```

Check a file against its format: the schema, and the rules a schema cannot hold.

| Option | Description |
| --- | --- |
| `--format TEXT` | The file's format, such as casebench.document/1.0. |
