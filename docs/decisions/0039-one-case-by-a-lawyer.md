---
status: accepted
date: 2026-10-14
decision-makers: Casebench maintainers
---

# A lawyer writes one case at a time, from a decision found by topic or by hand, and approves it

Adds to [0002](0002-evaluation-case-model.md) (the case model) and [0027](0027-answer-keys-from-decisions.md) (answer keys from decisions).

## Context and problem statement

Until now cases came only from bulk extraction: two models read many decisions and their agreement decides which keys are kept ([0027](0027-answer-keys-from-decisions.md)). That suits a team building a suite, but it is slow, it costs, and it leaves every case a draft until lawyers approve it. A lawyer who wants to test one point of law now has no way in. The lawyer knows the point, can recognise the right decision in a list, and can correct a draft quickly. What the lawyer cannot do is type JSON, JSONPath or a docket format for each country.

## Considered options

1. `casebench case new`: a topic, a search, a decision picked from a list by its citation, one model's draft, the lawyer's edits, and an approved case added to a named suite; `--manual` when there is no corpus or no decision covers the point
2. A template file the lawyer fills in and `casebench validate` checks
3. Wait for the workbench (R1)

## Decision outcome

Chosen option 1, because the lawyer answers questions in their own words and never sees a format, and the case is approved by the person who wrote it.

- **From a topic.** `casebench case new` asks for a topic and searches the corpus for court decisions with it, using the corpus's filters for decisions ([0037](0037-match-by-the-corpus-description.md)). It lists as many results as the judge is shown to match a citation (`candidates`, [0026](0026-judge-and-citation-checks.md)), each by its citation as the corpus gives it, else by court, date and id. The lawyer picks one.
- **One draft.** The first extraction model, or the judge when there is none, at its configured settings ([0038](0038-model-settings-by-measurement.md)), reads the decision once and drafts a question, the facts without the ruling, the outcome, and the statutes and precedents the court relied on. The draft uses the extraction prompt's rules: every quote is checked against the decision, and one that is not there is dropped. The command shows the model's time and cost with the draft.
- **The lawyer decides.** Each field is shown and can be changed. A fact the lawyer leaves as drafted keeps its quote from the decision as evidence; one the lawyer rewrites is recorded as the reviewer's. The case is saved only when the lawyer confirms it. It is `approved`, names the reviewer as the reference's author, and keeps `court` as its source with the decision as provenance.
- **By hand.** `casebench case new --manual` asks for the question, the expected answer, and the statutes and precedents, each as the lawyer writes them. The source is `lawyer`, and the evidence is the reviewer's own note.
- **How it is graded.** Each fact becomes one criterion, written by Casebench from the fact and never by a model ([0002](0002-evaluation-case-model.md)), such as "Passes if the answer concludes that the court reversed. Fails if it concludes otherwise or does not say." The judge grades them ([0035](0035-comparable-and-strict-scores.md)). Statutes and precedents are resolved to corpus documents as generated suites resolve them ([0029](0029-statute-and-precedent-scores.md)). A kind whose citations all resolve also gets the `statute` or `precedent` score, and with a corpus every case gets `citation_integrity`. A citation that does not resolve stays on the case as written.
- **Resolved later.** `casebench case resolve --suite DIR` resolves the citations still unresolved, once a corpus and a judge are configured, and adds the scores they allow.
- **The suite changes visibly.** A case joins the suite folder named, which is created when it does not exist. The suite is frozen again, so it gets a new hash, and the command prints the old and the new. A run records the hash it ran, the report prints it, and `report.json` carries it.

### Consequences

- Good, because a lawyer gets one approved case in minutes, and a team can mix such cases with generated ones in one suite; reports split them by source and approval.
- Good, because the grading criteria come from the lawyer's own facts, and the model only drafts.
- Bad, because one model drafts without a second to agree with; the lawyer's review takes the place of the agreement 0027 measures.
- Bad, because a topic search shows only the provider's first results; a lawyer who knows the decision can search for its citation instead.

## Revisit when

- The workbench (R1) gives lawyers a form for the same flow.
- Lawyers rewrite most drafted fields, which would mean the draft costs more time than it saves.

## More information

- The architecture's reference sources: [docs/design/architecture.md](../design/architecture.md).
