---
status: accepted
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

- **What produced a score set.** The first line of each score set says what produced it, and `report.json` carries a copy as `produced_by`:
  - the Casebench version;
  - each metric's version, and whether it reads the judge, the corpus or neither;
  - each judge's provider, model and family ([0032](0032-provider-catalog-and-sdk-providers.md)), and how many search results it matches a citation against;
  - a hash of each prompt the judge is asked;
  - each corpus's name and the key of its settings, the key that also names its cache;
  - for court-derived cases, the extraction models that wrote the answer keys, which each case's provenance records.

  `casebench compare` lists every setting in which the two runs' latest score sets differ, and marks the metrics each one moves as not comparable, still showing their figures:
  - a metric's version moves that metric;
  - the judge and its prompts move the metrics that read the judge;
  - a corpus moves the metrics that read the corpus;
  - other extraction models move every metric.

  A newer Casebench version moves no metric by itself, because a metric that scores differently gets a new version.
- **Strict pass rate.** For every task and metric whose cases carry criteria, the report adds the share of cases where every criterion passed: each positive criterion met and no negative one triggered. It has its own interval ([0028](0028-scores-baselines-and-intervals.md)) and sits beside the weighted mean, per reference source and approval state, as every figure does (rule 8). It is never folded into the mean and never shown alone.
- **Second judge.** `judges:` in `casebench.yaml` may name a second judge, which must be of a different model family from the first; `casebench run` refuses two of the same family before it sends anything. `judge:` stays the form for one. Both judges' verdicts are kept.
  - The first judge lists an answer's citations; each judge then decides each one on its own.
  - A criterion or citation counts as passed only when both judges pass it. A citation is verified only when both verify it, and an authority counts as the court's only when both judges name the same document.
  - Every disagreement is listed in the report and kept with its score in the run folder for review. A lawyer's verdict replaces both judges' verdicts (rule 6).
  - Lawyers review in the workbench ([workbench.md](../design/workbench.md)): an engineer sets Casebench up once, and lawyers then work in a browser, with no YAML and no terminal. The review queue is part of the Apache-2.0 workbench; hosting it for a team or as a service is the `ee/` side. Until the workbench ships, the disagreements wait in the run folder, and the strict "both judges pass" rule stands.
  - The report gives the two judges' agreement per metric.

  With one judge, nothing changes.
- **Grading criteria.** The `criteria` metric asks the judge about every criterion of an answer in one call, with the task, the facts the criteria come from and their evidence. The judge says whether each criterion is met and quotes the passage of the answer that decides it. With two judges, a criterion passes only when both pass it.
- **Writing criteria.** The authoring template and the workbench ask for one checkable point per criterion, written as "Passes if … Fails if …", and the judge's prompt follows that form where a criterion uses it. Casebench does not check the form: lawyers write criteria in their own language, and a check for English words would flag every criterion written in another.

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
