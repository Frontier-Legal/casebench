---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# The evaluation case is the unit: task, reference, metrics

## Context and problem statement

Legal AI is asked to do different jobs: answer a question, predict an outcome, find authorities, draft, edit, extract. The correct answer can come from a court decision, from a lawyer, or from expected fields. If each combination gets its own test format, a court-derived test and a lawyer-written one cannot share a suite or a report, and no result says where its answer key came from or whether a lawyer approved it.

## Considered options

- One case model with three independent axes: task type, reference source, metric
- A test format per court test type (outcome, statute, precedent), with lawyer cases bolted on
- Free-text expectations judged by an LLM, as most generic eval tools do

## Decision outcome

Chosen option: "One case model with three independent axes", because any task can be graded against any reference source with any metric, and the report can keep the axes apart.

A case is a task input, a reference, a list of metrics, tags, provenance and an approval state (draft or approved). A reference has two layers: facts, each tied to evidence (a passage in a decision, a lawyer's note, a corpus id), and criteria derived only from those facts. No criterion exists without the evidence it came from, so a model never writes the rubric it then grades against.

A suite is a frozen set of cases, stored as one case per line (`suite.jsonl`) beside a `manifest.json` with the suite id, a content hash, the Casebench version and the mix of reference sources. Generating the same suite id again yields the same cases in the same order.

Every score row names its task, metric, reference source and approval state. The report shows one table per task and metric, split by reference source, and never an overall accuracy figure.

### Consequences

- Good, because a firm can mix court-derived and lawyer-written cases in one suite and still read them apart.
- Good, because a published result can be reproduced from the suite id, the hash and the corpus snapshot.
- Good, because a finished run log can be re-scored with a newer metric without calling the target again.
- Bad, because the model is more general than the first release needs, and the extra fields must stay valid as tasks are added.

## Revisit when

A task type cannot express its reference as evidenced facts plus criteria, or a user needs a single combined score for a reason the per-source tables cannot answer.

## More information

- Weighted criteria use signed integer weights scored as the weighted sum of passed criteria over the sum of positive weights, clipped to 0 to 1, the scheme [PRBench](https://arxiv.org/abs/2511.11562) reports a judge-expert agreement of κ 0.603 for.
- [Inspect: Task = Dataset + Solver + Scorer](https://inspect.aisi.org.uk/scorers.html) and [lm-eval-harness task configs](https://github.com/EleutherAI/lm-evaluation-harness/blob/main/docs/new_task_guide.md) informed the declarative task type.
- [../design/architecture.md](../design/architecture.md) has the field-level model.
