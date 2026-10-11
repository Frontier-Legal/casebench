---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# No jurisdiction adapters: the corpus resolves citations and models extract

Supersedes [0013](0013-built-in-jurisdictions-load-on-demand.md). Amends [0016](0016-plugin-contract.md): the adapter plugin kind is removed.

## Context and problem statement

Decisions 0006 and 0013 gave each country an adapter: code that parses its citation formats, finds where a decision's ruling starts and maps its courts to levels. Looking across jurisdictions shows that little of this is shared. A decision is cited by court and docket numbers in Türkiye, by parties and reporter page in the United States, by a neutral citation in the United Kingdom, by ECLI in the Netherlands, and by court, date and case number in Germany. The ruling comes last in a Turkish or French decision and first, as the Tenor, in a German one. Meanwhile two parts of the pipeline already call a model: two models extract each decision's answer key ([0002](0002-evaluation-case-model.md)), and a judge grades every answer that is not an exact label, because a citation can exist while the answer is still wrong.

## Considered options

- No adapters: models extract from decisions and answers, the corpus resolves citations to ids, and ids are compared
- Adapters as code per country, with parsers (decisions 0006 and 0013)
- Adapters as structured profiles per country, with fixed citation fields and layout markers

## Decision outcome

Chosen option: "no adapters", because a fixed per-country structure fits few countries, and the model calls it would save happen anyway.

- **Answer keys.** The two extraction models read a decision and return the ruling as one label from a shared vocabulary (`upheld`, `reversed`, `partly_reversed`, `remanded`, `granted`, `rejected`, `partly_granted`), the statutes and decisions it relied on exactly as written, and the facts written out without the ruling. Their agreement is measured per field.
- **Citations in answers.** The judge lists every citation an answer makes exactly as written. The corpus connector resolves each one to a document id, through the provider's own search. "Did the agent cite the right authority" compares ids. A citation the corpus cannot resolve is fabricated, whatever its format.
- **Statutes and provisions** are documents in the corpus like decisions, resolved the same way.
- **Court levels** come from the provider's metadata when it has them; a suite cannot be stratified by level otherwise.
- **Countries.** A corpus names its jurisdiction only to filter a provider that serves several. Any country works with no plugin. If agreement measured for a country is low, optional notes for its models may be added then, from that measurement.

### Consequences

- Good, because adding a country costs no code, and a provider serving many countries needs one connector.
- Good, because "no country in the core" holds without a plugin boundary to police.
- Bad, because citation matching depends on the corpus search resolving the many ways one decision is written; the dry run and the report show how many citations went unresolved.
- Bad, because extraction and grading cost model calls that parsers would not; the run log stores the judge's output so re-scoring does not repeat them.

## Revisit when

Measured extraction agreement for a jurisdiction stays low with notes, or corpus search resolves too few citations for a provider.

## More information

- [European Case Law Identifier](https://e-justice.europa.eu/topics/legislation-and-case-law/european-case-law-identifier-ecli_en)
