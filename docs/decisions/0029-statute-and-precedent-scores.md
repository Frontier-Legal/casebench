---
status: accepted
date: 2026-10-12
decision-makers: Casebench maintainers
---

# Statute and precedent scores compare corpus documents; the judge's replies stay with the run

## Context and problem statement

A statute or precedent case asks the target which authorities decide a dispute, and the court's answer key lists the ones the court relied on, as the court wrote them ([0027](0027-answer-keys-from-decisions.md)). The target writes them its own way. Comparing the two strings fails on spelling and citation format, which differ by country ([0024](0024-no-jurisdiction-adapters.md)). Both sides have to become documents first: then the comparison is exact.

## Considered options

- Resolve the court's citations to corpus documents when the suite is generated, the answer's when it is scored, and compare document ids
- Resolve both sides at scoring time
- Ask the judge whether the answer's authorities match the court's

## Decision outcome

Chosen option: "resolve the key at generation, the answer at scoring, compare ids", because the key is resolved once and frozen with the suite, every run is compared against the same ids, and the judge never decides a score, only which document a citation means.

- **Resolving a citation.** The corpus searches for the citation as written and returns its first `candidates` results; the judge names the one the citation refers to, or none. This is the matching step of citation checks ([0026](0026-judge-and-citation-checks.md)), shared.
- **The key.** `casebench generate` resolves every statute and precedent of the keys it uses, with the judge and corpus in casebench.yaml, and stores the document id on the fact. A citation the corpus does not hold is dropped, and a case with none left is not made; the manifest counts resolved and dropped citations by type. An outcome-only suite needs neither judge nor corpus.
- **The answer.** The judge lists the answer's citations with a kind (`statute` or `decision`). Each one of the case's kind is resolved; one the corpus cannot resolve counts as a wrong authority.
- **Statute score.** Precision and recall of the answer's statute documents against the court's, and their F1 as the score. Labels: "missed statute" when recall is below one, "wrong statute" when precision is.
- **Precedent score.** The same over decisions: "missed precedent", "wrong precedent". A free-text answer does not rank its authorities, so recall at k and nDCG, which the design named, would measure an order the answer never meant.
- **Granularity.** Documents are compared at whatever the corpus holds: a whole statute in one corpus, an article in another. The report cannot be finer than the corpus.
- **The judge's replies stay with the run.** Every judge reply is kept in the run folder's `judge.jsonl`, keyed by provider, model and prompt. Re-scoring reads it back instead of asking again, so a re-score costs nothing and gives the same scores, and two metrics that list one answer's citations ask once.
- **Judge and target.** A model grading its own family's answers favours them. When a judge is configured, `casebench run` warns the user to pick a judge from another family than the target's model. It does not check this yet.

### Consequences

- Good, because a correct authority cited in another format still counts, and a score is a set comparison anyone can recompute from the ids in `report.json`.
- Bad, because a suite is tied to the corpus that resolved it: the same suite against another provider's ids needs regenerating.
- Bad, because generation now costs judge calls (one per court citation); the judge's tokens are the measure.
- Bad, because a corpus without statutes cannot make statute cases; generation says how many it dropped.

## Revisit when

Many court citations go unresolved for a corpus, or users need authorities ranked.

## More information

- [Panickssery et al., LLM Evaluators Recognize and Favor Their Own Generations](https://arxiv.org/abs/2404.13076)
