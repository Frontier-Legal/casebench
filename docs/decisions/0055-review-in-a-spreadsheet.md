---
status: accepted
date: 2026-10-15
decision-makers: Casebench maintainers
---

# Lawyers review a run in a spreadsheet when there is no server, and the import writes the same verdicts the workbench writes

Adds to [0047](0047-the-judge-rests-on-evidence.md) (lawyers' verdicts replace the judge's), [0049](0049-lawyers-write-cases-in-a-spreadsheet.md) (cases from a spreadsheet) and [0050](0050-the-review-queue.md) (the review queue).

## Context and problem statement

Some firms will not push data to a cloud or run a server for an evaluation, yet their lawyers have to review the answers. Most legal AI teams already do this in a spreadsheet. A lawyer's verdict today reaches a run through the workbench or `casebench review criterion` ([0047](0047-the-judge-rests-on-evidence.md)), and both need someone at the engineer's machine. A spreadsheet also travels by email, so it should not carry the text of court decisions, which a provider's terms may not let anyone copy.

## Considered options

1. `casebench export --review RUN` writes an XLSX with one row per criterion the judge decided. `casebench import` reads it back, checks every row before writing any, and appends each filled row to the run's `reviews.jsonl`, as the workbench does.
2. One row per answer, with a pair of verdict and note columns for each criterion.
3. A CSV, with the run's ids in every row.

## Decision outcome

Chosen option 1, because a criterion is what a lawyer's verdict is about, so a row maps to one verdict and the import needs no layout rules. Option 2 gives a varying number of columns per row, which lawyers cannot sort or filter. Option 3 offers no list of allowed verdicts, no links and no column widths.

- **Export.** `casebench export --review RUN [--out FILE]` writes `review-RUN.xlsx` by default.
  - **Which rows.** There is one row for each criterion verdict in the run's latest score set that no lawyer has given yet. `--all` adds the reviewed ones, with the lawyer's verdict filled in. Rows where the judges disagreed come first, then failed criteria, then the rest, as in the queue ([0050](0050-the-review-queue.md)).
  - **Columns.** Case, repeat and criterion identify the row. Then come the question, the AI's answer, the criterion, the judge's verdict, the quote of the answer the judge relied on, and the evidence. Last come the three columns the lawyer fills: **verdict** (`pass` or `fail`, from a list), **note**, and **reviewed by**.
  - **Evidence by link, not by copy.** A fact a lawyer wrote is shown as written, since it is the team's own text. A fact from a court decision is shown as its kind and value, such as the statute the court applied, with the decision's document id. The court's passage is never quoted, and no document is fetched to make the sheet. When the corpus's entry in `casebench.yaml` gives `link:`, a URL with `{id}` for the provider's document id, the cell links to the decision on the provider's site.
  - **Which run.** A hidden sheet records the run, the score set and when the sheet was made.
- **Import.** `casebench import FILE` sees a review sheet by its hidden sheet and needs no `--suite`. It finds the run under `--runs-dir`.
  - **Every row is checked before any is written.**
    - The verdict must be `pass` or `fail`, in any case.
    - A verdict that differs from the judge's needs a note.
    - The row needs a reviewer, from its **reviewed by** cell or from `--by`.
    - The row must name a criterion verdict the run still has.
  - The first bad row stops the import and is named, with its row number and column. Nothing is written.
  - **Rows left empty are skipped,** and their answers stay in the queue.
  - **Each filled row is a lawyer's verdict** with the reviewer's name, the time of the import and the note. It is appended to `reviews.jsonl`, so it replaces the judge's verdict in the report, the gate and the calibration exactly as a workbench verdict does. When the workbench's database exists, its event log keeps each verdict, and the import itself under the sheet's name.
- **Out of scope.** Approving court drafts in this sheet: drafts are approved in the queue or written in the authoring template ([0049](0049-lawyers-write-cases-in-a-spreadsheet.md)).

### Consequences

- Good, because a lawyer reviews with no login, no server and no install, and the verdicts count as fully as those given in the workbench.
- Good, because no decision text leaves in the file.
- Bad, because a lawyer without access to the provider's site sees only the document id beside a court fact.
- Bad, because a verdict's time is when the sheet was imported, not when the lawyer wrote it.

## Revisit when

- Lawyers ask for the passage itself in the sheet, and the provider's terms allow it.
- Two lawyers return sheets for the same run with different verdicts on the same row. Today the one imported last counts, as in the workbench.

## More information

- Workbench design, "Spreadsheet review": [workbench.md](../design/workbench.md).
