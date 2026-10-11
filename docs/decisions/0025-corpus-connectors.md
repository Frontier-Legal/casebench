---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# Corpus connectors fetch, search and are cached; any store is configured, not coded

## Context and problem statement

Citation checks resolve every citation an answer makes to a document in the corpus ([0024](0024-no-jurisdiction-adapters.md)), and case generation samples decisions from it. Teams keep decisions in a folder, a bucket, a database, a licensed API or an MCP server. A paid API charges per call, so a decision fetched once must never be fetched again. A tool must never confirm its own citations.

## Considered options

- One connector contract (fetch by id, search by text, optional listing), a local cache in front of every connector, generic HTTP and MCP connectors configured by JSONPath and written by a command
- A connector written per provider
- Copying the whole corpus locally before a run

## Decision outcome

Chosen option: "one contract, a cache, generic HTTP and MCP connectors".

- **Contract.** `fetch(id)` returns one document as a mapping; `search(text, limit)` returns ids, best first; `list_ids()` is optional, because many APIs cannot enumerate their store. A connector holds no legal logic.
- **Cache.** Every fetched document is written to `./.casebench/corpus-cache/<corpus key>/` and read from there afterwards, so a document costs one call ever. `casebench corpus cache clear` empties it. Searches are not cached; a citation is resolved once per run and its result stored in the run log.
- **HTTP.** A connector of type `http` names a base URL, headers (with `${VAR}` from the environment), a fetch path, a search path with its query parameters, and JSONPath expressions for the ids in a search result and for each decision-record field in a document. A field the expressions cannot find is reported by name.
- **No provider presets.** The core ships no connector for any particular provider. `casebench corpus add http` or `casebench corpus add mcp` asks for the store's address and key variable, makes one live search and one fetch, shows the JSON that came back with suggested JSONPath expressions for the id, text, court and date, and writes the corpus block into casebench.yaml once the user confirms; every answer can be a flag instead. It appends the block to an existing file and never rewrites one that already has a corpus. A provider may publish its own connector plugin.
- **MCP.** A connector of type `mcp` starts an MCP server over stdio, or reaches one over HTTP, through the official `mcp` SDK, and names its search and fetch tools, their arguments and the JSONPath to the ids and fields in their results.
- **Corpus check.** `casebench corpus check` samples 200 documents, the size the corpus-check scenario sets: by listing when the connector can, otherwise through searches the user names. It reports each required field present or missing and copies nothing outside the cache.
- **The system under test cannot verify itself.** A config whose corpus URL is the target's URL is refused, with the reason. A corpus that is the same document source the agent retrieves from is allowed.
- **S3** is left for when a user needs it; it brings `boto3` as an extra.

### Consequences

- Good, because a new provider is a config block the command writes, not code, and the core favours no provider.
- Good, because repeated runs against a paid API cost nothing after the first fetch of each document.
- Bad, because resolving a citation depends on the provider's search; a store without search, such as a plain folder at scale, resolves poorly, and the report counts unresolved citations.

## Revisit when

A provider's search cannot resolve citations reliably enough, or a team needs S3 or SQL.

## More information

- [Model Context Protocol Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [jsonpath-ng](https://github.com/jsonpath-ng/jsonpath-ng)
