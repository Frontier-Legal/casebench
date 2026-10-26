---
title: Review in a spreadsheet
description: Let lawyers confirm or overrule the judge with no server and no login. Export a run's criteria to a spreadsheet, import their verdicts back, or record one verdict at the command line.
sidebar:
  order: 6
---

A lawyer's verdict on a criterion replaces the judge's in the report, the gate and the export. Most lawyers give verdicts in the workbench's review queue. When a firm runs no server and lawyers cannot reach your machine, send them a spreadsheet instead. Every verdict it brings back counts exactly as one given in the workbench.

## Export the sheet

```text frame="terminal"
$ casebench export --review .casebench/runs/after-prompt-fix
wrote 12 rows to review to review-after-prompt-fix.xlsx
then: casebench import review-after-prompt-fix.xlsx
```

`--out FILE` names the file; the default is `review-RUN.xlsx`.

There is one row per criterion the judge decided that no lawyer has reviewed yet. Rows where two judges disagreed come first, then failed criteria, then the rest, as in the review queue. `--all` adds the rows already reviewed, with the lawyer's verdict filled in.

### The columns

| Column | Holds |
| --- | --- |
| `case`, `repeat`, `criterion` | Which criterion verdict the row is |
| `question` | What the agent was asked |
| `the AI's answer` | The agent's answer |
| `what the answer must do` | The criterion |
| `the judge said` | `pass` or `fail` |
| `the judge relied on` | The quote from the answer the judge's verdict rests on |
| `evidence` | The fact the criterion comes from |
| `verdict` | The lawyer fills it: `pass` or `fail`, picked from a list |
| `note` | Why, needed when the verdict differs from the judge's |
| `reviewed by` | The lawyer's name |

A fact a lawyer wrote is shown as written. A fact from a court decision is shown as its kind and value with the decision's document id, such as:

```text
rule: unused annual leave is not lost at the end of the year unless the employer invited the employee to take it in time. (court record corpus:CA-2025-04)
```

The court's passage is never copied into the sheet, and no document is fetched to make it, so the file can travel by email without carrying text a provider's terms protect. When the corpus's block in `casebench.yaml` has a `link:` with `{id}`, such as `https://decisions.example/doc/{id}`, the evidence cell links to the decision on the provider's site. `--config` names the config the links are read from.

A hidden sheet records the run, its score set and when the sheet was made, so the import knows where the verdicts go.

## Import the verdicts

```text frame="terminal"
$ casebench import review-after-prompt-fix.xlsx
imported 2 verdicts on run after-prompt-fix by Ayşe Demir, 1 overruling the judge; they replace the judge's in the report and the gate
```

The import recognises a review sheet by its hidden sheet and needs no `--suite`. It finds the run under `.casebench/runs`, or under `--runs-dir`.

Every row is checked before any is written:

- the verdict is `pass` or `fail`, in any case;
- a verdict that differs from the judge's has a note;
- the row has a reviewer, from its `reviewed by` cell or from `--by`;
- the row names a criterion verdict the run still has.

The first bad row stops the import, and nothing is written:

```text frame="terminal"
Error: rv-bad.xlsx, row 3, column note: the judge said pass; overruling it needs a note; nothing was imported
```

Rows left empty are skipped, and their answers stay in the review queue. Each filled row is appended to the run's `reviews.jsonl` with the reviewer, the note and the time of the import:

```json
{"case_id":"annual-leave","repeat":0,"criterion_id":"c2","verdict":"fail","judge":"pass","note":"The answer does not say how the leave is paid.","by":"Ayşe Demir","at":"2026-10-26T20:06:42+00:00"}
```

When the workbench's database exists, its event log keeps each verdict too. `--database` names another database. If two lawyers return sheets with different verdicts on the same row, the one imported last counts.

Court drafts are not approved in this sheet. They are approved in the review queue, or written as cases in the [authoring spreadsheet](/developers/guides/suites/lawyer-cases/#from-a-spreadsheet).

## One verdict at the command line

`casebench review criterion` records a single verdict:

```text frame="terminal"
$ casebench review criterion .casebench/runs/after-prompt-fix --case annual-leave --criterion c1 \
    --verdict pass --by "Ayşe Demir"
recorded: Ayşe Demir says pass, which agrees with the judge (pass)
it replaces the judge's verdict in the scores the next time the run is scored; scoring again reads the judge's kept replies and asks the judge nothing
judge vs lawyers · rule: 1 of 2 agreed, 1 overruled
```

`--case`, `--criterion`, `--verdict` and `--by` are required. `--repeat` picks the repeat, `0` by default. A verdict that overrules the judge needs `--note`:

```text frame="terminal"
Error: the judge said pass; overruling it needs --note saying why
```

## Where verdicts count

| Reader | Uses lawyers' verdicts |
| --- | --- |
| `casebench gate` | At once, over the judge's |
| `casebench report RUN` | In the error rates and the judge-versus-lawyers lines at once. The metric tables show the judge's scores until the run is scored again. |
| `casebench report RUN --export FILE` | At once |
| The workbench | At once |
| `casebench compare` | No. It compares the judge's score sets. |

Score the run again by running it with the same `--run-id`. Scoring again reads the judge's kept replies and asks the judge nothing.

### The judge against lawyers

The report counts, for each kind of criterion, the verdicts lawyers gave, how many agreed with the judge and how many overruled it:

```text frame="terminal"
judge vs lawyers · rule: 1 of 2 agreed, 1 overruled
```

Read these lines before you rely on a judge for a kind of criterion.

## Related

- [Review an answer](/lawyers/guides/review-an-answer/), the lawyer's side in the workbench.
- [Invite lawyers to a team server](/developers/guides/team/invite-lawyers/), for lawyers who review elsewhere.
- [Run folder](/developers/reference/run-folder/).
