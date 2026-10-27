---
title: Measure a tool Casebench cannot call
description: Score a legal research tool you can only use through its web page. Export a suite's questions as CSV, paste each answer back, and import the sheet as a run.
sidebar:
  order: 7
---

Some tools have no API Casebench can call: a legal research product you reach through its web page, or a system behind someone else's login. You can still measure one against the same suite and the same scoring as your own agent. Casebench writes the questions to a sheet, a person asks the tool each one and pastes its answer, and Casebench scores the sheet as a run.

## Export the questions

```sh
casebench export --suite suites/employment --format csv
```

```text frame="terminal"
wrote 6 questions to questions-employment.csv; fill the answer column, then:
  casebench import questions-employment.csv --suite suites/employment
```

The file is named after the suite's folder unless `--out FILE` names another. Casebench refuses to overwrite a file that exists.

The sheet has one row per case: its id, the repeat, each input the cases give, and an empty `answer` column.

```text title="questions-employment.csv"
case_id,repeat,question,answer
written-notice,0,"Under Examplia law, is a dismissal communicated only by telephone valid, and what remedies does the employee have?",
probation,0,"Must an Examplia employer give reasons or notice to end employment during a three-month probation period?",
overtime,0,"What limitation period applies to claims for unpaid overtime pay under Examplia law, and from when does it run?",
```

## Fill in the answers

Paste each question into the tool, as a user would ask it, and paste the tool's full answer into the row's `answer` cell. Keep the citations as the tool wrote them: the judge reads them from the text.

- Leave `case_id` as it is. A row that names a case the suite does not have is refused with its row number.
- A row left blank is reported as unanswered and is not scored.
- Leave `repeat` as the sheet gives it. It must be a whole number.

Any spreadsheet program works, as long as you save as CSV with the header row intact.

## Import the sheet

```sh
casebench import questions-employment.csv --suite suites/employment
```

`casebench import` sees a sheet of answers by its `case_id` and `answer` columns. It stores the sheet as a run whose target is `offline`, scores it with the config's judge and corpus as `casebench run` scores a run, and prints the same report:

```text frame="terminal"
run 20261026T200546Z-ee517e8c05b049c4ab247f241a0c5d06: 2 answers from questions-employment.csv, 4 cases unanswered
```

The judge's calls are paid with your key, as in any run. The import holds those calls to the [perimeter](/developers/guides/setup/network/) and prices them as a run does.

Each import is a new run. To score again, for example after you set a missing key, import the sheet again. Do not resume the imported run with `casebench run --run-id`: that sends its unanswered cases to the target in `casebench.yaml`, and the run would then mix two systems' answers.

## What the run holds

An imported run has no recorded steps, so the [authority funnel](/developers/concepts/authority-funnel/) reports "no diagnostic possible" and the workbench's harness view is empty. Every citation check, criterion and score works as for any run.

To compare the tool with your own agent, run your agent on the same suite and compare the two runs. See [Compare two runs](/developers/guides/runs/compare-runs/).

## Related

- [Review answers in a spreadsheet](/developers/guides/runs/spreadsheet-review/), the other sheet Casebench writes.
- [Export a report](/developers/guides/runs/export-report/).
