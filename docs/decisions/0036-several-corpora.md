---
status: proposed
date: 2026-10-13
decision-makers: Casebench maintainers
---

# A setup connects several corpora by name; citations go to the corpus that covers their jurisdiction

Amends [0025](0025-corpus-connectors.md) (one corpus per config), [0026](0026-judge-and-citation-checks.md) (a citation no corpus resolves is fabricated) and [0033](0033-data-provider-profiles.md) (the corpus question asks once).

## Context and problem statement

`casebench.yaml` holds one `corpus:`. Teams that serve several countries already use one data provider per jurisdiction, and add more as they enter new ones. One setup must therefore reach several providers, and run one suite across them.

Four things break with more than one corpus:

- **Ids collide.** Two providers can both have a document `101`. Answer keys, run logs and the authority funnel store bare ids today.
- **Cost.** Searching every provider for every citation multiplies paid searches ([0033](0033-data-provider-profiles.md)).
- **Wrong labels.** A citation to a country no connected corpus covers is unresolved, so it would be labelled `fabricated`, though Casebench simply cannot check it.
- **Ambiguous commands.** Case generation and `corpus check` would not know which store they read.

The formats are at 1.0 and not yet released ([0034](0034-versioned-formats.md)). A change to how ids are written fits now, and would need a major version later.

## Considered options

1. Named corpora, each listing the jurisdictions it covers; ids qualified by corpus name; each citation routed to the corpora that cover its jurisdiction, and labelled unchecked when none does
2. One federated connector that fans every call out to several stores behind one corpus
3. One config per jurisdiction, run separately
4. Several corpora with bare ids, refusing a run when two stores return the same id

## Decision outcome

Chosen option 1, because it is the only one where a mixed-jurisdiction suite runs once, each citation costs searches only where it can be found, and a citation nobody can check is not called fabricated.

- **Config.** `corpora:` maps a name to a corpus block. The name is lower-case letters, digits and hyphens.

  ```yaml
  corpora:
    no-statutes: {connector: http, jurisdictions: [NO], profile: ..., options: {...}}
    tr-courts:   {connector: mcp,  jurisdictions: [TR], profile: ..., options: {...}}
  ```

  The existing `corpus:` stays as the form for one store, and is read as `corpora: {corpus: ...}`. `jurisdictions` replaces the single `jurisdiction` filter; a corpus that lists none covers every jurisdiction. A profile's own `jurisdictions` fill it in.
- **Ids.** Every document id Casebench stores is qualified: `<corpus name>:<id as the provider gives it>`. This applies to a fact's `document_id`, run logs, scores and the funnel. The provider is only ever sent the part after the first colon. The cache already keeps each corpus apart.
- **Routing a citation.** When the judge lists citations, it also names the jurisdiction each one belongs to, where the citation shows it.
  - A citation is searched only in the corpora that cover that jurisdiction.
  - Where the judge cannot tell, it is searched in the corpora that cover the case's jurisdiction (`provenance.jurisdiction`).
  - Where the case has none, it is searched in every corpus.
  - Candidates from several corpora reach the judge together, each marked with its corpus, so the judge picks among them as it does now.
- **Unchecked, not fabricated.** A citation whose jurisdiction no connected corpus covers gets the new label `unchecked`. It is counted and reported apart from `verified`, `misgrounded` and `fabricated`, and never counts against the answer. `fabricated` keeps its meaning: a corpus that covers the jurisdiction was searched and holds no such document.
- **The agent's own ids.** Retrieval spans carry the ids the agent's store uses. A bare id in a span matches a qualified gold id when exactly one corpus could hold it, and `doc_id` mapping ([0031](0031-authority-funnel.md)) may name the corpus when it is ambiguous.
- **Commands.**
  - `casebench corpus add http|mcp|profile` takes `--name`. Without it, the name is the profile's id, or else the store's host, and the user may edit it. Adding to a config that already names corpora adds one more, and never replaces one.
  - `corpus check`, `extract` and `generate` take `--corpus NAME`. With one corpus they need none; with several and no name, they say which names exist.
  - `init` asks the corpus question again after each source is added ("Connect another source?"), until the user answers "that's all".
- **Cost.** `casebench run --dry-run` counts searches per corpus, so a metered provider's share is visible before a run.
- **Self-check guard.** No corpus may be the target ([0025](0025-corpus-connectors.md)); every one is checked.

### Consequences

- Good, because a team with one provider per country connects them all in one setup, and runs one suite across them.
- Good, because a citation to a country nobody connected is reported as unchecked: the report says what Casebench could not see, instead of blaming the answer.
- Good, because routing keeps paid searches to the providers that can hold the citation.
- Bad, because ids in stored files gain a prefix. Nothing is released yet; after the first release, this is part of format 1.0.
- Bad, because routing trusts the judge to name a citation's jurisdiction. A wrong guess sends a citation to the wrong corpus, where it is not found. The report counts citations routed by the judge, by the case and to all corpora, so a high miss rate after routing is visible.
- Bad, because a single store keyed `corpus:` now writes ids as `corpus:<id>`.

## Why not the others

- A federated connector: it hides which provider answered, multiplies every paid search, and still returns colliding ids.
- One config per jurisdiction: it cannot run a case whose answer cites two countries' law, splits one suite into several reports, and leaves cross-border citations unverifiable.
- Bare ids with a refusal on clashes: two independent providers collide by accident, so runs would fail for reasons the user cannot fix.

## Revisit when

- The judge's jurisdiction guesses route a measurable share of resolvable citations to the wrong corpus: route by search across all covering corpora instead.
- A provider needs Casebench to send it a qualified id, or ids that contain the separator.

## More information

Checked on 2026-10-13 in the code: a single `corpus` is read by `casebench/runs/scoring.py`, `casebench/suites/cli.py`, `casebench/extract/cli.py`, `casebench/corpus/cli.py`, `casebench/setup/checks.py` and `casebench/runs/dry_run.py`. `Resolver` (`casebench/judge/resolve.py`) searches one corpus. `CitationLabel` (`casebench/core/score.py`) has `verified`, `misgrounded` and `fabricated`.
