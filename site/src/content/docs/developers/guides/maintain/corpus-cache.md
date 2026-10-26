---
title: Manage the corpus cache
description: How fetched documents and paid searches are kept on disk, how a provider's terms limit that, and how to clear it.
sidebar:
  order: 2
---

Every document Casebench fetches is written under `.casebench/corpus-cache/<corpus key>/` and read from there afterwards. A document costs one call, ever. Citation checks, re-scoring, extraction, suite generation and `corpus check` all read the same cache.

## The corpus key

Each corpus has its own folder, named by a key made from its connector and the options that decide what a fetched document holds. Change the base URL or the field paths and you get a fresh cache. Options that only describe search results, `search_results` and `result_fields`, are left out of the key, so adding them keeps every document already cached. A search kept before they were added lists ids alone and is still read; its candidates are described from the stored documents.

## Searches from metered providers

A provider that charges per search sets `metered: search` in its profile, and the corpus block carries it. Each search it answers is kept under `searches/`, keyed by the search text, the number of results asked for and any search filters, so the same search costs one call, ever.

A store that does not charge per search is searched afresh each time, so documents added to it are found.

Before spending, `corpus check --query TEXT` says how many searches it may make and how many are already kept. `run --dry-run` counts the documents and searches already cached, per corpus, which cost no call.

## What a provider's terms allow

Documents and searches are often licensed separately. A profile, or any corpus block, can say what may be kept on disk:

```yaml title="casebench.yaml"
corpora:
  court-api:
    connector: http
    metered: search
    keep: [documents]       # fetched texts only; searches are made each time
    options: { ... }
```

| `keep` | Effect |
| --- | --- |
| left out | Documents are kept, and searches when the corpus is `metered: search` |
| `[documents]` | Documents only |
| `[searches]` | Searches only, when the corpus is `metered: search`. Every read of a document is a fetch. |
| `[]` | Nothing is written under `.casebench/corpus-cache/` |

Adding a profile whose `keep` leaves something out says what will not be kept and that each such call is paid again on every run and re-score.

## Clear it

```sh
casebench corpus cache clear
```

It deletes every cached document and every kept search, of every corpus, and says how many of each it removed.

## Keep it out of git

`.casebench/` holds the cache, the answer keys, the runs and the price lists. Keep it out of git apart from the files that belong to the setup, with a `.casebench/.gitignore` that holds these lines:

```text
*
!.gitignore
!target.py
!casebench.schema.json
```

The setup guide a coding agent follows writes this file, and so does the workbench when it saves a key to `.casebench/.env`. Commit the suites and the reports you want to share from outside `.casebench/`.
