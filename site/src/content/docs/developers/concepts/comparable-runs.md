---
title: Comparable runs
description: Every score set records what produced it, so two runs can be judged comparable from their files alone, without the repository's history.
sidebar:
  order: 6
---

A score depends on your agent, and also on the judge, its prompts, the corpus, the extraction models and each metric's code. Change any of those and the same agent can score differently. Casebench makes that visible in the data itself.

## What a score set records

The first line of every score set, and `produced_by` in `report.json`, records:

- the Casebench version;
- each metric's version, and whether it reads the judge, the corpus or neither;
- each judge's provider, model and family, and how many candidates it matches a citation against;
- a hash of each prompt the judge is asked;
- each corpus's name and the key of its settings;
- for court-derived cases, the models that extracted the answer keys.

```json title="report.json (part)"
"produced_by": {
  "casebench_version": "0.0.0",
  "metrics": { "outcome": { "version": "1", "reads": [] } },
  "judges": [],
  "prompts": {},
  "corpora": {},
  "extracted_by": []
}
```

## What moves what

| Setting changed | Metrics that are no longer comparable |
| --- | --- |
| A metric's version | That metric |
| The judge or a judge prompt | Every metric that reads the judge |
| A corpus | Every metric that reads the corpus |
| The extraction models | Every metric |
| The Casebench version alone | None. A metric that scores differently gets a new version. |

`casebench compare` lists every setting that differs between two runs' latest score sets and marks each metric it moves as not comparable, while still showing the figures. `casebench gate` exits 2 instead of judging when such a setting differs, and the workbench's History marks such a run with a diamond.

## Why in the data

A changelog helps readers who build from the repository. A team comparing two runs from installed packages, or a buyer reproducing a vendor's result, has only the files. The score set's header answers the question for both.

## Reproducing a result

A third party with the suite (its id and content hash), the same corpus snapshot, the same judge and the open-source code can reproduce a report. The manifest and the score set name everything else they need.

## Related

- [Compare two runs](/developers/guides/runs/compare-runs/).
- [Run folder](/developers/reference/run-folder/).
