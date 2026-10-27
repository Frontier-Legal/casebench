---
title: MCP server
description: Connect a document store served over the Model Context Protocol, over stdio or Streamable HTTP, through its search and fetch tools.
sidebar:
  order: 2
---

The `mcp` connector reaches a server with a search tool and a fetch tool, through the official `mcp` Python SDK. It starts the server over stdio, or reaches one over Streamable HTTP.

## Add it

Over stdio, Casebench starts the server itself:

```sh
casebench corpus add mcp --command "python -m court_search.mcp" \
  --search-tool search_decisions --fetch-tool get_decision --probe "notice period"
```

Over HTTP:

```sh
casebench corpus add mcp --url https://mcp.example.com/mcp \
  --search-tool search --fetch-tool fetch --probe "notice period"
```

`corpus add mcp` first lists the server's tools with their descriptions. It then calls the search tool with the probe, shows what came back, and asks where each result keeps its id, citation, type and passage. It fetches the first result and asks which field is the document's id, jurisdiction, court, date, text and level, suggesting the id, text and date from their values, as for [HTTP stores](/integrations/stores/http-api/). `--search-arg` and `--fetch-arg` name the tools' arguments, `query` and `id` by default.

The workbench's Jurisdictions page adds an MCP server the same way: give the command or the URL, pick the two tools, then pick each field from the values the server returned.

## The block it writes

```yaml title="casebench.yaml"
corpora:
  mcp-example-com:
    connector: mcp
    jurisdictions: ["NO"]
    options:
      url: https://mcp.example.com/mcp
      search_tool: search
      search_arguments: { query: "{text}" }
      fetch_tool: fetch
      fetch_arguments: { id: "{id}" }
      search_ids: $.results[*].id
      fields:
        id: $.id
        jurisdiction: $.country
        court: $.court
        date: $.date
        text: $.text
    probe: notice period
```

For a server started over stdio, `options` holds `command` as a list instead of `url`, such as `command: [python, -m, court_search.mcp]`.

An argument whose whole value is `{text}`, `{limit}` or `{id}` is filled per call, so you can add `limit: "{limit}"` to `search_arguments` by hand. Every option is in the [configuration reference](/developers/reference/configuration/#mcp-options).

## What a tool returns

Casebench reads a tool's structured content, or else the JSON in its first text block. A tool that returns a string has it wrapped as `{"result": "..."}`, and the string is read as JSON when it is JSON. The JSONPath expressions apply to what is read.

## Headers and keys

Over HTTP, `headers` are sent on every request, with `${NAME}` read from the shell or a `.env` file `keys:` names:

```yaml
    options:
      url: https://mcp.example.com/mcp
      headers:
        Authorization: Bearer ${COURT_MCP_KEY}
```

`corpus add mcp` and the workbench take no headers, so a server that refuses a call without one has to be written by hand: add the block with its `headers`, then run `casebench check`. A server started over stdio gets the MCP library's minimal default environment, not your shell's, so it does not see your keys. A server needing OAuth needs a connector plugin for now.

## Related

- [Connect a document store](/developers/guides/connect/document-store/).
- [Configuration reference: MCP options](/developers/reference/configuration/#mcp-options).
