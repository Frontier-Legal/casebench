---
title: Grade research, drafting, editing and extraction
description: The task types beyond legal questions and court outcomes, the inputs your agent receives for each, what it must return, and the metrics that grade it.
sidebar:
  order: 4
---

A case's task says what the agent is asked to do and how the answer is graded. Court decisions give `outcome` cases, and lawyers' questions give `qa` cases. Four more tasks have only your firm's own answers to be graded against, so lawyers write them in a spreadsheet or in the workbench: `research`, `drafting`, `editing` and `extraction`.

Where the answer can be checked without a model, it is. Editing and extraction are graded by code alone. Research is graded by code once the citations are resolved to corpus documents.

## The tasks at a glance

| Task | The agent receives | It returns | Default metrics |
| --- | --- | --- | --- |
| `qa` | `question`, `facts` | An answer in prose | `criteria` |
| `outcome` | `question`, `facts` | The ruling | `outcome` |
| `research` | `question`, `constraints` | Authorities in rank order, and a synthesis | `authority_recall`, `authority_ndcg`, `citation_integrity` |
| `drafting` | `instruction`, `facts`, `document` | A document | `criteria`, `citation_integrity` |
| `editing` | `instruction`, `document` | The edited document | `issues_found`, `edit_preservation` |
| `extraction` | `document`, `fields` | A JSON object of field values | `fields` |

A row with key points also gets `criteria`, whatever its task. The `extraction` sheet has no key points column.

## How the agent receives the inputs

A Python target's function is called with the inputs it names as parameters, or all of them when it takes `**kwargs`. An HTTP target's `body` names them as `"{{instruction}}"` or `"{{document}}"`, and a command target's `run` as `{instruction}`. A template that names an input the case does not have fails that case.

`document` is the full text. `fields` is a mapping of each field's name to what to take, such as `{"party_a": "The first party"}`.

One adapter can serve several tasks by naming every input it handles:

```python title="agent.py"
import json


def answer(
    question: str = "",
    facts: str = "",
    instruction: str = "",
    document: str = "",
    fields: dict | None = None,
) -> str:
    if fields is not None:
        values = extract(document, fields)  # your agent
        return json.dumps(values)
    if instruction:
        return edit(instruction, document)  # your agent
    return ask(question, facts)  # your agent
```

An extraction answer is the JSON object as text. A target that returns a mapping must put that text under `answer`.

## Write the cases

`casebench template lawyer --task TASK` writes the sheet for a task. Each sheet also has a `practice area` column, and an optional `id`.

| Task | Columns |
| --- | --- |
| `research` | `question`, `constraints`, `reference answer`, `key points`, `statutes`, `precedents` |
| `drafting` | `instruction`, `facts`, `document`, `reference answer`, `key points`, `statutes`, `precedents` |
| `editing` | `instruction`, `document`, `issues`, `key points` |
| `extraction` | `document`, `fields`, `expected` |
| `outcome` | `question`, `facts`, `outcome` |

- `document` is a path to a `.txt`, `.md` or `.docx` file, relative to the spreadsheet. Its text is copied into the case when you import it.
- `constraints` are limits on the research, such as courts or dates.
- `issues` are lines such as `9.2: Uncapped indemnity`, naming the clause by its number.
- `fields` are lines such as `party_a: The first party`, and `expected` gives each value as `party_a: Acme A.Ş.`.

Import the sheet as [Add lawyer-written cases](/developers/guides/suites/lawyer-cases/#from-a-spreadsheet) describes:

```sh
casebench import cases-editing.xlsx --suite suites/contracts --by "Ayşe Demir"
```

## Research

The target returns its authorities in rank order as `citations`, with the synthesis as its answer. When it returns none, the authorities are the citations the judge lists from the answer, in the order they appear. Each is resolved to a corpus document as any citation is.

The gold authorities are the row's `statutes` and `precedents`.

- `authority_recall` is the share of the gold authorities found among the first ten.
- `authority_ndcg` is the normalised discounted cumulative gain over the same ten, each gold authority of equal weight.

Both name each gold authority the first ten miss. A case whose gold authorities have not all resolved to corpus documents is not scored for them, and the report lists it as unevidenced. Resolve them with `casebench case resolve` once a corpus and a judge are set:

```text frame="terminal"
$ casebench import cases-research.xlsx --suite suites/research --by "Ayşe Demir"
added 1 cases from cases-research.xlsx, approved by Ayşe Demir
  r1 (row 2) is unevidenced for authority_recall, authority_ndcg: the row gives nothing to grade against, so runs will not score it for them
  r1: not in the corpus yet: Employment Act s 9; CA 2024/02; CA 2023/07; they resolve with a corpus, then casebench case resolve
```

## Drafting

The judge grades the draft against the key points' criteria, with the reference answer as the lawyer's evidence. `citation_integrity` checks every citation in the draft against the corpus.

## Editing

The target returns the whole edited document. Both documents are split into clauses at each line that starts with a clause number, such as `4.` or `9.2`. Text before the first number is the preamble.

- `issues_found` is the share of listed issues whose clause the edit changed. It names each issue left unchanged.
- `edit_preservation` is the share of the other clauses left unchanged. It shows a diff of each one changed.

Whitespace does not count as a change. Any other change of wording outside the issues does, even one that keeps the meaning. If rewording a clause is fine, list it as an issue. A document whose clauses are not numbered at the start of a line has one clause, the preamble.

An editing run with one issue, where the agent fixed clause 9.2 and also reworded clause 10:

```text frame="terminal"
editing · edit_preservation
  source   approval         place      n  score   95% interval  majority text-only
  lawyer   lawyer-approved  -          1    67%        67%-67%         -         -
editing · issues_found
  source   approval         place      n  score   95% interval  majority text-only
  lawyer   lawyer-approved  -          1   100%      100%-100%         -         -
```

The score set names the clause that changed and shows the diff:

```diff
--- clause 10
+++ clause 10
@@ -1,2 +1,2 @@
 10. Governing law
-Examplia law applies.
+Examplia law governs.
```

## Extraction

`fields` is the share of expected fields the answer matched, exactly or after normalising: Unicode NFC, case folded, whitespace collapsed and surrounding punctuation dropped. An answer that is not a JSON object scores 0 with the label `no JSON object of fields`.

The explanation says how each field matched, or what came back instead:

```text
wrong fields: law
party_a: normalised; law: expected 'Examplia law', got 'the law of Ruritania'
```

## Related

- [Add lawyer-written cases](/developers/guides/suites/lawyer-cases/).
- [Labels](/developers/reference/labels/).
- [Case format](/developers/reference/formats/case/).
