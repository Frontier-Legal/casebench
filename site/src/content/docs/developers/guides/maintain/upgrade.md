---
title: Upgrade a setup
description: Bring an existing casebench.yaml up to what a newer Casebench can use, without rewriting anything you set, and keep reading older suites and runs.
sidebar:
  order: 1
---

After you install a newer Casebench, the same three commands bring a setup up to date: `check`, `init` and `run`. Nothing is migrated by hand.

## See what the setup could use

```sh
casebench check
```

Besides its pass and fail lines, `check` lists what the newer version can use and your setup lacks. Each of these lines starts with `could use`, names the command that fills it in, and never fails the check. Two things are listed:

- a corpus reached over HTTP or MCP whose search results are not described, so the judge reads each candidate from the stored document. `casebench corpus add` suggests where the results keep their citation, type and passage.
- a judge with no context window, so a matching call is never split to fit. `casebench init` takes it from the model catalog.

`casebench check --json` puts the same lines under `advice`.

## Let init repair it

```sh
casebench init
```

In a folder that already has a `casebench.yaml`, `init` runs as a repair pass. It scans your code and the model catalog again and offers only what the config lacks:

- a capture route for each model client the config does not route yet;
- a context window for each judge or extraction model that has none;
- the team server, when you pass `--team-server URL`.

It prints the `could use` lines for your corpora too, shows the changes and writes them only when you agree. Every setting you already wrote stays as it is. The file is written again with its header, which includes the line your editor reads the schema from, and other comments are not kept, so review the change in git before you commit it. `init` also rewrites `.casebench/casebench.schema.json` for the installed version, when the file starts with that line or when it writes the file.

When there is nothing to add, `init` says the file has everything this version adds and leaves it as it is.

## Prices are looked up now

Earlier releases had `init` and the workbench copy each model's price into `casebench.yaml`. They no longer write `price:`. `run`, `import` and `extract` read each model's price when they start: from OpenRouter's own list for a model called through OpenRouter or named by an OpenRouter id, else from the public model catalog. The last lists read are kept in `.casebench/prices.json` and used when the network is out of reach.

A `price:` already in your file still wins over the lists. Delete it to take the seller's current price, or keep it for a model no list has, such as one on your own servers.

## Older files keep working

| File | Read as |
| --- | --- |
| A suite manifest that names no format | Format 1.0, with a note. Its hash is checked as before. |
| A suite whose cases are `casebench.case/1.0` | As it is. Its hash is unchanged. |
| A `report.json` at `casebench.report/1.0` | As it is, by `casebench report` |
| A document id with no corpus name, from before several corpora | The id in the only corpus, when the setup has one |
| A score set without a header line | Scores only. Score the run again to record what produced it. |
| A `judge.jsonl` line without `usage` | A call of an unknown model, with no tokens and no price |

A setup with several corpora and suites from before ids named their corpus has to generate those suites again.

## Rescore an old run

Running a finished run's id again sends no case to the target, because every result is already stored, and scores the run into a new score set next to the old ones. A score set is never rewritten. Judge replies already in the run's `judge.jsonl` are read back instead of asked again, so the same judge with the same prompts costs nothing the second time:

```sh
casebench run --suite suites/employment-court --run-id court-1
```

The new score set's `report.json` is at the latest report format, with the error rates and spend that 1.1 adds.

## Before 1.0

While the version is 0.x, a minor release may change the command line, the file formats or the Python interface. The [changelog](/changelog/) names every break.
