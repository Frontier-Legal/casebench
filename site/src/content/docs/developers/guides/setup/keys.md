---
title: Keep keys out of the config
description: Where Casebench reads the keys it calls services with, from the shell or a project's .env files, and how it keeps them out of child processes, output and run files.
sidebar:
  order: 3
---

Casebench calls a few services itself: the judge, the extraction models, the document store and, if you have one, the team server. Each needs a key. `casebench.yaml` never holds one. It names the variable a key is in, and, when the key lives in a `.env` file, which file.

Your agent's own keys are not Casebench's business. The agent loads its settings the way production does, in its own code or in the [adapter](/developers/guides/connect/python-agent/#load-the-agents-settings-in-an-adapter).

## Where Casebench reads a key

For every variable the config names, Casebench reads the shell first. When the shell does not set it, Casebench reads it from the file `keys:` names for it:

```yaml title="casebench.yaml"
judge:
  provider: openai
  model: gpt-5.5
  options:
    api_key_env: OPENAI_API_KEY
    family: gpt
keys:
  OPENAI_API_KEY: .env
  DOCS_API_KEY: research/.env
```

A path under `keys:` is relative to the folder that holds `casebench.yaml`. Every command reads exactly these variables from these files, and only when the shell does not set them. A file is read for that one name; Casebench keeps no other value from it.

These are the places a config names a variable:

| Setting | Example |
| --- | --- |
| A judge's or extraction model's key | `options: { api_key_env: OPENAI_API_KEY }` |
| A header of an HTTP corpus, an MCP corpus or an HTTP target | `Authorization: Bearer ${DOCS_API_KEY}` |
| An address: an HTTP corpus's `base_url`, the `url` of an HTTP target, an MCP corpus or the team server, a capture route's `upstream` | `base_url: ${DOCS_URL}` |
| The team server's key | `cloud: { key_env: CASEBENCH_CLOUD_KEY }`, the default |

A `${NAME}` that neither the shell nor a `keys:` file sets is an error that names the variable.

## Which files count as .env files

When `casebench init`, `casebench keys` or `corpus add` look for a variable, they read the project's `.env` files:

- files named `.env`, `.env.<anything>` or `<anything>.env`, such as `env/eval.env`;
- not a file of placeholders, whose name ends in `.example`, `.sample`, `.template` or `.dist`;
- not inside a hidden folder, `node_modules`, `__pycache__`, `site-packages` or a virtual environment, which is any folder holding `pyvenv.cfg`.

Files nearer the project's root come first. In a file, each `NAME=value` line counts. An `export ` prefix and surrounding quotes are taken off, and a value given twice keeps the last one.

The search skips hidden folders, but `keys:` may still name a file in one. The workbench uses `.casebench/.env` for a key you type into its Settings page when the file `keys:` names is not ignored by git. See [Set up in the workbench](/developers/guides/setup/workbench/).

## Find where a key is kept

`casebench keys` names the shell and each `.env` file that gives a variable a value. It prints no value, not even part of one. Files that disagree show different fingerprints, the first 8 hex characters of the value's SHA-256:

```sh
casebench keys ANTHROPIC_API_KEY
```

```text frame="terminal"
ANTHROPIC_API_KEY: not set in this shell
  .env  (fingerprint 3b18bc4f)
  research/.env  (fingerprint fcf12ace)
  the values differ; pass --key ANTHROPIC_API_KEY=FILE to say which is used
```

`--json` gives the same for a script or a coding agent:

```json
[
  {
    "name": "ANTHROPIC_API_KEY",
    "in_shell": false,
    "files": [
      { "file": ".env", "fingerprint": "3b18bc4f" },
      { "file": "research/.env", "fingerprint": "fcf12ace" }
    ],
    "values_agree": false
  }
]
```

`--root DIR` reads another project's folder.

## Say which file a key comes from

`casebench init`, `casebench corpus add http` and `casebench corpus probe http` take `--key NAME=FILE`. It names the file and records the pair under `keys:`, so a script never exports a key's value:

```sh
casebench corpus add http --base-url '${DOCS_URL}' --search-path /search \
  --fetch-path "/documents/{id}" --key-env DOCS_API_KEY \
  --key DOCS_API_KEY=research/.env --key DOCS_URL=research/.env ...
```

```text frame="terminal"
key DOCS_API_KEY: read from research/.env, by name; its value is not written
key DOCS_URL: read from research/.env, by name; its value is not written
```

Without `--key`, a command finds the name itself. One file holding it is used, and the command says which. When several files hold different values, a terminal shows a numbered list with fingerprints. Without a terminal, the command stops and names the flag:

```text frame="terminal"
Error: ANTHROPIC_API_KEY has different values in these files; which one: nothing here can answer it; give it with --key ANTHROPIC_API_KEY=FILE
```

A name already under `keys:` keeps its file. To point it at another file, edit the line in `casebench.yaml`.

## What Casebench does with a key

- Casebench keeps a key from a file in its own memory. It never sets it in the environment, so your agent, a command target, a `start` command and every other child process start without it. A key your shell sets is the shell's, and child processes inherit it as they always do. An MCP server that Casebench starts over stdio gets the MCP library's minimal default environment.
- A key goes only to its service. A model key goes only in the request to its provider's configured address. A corpus key goes only in the headers configured for that corpus. The [perimeter](/developers/guides/setup/network/) holds every call to the hosts the config names.
- No command prints a key's value. When a provider's error repeats the request, the key is replaced by `${NAME}` before the message is shown or written.
- No command writes a key into the config. `corpus add` refuses a literal value in `Authorization` or `Proxy-Authorization`, the headers that carry credentials:

  ```text frame="terminal"
  Error: Invalid value: Authorization would write a key into casebench.yaml; give it as ${NAME}, such as 'Authorization=Bearer ${DOC_KEY}', or pass --key-env NAME
  ```

  A literal value in another header, such as `--header x-api-key=...`, is written as given, because nothing tells a key from a plain value there. Use `--key-env NAME` with `--key-header x-api-key` for such a key.

## Keys never reach a run's files

Casebench scrubs every line of `run.json`, `results.jsonl`, each score set and `report.json` before it writes it:

- the value of each key read from a `.env` file, and of each variable a header or a provider's `api_key_env` names, becomes `${NAME}`;
- a credential the call carried in an `Authorization`, `Proxy-Authorization`, `x-api-key`, `api-key` or `x-goog-api-key` header, sent by Casebench or forwarded by the recording proxy, becomes `[credential]`. Values shorter than 8 characters are left alone, so ordinary text is not rewritten.

Recorded calls hold no request headers at all. In a recorded URL, the value of each query parameter whose name contains `key`, `token`, `secret`, `signature` or `password` becomes `REDACTED`.

## Related

- [Allow the hosts your agent calls](/developers/guides/setup/network/).
- [The perimeter](/developers/concepts/perimeter/), and why it exists.
- [Set up with a coding agent](/developers/guides/setup/coding-agent/), which locates keys with `casebench keys`.
