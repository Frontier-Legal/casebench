---
status: accepted
date: 2026-10-15
decision-makers: Casebench maintainers
---

# Lawyers write cases in a spreadsheet, and research, drafting, editing and extraction tasks are graded

Adds to [0002](0002-evaluation-case-model.md) (the case model), [0039](0039-one-case-by-a-lawyer.md) (one case by a lawyer) and [0047](0047-the-judge-rests-on-evidence.md) (the judge rests on evidence).

## Context and problem statement

A firm's most trusted ground truth is its own matters with its lawyers' answers, and it lives in spreadsheets and Word files. `casebench case new` takes one case at a time at a terminal ([0039](0039-one-case-by-a-lawyer.md)), which suits a lawyer testing one point, not a lawyer handing over fifty matters. Court decisions label questions and outcomes, never drafting, editing or extraction, so those tasks have only the firm's own answers to be graded against. Until now every case was a `qa` or `outcome` case, and no metric read a ranked list of authorities, an edited document or extracted fields.

## Considered options

1. A spreadsheet per task type that `casebench template lawyer` writes and `casebench import` reads, one row per case. Each key point becomes a criterion. Research, editing and extraction get metrics of their own, and drafting is graded by criteria.
2. YAML files a lawyer fills in.
3. Every new task graded only by criteria the judge decides.

## Decision outcome

Chosen option 1, because a lawyer fills a spreadsheet without learning a format, and because what can be checked without a model should be: a ranked list against gold authorities, a clause left untouched, a field's value. Option 2 asks lawyers for a format. Option 3 makes a judge decide what code can count.

- **The template.** `casebench template lawyer --task qa|research|drafting|editing|extraction [--out FILE]` writes an XLSX workbook, or a CSV when `FILE` ends in `.csv`. The workbook has one sheet named after the task, with a header row, and a sheet that says what each column takes. A cell that holds several items takes one per line.

  | Task | Columns |
  |---|---|
  | qa | id, question, facts, reference answer, key points, statutes, precedents |
  | research | id, question, constraints, reference answer, key points, statutes, precedents |
  | drafting | id, instruction, facts, document, reference answer, key points, statutes, precedents |
  | editing | id, instruction, document, issues, key points |
  | extraction | id, document, fields, expected |

  - **Key points** are lines such as `+5 Concludes the dismissal is invalid` or `-4 Relies on the repealed article`. A line without a weight weighs 1.
  - **Document** is a path to a `.txt`, `.md` or `.docx` file, relative to the spreadsheet. Its text becomes the case's `document` input, so the frozen suite holds it and its hash covers it.
  - **Issues** are lines such as `9.2: Uncapped indemnity`, naming the clause by its number.
  - **Fields** are lines such as `party_a: The first party's name`, and **expected** gives each field's value as `party_a: Acme A.Ş.`.
- **The import.** `casebench import FILE --suite DIR --by NAME` reads every sheet named after a task type, or a CSV with `--task`, and adds one case per filled row to the suite, which is frozen again as `case new` freezes it. It prints the old and new hash. The cases are `approved` with NAME as the reference's author and `lawyer` as their source, as a lawyer's case written by hand is ([0039](0039-one-case-by-a-lawyer.md)). A row without an id gets the file's name and its row number.
- **A key point is a criterion.** Each key point becomes a fact of kind `key point`, whose evidence is the spreadsheet and the row, written by NAME. The criterion is the lawyer's own text with its weight. The row's reference answer is a fact of kind `answer` that each key point's criterion also comes from, so the judge receives it as evidence ([0047](0047-the-judge-rests-on-evidence.md)). A reference answer alone makes no criterion: a row with no key points is unevidenced, the import names it, and the report lists it.
- **Statutes and precedents** become facts as `case new` makes them, and `casebench case resolve` resolves them to corpus documents ([0039](0039-one-case-by-a-lawyer.md)).
- **Task types** are built-in task plugins, each with its inputs and default metrics. A row with key points also gets `criteria`.

  | Task | Inputs | Metrics |
  |---|---|---|
  | qa | question, facts | criteria |
  | research | question, constraints | authority_recall, authority_ndcg, citation_integrity |
  | drafting | instruction, facts, document | criteria, citation_integrity |
  | editing | instruction, document | issues_found, edit_preservation |
  | extraction | document, fields | fields |
- **Research.** The target returns its authorities in rank order as `citations`, with the synthesis as its answer. When it returns none, the authorities are the citations the judge lists from the answer, in the order they appear. Each is resolved to a corpus document as other citations are ([0029](0029-statute-and-precedent-scores.md)). `authority_recall` is the share of the gold authorities, the row's statutes and precedents, found in the first ten; `authority_ndcg` is the normalised discounted cumulative gain over the same ten, with each gold authority of equal weight. Both name each gold authority the first ten miss as "missed key authority". A case whose gold authorities have not all resolved to corpus documents is not scored for them, and the report lists it as unevidenced until `casebench case resolve` resolves them.
- **Drafting** is graded by the key points' criteria. Every citation in the draft is checked against the corpus by `citation_integrity`.
- **Editing.** The target returns the edited document. Both documents are split into clauses at each line that starts with a clause number, such as `4.` or `9.2`; text before the first number is the preamble. `issues_found` is the share of listed issues whose clause the edit changed, and names each one left unchanged. `edit_preservation` is the share of clauses outside the issues left unchanged, and shows the diff of each one changed. Whitespace does not count as a change. Both are code, with no model.
- **Extraction.** The target returns a JSON object of field values as its answer. `fields` is the share of expected fields matched, exactly or after normalising: Unicode NFC, case folded, whitespace collapsed and surrounding punctuation dropped. The explanation says how each field matched, or what came back instead.

### Consequences

- Good, because a lawyer hands over a firm's matters in the tool they already use, and each key point is graded as they wrote it.
- Good, because the editing, extraction and research checks are code, so they cost nothing and never disagree with themselves.
- Bad, because editing counts any change of wording outside the issues, also one that keeps the meaning. A lawyer who wants rewording outside the issues lists that clause as an issue.
- Bad, because a document whose clauses are not numbered at the start of a line has one clause, the preamble.

## Revisit when

- Lawyers ask for documents with clauses numbered another way, or with tracked changes.
- Research targets return more than ten authorities that matter.

## More information

- The task types and their metrics in [architecture.md](../design/architecture.md).
- Järvelin and Kekäläinen, "Cumulated gain-based evaluation of IR techniques", ACM TOIS 20(4), 2002.
