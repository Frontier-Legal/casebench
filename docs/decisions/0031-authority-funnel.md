---
status: accepted
date: 2026-10-12
decision-makers: Casebench maintainers
---

# The authority funnel follows each court authority through the captured steps

## Context and problem statement

A wrong answer does not say where the right authority was lost: the search never found it, the reranker dropped it, it never reached the model, or the model ignored it. Asking a model which step failed finds the step 14% of the time ([Who&When](https://arxiv.org/abs/2505.00212)), so the blame has to come from what the steps saw. Statute and precedent cases know the court's authorities as corpus documents ([0029](0029-statute-and-precedent-scores.md)), and the captured steps carry document ids ([0019](0019-recording-proxy.md), [0022](0022-config-named-functions.md), [0023](0023-otlp-trace-intake.md)).

## Considered options

- Follow each court authority through the steps by document id, with a fixed label for the first stage it fails
- Ask the judge which step lost the authority
- Show the steps and leave the reading to the user

## Decision outcome

Chosen option: "follow each authority by document id", because every label is a lookup anyone can repeat from the run log.

- **Stages.** For each document the court relied on: *retrieved* when a retrieval, rerank or document step returned its id; *kept* when a rerank step returned it, checked only when a rerank step was captured; *read* when its id is in the request of a model call; *cited* when the answer cites it. The first stage it fails gives its label: `retrieval_miss`, `rerank_drop`, `not_in_context`, `ignored_authority`.
- **Read.** The capture marks, on each model call, the ids of documents the case's other steps returned that appear in that call's request as a whole word. An agent that puts a document's text before the model without its id shows as `not_in_context`; the label says the id was missing, and the report says how read was decided.
- **Ids.** The funnel compares the ids the steps carried with the corpus's. A route's or function's JSONPath picks the field that holds the corpus id when the agent's own ids differ.
- **Ungrounded.** A citation in the answer that resolves to a corpus document no step returned is `ungrounded`: written from the model's memory, right or wrong.
- **Cited and ungrounded need the judge and the corpus**, which resolve the answer's citations ([0029](0029-statute-and-precedent-scores.md)). The judge's replies are already in the run's `judge.jsonl` when a statute or precedent metric ran, so the funnel asks nothing new. Without a judge, the funnel stops at read and says so.
- **A black box.** A case whose steps carry no document ids gets "no diagnostic possible", and the suite funnel counts only the cases that have ids. With none, it says "no diagnostic possible" instead of a number.
- **Report.** The terminal shows how many court authorities survive each stage, the count of each label, and the ungrounded citations; `report.json` holds every case's authorities with their stages and label. The funnel never changes a score.
- **Characterised**, whether a cited passage supports the claim, is the citation-integrity metric's label ([0026](0026-judge-and-citation-checks.md)) and is not repeated in the funnel.

### Consequences

- Good, because "the right decision was retrieved in 81% of cases and reached the model in 52%" points at the reranker or the context budget, not the model.
- Bad, because read depends on the agent putting ids in front of the model; an agent that strips them shows `not_in_context` for authorities the model did see.
- Bad, because ids must be the corpus's; an agent with its own ids needs the JSONPath that maps them.

## Revisit when

Agents that strip ids are common enough that read should also match document text, or users need the funnel for authorities a lawyer listed rather than a court.
