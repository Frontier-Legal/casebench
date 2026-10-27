---
title: Folder
description: A corpus of JSON files on disk, one document each, for small sets and for trying Casebench out.
sidebar:
  order: 4
---

The `folder` connector reads `<path>/*.json`, one [document](/developers/reference/formats/document/) per file. It suits a few hundred decisions: a sample exported from your store, or a set you assembled for a test.

```yaml title="casebench.yaml"
corpora:
  folder:
    connector: folder
    jurisdictions: [GB]
    options:
      path: decisions
```

`casebench init --corpus folder --corpus-path decisions` writes the same block, without `jurisdictions`; add it to route citations by jurisdiction. On the workbench's Jurisdictions page, a folder of sample files is the last source offered for a country. A relative `path` is read from the folder that holds `casebench.yaml`.

## Ids

A document's id is its `id` field, or the file name without `.json` when it has none.

## Search

Search counts how many of the query's words a document contains, and ranks the documents by that count. That is enough to resolve a citation in a small folder, and too crude for a large one: put a large store behind its real search API and use the [HTTP connector](/integrations/stores/http-api/).

A result is described by its file name and the paragraph of its text the search matched best, so the judge can match citations without reading every candidate in full.

## Filters

A search filter matches a field of the document, at its top level or in its `metadata`. With `search_filters: { statute: { type: statute } }`, a search for a cited statute looks only at documents whose `type` is `statute`.

## Listing

A folder lists its documents, so `casebench extract`, `corpus check` and the first `casebench run` sample it with no `--query`.
