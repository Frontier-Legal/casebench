---
title: Connect several corpora
description: Check citations across jurisdictions by connecting one named corpus per store, each with the jurisdictions it covers.
sidebar:
  order: 5
---

An agent that answers across countries cites authorities from more than one store. Connect each store as its own named corpus and say which jurisdictions it covers. Casebench then searches for each citation only where it can be found.

## Add each store under a name

Each `corpus add` adds one more corpus under its `--name`, and refuses a name the config already has:

```sh
casebench corpus add profile no-provider.yaml --name no-courts --jurisdiction NO
casebench corpus add mcp --url https://mcp.example.com/mcp --name tr-courts --jurisdiction TR \
  --search-tool search --fetch-tool fetch --probe "işe iade"
```

`init` asks "Connect another source?" after each one, until you answer that you are done. The config then holds `corpora:` instead of `corpus:`:

```yaml title="casebench.yaml"
corpora:
  no-courts:
    connector: http
    jurisdictions: ["NO"]
    profile: no-provider.yaml
    options: { ... }
  tr-courts:
    connector: mcp
    jurisdictions: [TR]
    holds: [decisions]
    options: { ... }
```

A name is lower-case letters, digits and hyphens. A corpus that lists no jurisdictions covers all of them, and one without `holds` holds both decisions and statutes. A `base_url` may be a variable, such as `${NO_COURTS_URL}`, read as a key is.

## Jurisdiction codes

Every jurisdiction is one code:

- ISO 3166-1 alpha-2 for a country: `NO`, `TR`, `GB`.
- ISO 3166-2 for a part of one with its own law: `US-CA`, `DE-BY`.
- `EU` for the European Union's own law and courts.

`UK` and `EL`, used by the European Case Law Identifier, are read as `GB` and `GR`. Any other code is refused with the code Casebench expected.

## How a citation finds its corpus

When the judge lists an answer's citations, it also names the jurisdiction each one belongs to and whether it cites a decision or a statute.

1. The citation is searched in the corpora that cover its jurisdiction and hold its kind of document.
2. If the judge cannot tell the jurisdiction, it is searched in the corpora covering the case's jurisdiction.
3. If the case has none, every corpus is searched.

Candidates from several corpora reach the judge together, each marked with its corpus. The report says how many citations were routed each way.

A citation whose jurisdiction no connected corpus covers is labelled `unchecked`. It is counted apart and never counts against the answer. `fabricated` keeps its meaning: a corpus that covers the jurisdiction was searched and holds no such document.

## Ids carry their corpus

Every document id Casebench stores is written `<corpus name>:<id as the provider gives it>`, such as `tr-courts:2024-1234`. The provider only ever receives the part after the first colon.

## Build a suite that mixes jurisdictions

A document API or an MCP server cannot list its documents, so sample each through a search with `--query`. Then name the share each corpus contributes:

```sh
casebench extract --sample 80 --corpus tr-courts --query "işe iade" --out .casebench/keys
casebench extract --sample 80 --corpus no-courts --query "oppsigelse" --out .casebench/keys
casebench generate --suite-id labour-mixed --out suites/labour-mixed \
  --corpus tr-courts=30 --corpus no-courts=30
```

Extracting from a second corpus into the same folder keeps the first one's keys; extracting from the same corpus again replaces only its own. Each case records the corpus its decision came from, the manifest counts cases per corpus and per jurisdiction, and every report table splits by jurisdiction. Jurisdictions are never averaged together.

## Commands that need a name

With more than one corpus, `corpus check` and `extract` take `--corpus NAME`. Without it they stop and list the names that exist:

```text frame="terminal"
Error: name the corpus with --corpus; the config has: no-courts, tr-courts
```

`casebench check` checks every corpus, one part each, named `corpus no-courts`, `corpus tr-courts`. A first `casebench run` with no suite builds it from the first corpus the config names; `extract` and `generate`, as above, build one that mixes them.

During a run, each corpus with the `http` connector gets its own capture route, so a Python agent's searches of either store are [recorded as retrievals](/developers/guides/capture/retrieval-steps/#searches-of-your-corpus).

## Related

- [A suite across two jurisdictions](/examples/walkthroughs/mixed-jurisdictions/), end to end.
- [Citation labels](/developers/reference/labels/) for `unchecked`, `fabricated` and the rest.
