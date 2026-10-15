---
status: accepted
date: 2026-10-15
decision-makers: Casebench maintainers
---

# Golden data changes only when a second editor approves, and a question can be tried within a daily dollar limit

Adds to [0049](0049-lawyers-write-cases-in-a-spreadsheet.md) (cases in a spreadsheet), [0050](0050-the-review-queue.md) (the review queue) and [0051](0051-what-a-run-spends.md) (what a run spends). Follows the workbench design ([workbench.md](../design/workbench.md)).

## Context and problem statement

One lawyer's slip in a reference answer silently changes every score built on it. Today a lawyer edits a case in a spreadsheet and imports it, or rewrites it with `case new`, and nothing asks a second lawyer to look. A lawyer who wants to see how the team's agent answers a question has to ask an engineer to run it. A model call made from the workbench costs money that no one budgeted.

## Considered options

1. In the workbench, a change to an approved case is held as a proposal until a second editor approves it, and a new case enters its suite as a draft awaiting one. A lawyer can try a question against the configured target, within a daily dollar limit the engineer sets, and keep it as a new case.
2. Every save takes effect at once, and the event log records who changed what.
3. Changes are made only in spreadsheets, approved by whoever imports them.

## Decision outcome

Chosen option 1, because a reference answer is evidence that every later score rests on, and a lawyer's duty of supervision is easiest to meet when the tool makes the second look the only way in. Option 2 records a slip after it has changed the scores. Option 3 leaves the second look to an import that one person runs.

- **Golden data** is the cases in the suites the workbench reads. The workbench lists them per suite, with each case's task, source, approval and any change waiting. A case opens in a form with the same fields as the spreadsheet for its task ([0049](0049-lawyers-write-cases-in-a-spreadsheet.md)): its inputs, the reference answer, key points with weights, statutes and precedents.
- **A change is a proposal.** Saving a changed case needs a reason. It records the case before and after, the author, the time and the reason, and leaves the suite as it was.
  - It waits in every other editor's queue. That editor sees each changed field before and after, the author, the time and the reason, and approves it, or rejects it with a note.
  - An approved change is written into the suite, which is frozen again and gets a new hash ([0039](0039-one-case-by-a-lawyer.md)).
  - No one approves their own change.
- **A new case** from the form enters its suite as a draft, with its author, and a proposal to approve it. The second editor's approval makes it approved.
  - Until then it can be run, with its scores in the report's unreviewed row.
- **The event log** keeps each proposal, approval and rejection, with who, when, before, after and why ([0050](0050-the-review-queue.md)).
- **Who may edit.** Every person in the workbench may, except where `casebench ui --role reviewer` serves the review view only; a reviewer reviews answers and proposes no change. Roles with logins come with team mode.
- **A court draft** is still approved by one lawyer with the decision's passages in view ([0050](0050-the-review-queue.md)). Its facts rest on the decision itself.
- **Try a question.** A lawyer asks the target configured in `casebench.yaml` a question.
  - It is sent as `casebench target check` sends one, inside the same network rules ([0046](0046-the-perimeter.md)).
  - Every citation in the answer is then checked against the corpus by the configured judge.
  - "Save as case" opens the form with the question filled in, and the case is added as a draft awaiting approval.
- **The daily limit.** `workbench: try_daily_limit_usd:` in `casebench.yaml` sets what trying questions may spend each day, in US dollars, summed as a run's spend is summed ([0051](0051-what-a-run-spends.md)): the agent's model calls and the judge's.
  - Before sending, the workbench compares what was spent today with the limit. When the limit is reached, it says so and sends nothing.
  - Without a limit, or when a model the agent or the judge calls has no price, the workbench cannot measure what a question costs, so it sends nothing and says what is missing.
  - Each question's spend is kept in the workbench's database.

### Consequences

- Good, because no reference answer changes without two people having read it, and the log shows both.
- Good, because a lawyer turns a spot check into a case in one step, and the team knows what spot checks cost.
- Bad, because a change waits for a second editor, which a team of one does not have. Such a team keeps editing in spreadsheets, as before.
- Bad, because a target that calls models Casebench cannot price cannot be tried from the workbench until the team adds a price.

## Revisit when

- Team mode adds roles with logins and assignments.
- Teams want a court draft whose facts a lawyer edited to wait for a second editor too.

## More information

- The workbench's golden data screen and its "try a question": [workbench.md](../design/workbench.md).
