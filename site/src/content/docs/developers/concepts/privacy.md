---
title: Privacy and what leaves your machine
description: What Casebench sends where, what a team server receives and never receives, and what a security review needs to know.
sidebar:
  order: 8
---

Casebench runs on your machines. Nothing leaves them except calls to the system under test, the judge and extraction models you configure, your corpus, and a team server if you push to one. There is no telemetry, no usage reporting and no update check.

## Who receives what

| Recipient | Receives | Why |
| --- | --- | --- |
| The system under test | Each case's inputs, and a short greeting from `casebench check` | It is what you are testing |
| The judge's model provider | Answers, their citations, the case's evidence and the corpus documents needed to check them | It lists, matches and weighs citations and grades criteria |
| The extraction models' provider | Full decision texts | Reading answer keys out of decisions |
| Your corpus | Searches for citations, and fetches by id | Finding what exists |
| The public model catalog and price lists | GET requests for public lists, with nothing of yours | Picking models and pricing a run |
| Your team server, when you push | What the next section lists | So lawyers can review in a browser |

Every call stays inside [the perimeter](/developers/concepts/perimeter/): a run calls only the hosts `casebench.yaml` names.

## What a team server receives

`casebench push` sends each suite the pushed runs ran, with its cases and their evidence excerpts, and each run's `run.json`, results, score sets, `report.json`, lawyers' reviews and preferences. Without `--traces` the results go up without their steps; with it, steps go as ids and numbers only: kind, name, model, provider, tokens, times, document ids and sizes.

It never sends the judge's kept replies, the corpus or its cache, full decision texts, the agent's code, `casebench.yaml`, `.env` files or any key. The server accepts only the files it expects and refuses any other path. It never computes a score: it has no route that scores, re-scores or calls a judge.

## Keys

`casebench.yaml` names each key by its environment variable, or by the `.env` file `keys:` points to, and never holds a value. No key value is printed, not even in part. Every file a run writes is scrubbed of keys. See [The perimeter](/developers/concepts/perimeter/#keys-never-reach-a-file).

## What stays on disk

Under `.casebench/` in your project: the corpus cache, answer keys, suites, runs with answers and captured steps, the workbench's database at `.casebench/casebench.db`, and kept prices. A provider profile's `keep` setting limits what is cached when the provider's terms require it.

## What `init` reads

`init` reads your project's dependency files and its own Python files as text, without importing or running them, and never reads the value of an environment variable. It reports how many files it read.

## The workbench

`casebench ui` binds to `127.0.0.1`, answers only requests whose `Host` is the loopback address it serves, as `127.0.0.1` or `localhost`, so a web page elsewhere cannot reach it through DNS rebinding, and accepts writes only from its own origin. `casebench ui --role reviewer` serves the review view only: the API leaves the engineering fields out.

## Related

- [Run a team server](/developers/guides/team/team-server/).
- For lawyers: [Confidentiality](/lawyers/concepts/confidentiality/).
