---
status: accepted
date: 2026-10-15
decision-makers: Casebench maintainers
---

# Lawyers compare two runs blind, and a run's report, with its error rates, is exported for partners by practice area

Adds to [0028](0028-scores-baselines-and-intervals.md) (scores, baselines and intervals), [0034](0034-versioned-formats.md) (versioned formats), [0047](0047-the-judge-rests-on-evidence.md) (lawyers' verdicts replace the judge's) and [0050](0050-the-review-queue.md) (the review queue). Follows the workbench design ([workbench.md](../design/workbench.md)).

## Context and problem statement

Asked whether a new agent version is better, `casebench compare` answers with each metric and the interval of its difference ([0028](0028-scores-baselines-and-intervals.md)). That rests on the judge. A lawyer asked the same question reads both answers, and a lawyer who knows which one is new leans towards it. A partner handed a table of means from 0 to 1 cannot act on it either: they ask how often the agent cites a decision that does not exist, in which practice areas, show me one, and who checked the answer key. A case today names no practice area, and the cases a lawyer approved carry the approver only as the reference's author.

## Considered options

1. A case names its practice area and its approver. The report gives four error rates with their failing answers. Lawyers compare two runs blind in the workbench, and their preferences are kept in the run's folder. The report exports to one HTML file, PDF and DOCX.
2. Practice areas as a tag convention on cases, such as `area:labour`, and the export as HTML only, for the reader to print.
3. Leave comparison to the judge's scores and export the report as `report.json` for a team to lay out.

## Decision outcome

Chosen option 1, because a practice area is something every lawyer writes and reads, so it is a field, not a convention to remember; a preference given blind is evidence the judge cannot give; and partners read PDF and Word. Option 2 hides the practice area in a convention and leaves partners a browser's print dialog. Option 3 leaves the question "is it better" to the model it is about.

- **The case, format 1.1.**
  - `practice_area`: the area of law, as the team names it, such as `labour` or `tax`. It is optional. Cases without one are reported under "no practice area".
  - `approved_by`: who approved the answer key. Every path that approves a case sets it: the spreadsheet import and `case new` to the author, an approved court draft to its reader, a change saved at once to the lawyer who saved it, and a change or a case approved by a second editor to that editor ([0053](0053-second-approval-is-opt-in.md)). For a case approved before it existed, the reference's author stands in, as it was the approver on every path then.
  - The spreadsheet gains an optional `practice area` column on every task's sheet, and the golden data form a field for it.
  - Each score carries its case's practice area, as it carries its jurisdiction ([0036](0036-several-corpora.md)).
  - Format 1.0 is unchanged.
- **Error rates.** The report gives four, each the share of answers with the error, with its 95% interval ([0028](0028-scores-baselines-and-intervals.md)), over the answers the error could occur in:

  | Error | An answer has it when | Over the answers |
  |---|---|---|
  | fabricated citation | a citation names a decision or statute the corpus does not hold | checked for citations |
  | unsupported claim | a citation the corpus holds does not support the claim made with it (misgrounded) | checked for citations |
  | wrong outcome | it states a ruling other than the court's or the lawyer's, or none: the outcome metric found another or none, or a criterion asking for that outcome failed | scored for an outcome |
  | wrong statute | the statute metric found a statute the court did not apply | scored for statutes |

  - A lawyer's verdict replaces the judge's before the rates are counted ([0047](0047-the-judge-rests-on-evidence.md)), so a rate read later counts verdicts given since scoring.
  - Each rate lists its failing answers. In the workbench each opens with the question, the answer and the court record or the lawyer's reference side by side, as in answer review.
  - `report.json`, format 1.1 and not yet released, gains `error_rates`, and `casebench report` prints them.
- **Blind comparison.**
  - The workbench's "Compare runs" page takes two runs of one suite: the suite's hash must match, as `compare` and `gate` require.
  - Each answer pair is shown as A and B, the question and the reference beside them. Which run is A is drawn from a hash of the two run ids, the case and the repeat, so it stays put on reload and differs from case to case. Nothing on screen names a run, a score, a cost or the judge's verdict until the preference is given.
  - The reader presses A, B or E (Equal) and writes a reason, which is required, then Cmd+Enter or Ctrl+Enter gives it and opens the next pair.
  - Each preference is appended to the second run's folder, in `preferences.jsonl`, with the first run's id, the case, the repeat, which run was shown as A, the choice, the reason, who and when. The event log keeps it too. For each answer pair the latest preference counts.
  - The summary gives, per practice area, the second run's wins, losses and ties. Its interval is the 95% bootstrap interval of the mean of +1 for a win, −1 for a loss and 0 for a tie, seeded by the suite as in [0028](0028-scores-baselines-and-intervals.md). A difference is marked significant only when that interval leaves out 0 and the exact two-sided sign test of wins against losses, ties left out, gives p below 0.05. A few pairs that all went one way have an interval of one point, and the sign test keeps them from being called significant.
  - `casebench compare FIRST SECOND` prints the same summary when lawyers have compared the two runs.
- **The report for partners.** `casebench report RUN --export FILE` writes it as HTML, PDF or DOCX, by the file's extension; the workbench's report page downloads the same three. It holds:
  - the suite, its hash, the run, its date and the target;
  - each metric by task and practice area, with the number of cases, the mean and its interval, over lawyer-approved cases, and the number of unreviewed cases left out, as the gate counts them ([0048](0048-a-gate-in-ci.md));
  - the four error rates with their intervals;
  - worked examples: for each error rate with failures, up to three failing answers, each with its question, the answer, and its evidence (the citation and what the corpus found for it, or the court's passage or the lawyer's reference the criterion rests on);
  - who approved the golden data: each approver and how many cases they approved, the cases whose approver is not recorded, and the unreviewed cases.
- **One file with no server.** The HTML export holds its styles inline and loads no script, font or image from elsewhere, so it opens from disk or an email attachment. It prints to A4 with its tables whole.
- **Libraries.** PDF through ReportLab (BSD), DOCX through python-docx (MIT). The PDF embeds Noto Sans (SIL Open Font License), shipped in the wheel, because the PDF standard fonts lack letters such as ğ, ş and ı.

### Consequences

- Good, because a lawyer's judgement of which version is better is recorded without knowing which one is new, and kept beside the run it judges.
- Good, because a partner reads error rates, worked examples and approvers in the format they open every day, with intervals that say what is noise.
- Good, because the practice area and the approver are fields every reader and writer of a case sees.
- Bad, because each export format is laid out separately, so a change to the report touches three writers.
- Bad, because the PDF covers the scripts Noto Sans covers: Latin, Greek and Cyrillic. Another script needs another font.
- Bad, because with several lawyers comparing, only the latest preference on a pair counts until team mode can weigh several.

## Revisit when

- Team mode lets several lawyers give a preference on the same pair.
- Partners ask for the comparison in the exported report.
- A jurisdiction whose script Noto Sans does not cover adopts Casebench.

## More information

- Blind pairwise preference with an "equal" option, and a sign of the mean difference with a bootstrap interval, follow [0028](0028-scores-baselines-and-intervals.md)'s convention for intervals.
- Workbench design: [workbench.md](../design/workbench.md), "Compare runs" and "Report".
