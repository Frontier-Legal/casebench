---
status: proposed
date: 2026-10-13
decision-makers: Casebench maintainers
---

# Every score set says what produced it; a strict pass rate and a second judge are reported beside the scores, never blended

## Context and problem statement

A result is worth something only when a reader can tell whether two runs can be compared. Today a run records its suite hash and the Casebench version ([0015](0015-suite-and-run-log-formats.md)), and each score records its metric's version. But nothing records which judge model or prompt graded it, so two score sets that differ only in their judge look alike.

A weighted criterion score also hides the case that matters most in legal work: an answer that meets most criteria but misses one material point is wrong, not mostly right. And one judge's verdict on a criterion is unchecked unless a lawyer reviews it. Its agreement with exact scoring is measured only on objective tests ([0026](0026-judge-and-citation-checks.md)).

## Considered options

1. Record in every score set what produced it, report a strict pass rate beside each criterion-based score, and allow an optional second judge from another model family
2. Keep a changelog listing only the changes that move scores, and leave the data as it is
3. Make the strict pass rate the headline score
4. Average two judges' verdicts
5. Change nothing: the suite hash and the Casebench version are enough

## Decision outcome

Chosen option 1, because comparability becomes a property of the data rather than of the repository's history, and both new numbers add evidence without hiding any.

- **What produced a score set.** Each score set starts with a header that holds:
  - the Casebench version and each metric's version;
  - the judge's provider, model and family ([0032](0032-provider-catalog-and-sdk-providers.md));
  - a hash of each judge prompt;
  - the corpus key;
  - for court-derived cases, the extraction models that wrote the answer keys.

  `casebench compare` lists every field in which two score sets differ. When a field that changes scores differs, it says the runs are not comparable on the metrics that field affects, and still shows the figures.
- **Strict pass rate.** For every task and metric whose cases carry criteria, the report adds the share of cases where every criterion passed: each positive criterion met and no negative one triggered. It has its own interval ([0028](0028-scores-baselines-and-intervals.md)) and sits beside the weighted mean, per reference source and approval state, as every figure does (rule 8). It is never folded into the mean and never shown alone.
- **Second judge.** `judges:` in `casebench.yaml` may name a second judge, which must be of a different model family from the first; `init` refuses two of the same family. Both judges' verdicts are kept.
  - A criterion or citation counts as passed only when both judges pass it.
  - Every disagreement is listed in the report and goes to the workbench review queue, where a lawyer's verdict replaces both judges' verdicts (rule 6).
  - The report gives the two judges' agreement per metric.

  With one judge, nothing changes.
- **Writing criteria.** The authoring template and the workbench ask for one checkable point per criterion, written as "Passes if … Fails if …". `casebench validate` warns about a criterion without that form; it does not refuse it.

### Consequences

- Good, because a reader can tell from two score sets alone whether their figures can be compared, without the repository's history.
- Good, because a weighted score of 0.9 no longer hides that the answer missed something material in most cases.
- Good, because judge errors become visible as disagreements, and those are what lawyers review first.
- Bad, because a second judge doubles judge calls; the dry run counts them, and it is off by default.
- Bad, because "both judges pass" is stricter than either judge alone, so scores with two judges are not comparable to scores with one; the score-set header says which.

## Why not the others

- A changelog alone: it serves only readers who run from the repository and compare commits, not a team comparing two runs from installed packages; the score-set header covers both.
- Strict pass as the headline: one number per suite is what rule 8 forbids, and a strict rate alone hides how close the answers came.
- Averaging two judges: a criterion is not half passed, and an average hides exactly the disagreements a lawyer should see.
- Changing nothing: a new judge prompt or model would move every judge-based score with no trace in the data.

## Revisit when

- Drafting tasks with several output documents arrive: each criterion may then name the document it is checked against, so the judge reads only that one.
- Measured agreement between the two judges is high enough, over enough cases, that the second judge stops changing verdicts.

## More information

Checked on 2026-10-13 in the code:

- `RunInfo` (`casebench/runs/log.py`) holds the suite id and hash, the target and the Casebench version.
- `Score` (`casebench/core/score.py`) holds `metric_version`.
- The judge memo (`casebench/judge/memo.py`) keys each reply on provider, model and prompt, but none of these is stored with the scores.
