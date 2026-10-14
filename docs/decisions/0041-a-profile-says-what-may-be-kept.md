---
status: accepted
date: 2026-10-14
decision-makers: Casebench maintainers
---

# A profile says what a provider's terms let Casebench keep on disk, and the cache follows it

Amends [0033](0033-data-provider-profiles.md) (its "Revisit when a provider's terms forbid the local cache") and [0025](0025-corpus-connectors.md) (every fetched document is kept).

## Context and problem statement

Casebench keeps every document it fetches on disk, and every search of a provider that charges per search ([0025](0025-corpus-connectors.md), [0033](0033-data-provider-profiles.md)). 0033 assumed, without checking, that commercial providers' terms allow this, and named a provider whose terms forbid it as the event to revisit. Terms differ: some licences let a customer keep texts, some only let them display texts, and some let a customer keep search results but not full texts. A team should not have to read the code to learn whether Casebench honours its provider's terms, and the provider is the one who knows them.

## Considered options

1. A profile, and the corpus block it writes, say what may be kept: `keep: [documents, searches]`, a subset, or none; the cache keeps only that
2. One switch that turns the cache off for a corpus
3. Leave the cache as it is and document the assumption

## Decision outcome

Chosen option 1, because documents and searches are licensed separately, and a provider can state its own terms in the file it already maintains.

- **What a profile says.** `keep` lists what the provider's terms let a customer keep on disk: `documents` (fetched texts and their fields) and `searches` (what a search returned). Leaving it out keeps the behaviour of 0025 and 0033: documents always, searches when the provider charges per search. `keep: []` keeps nothing.
- **What the corpus does.** The corpus block written from a profile carries the same `keep`, and a user can set it on any corpus. A document not kept is fetched each time it is read, and a search not kept is made each time it is asked; nothing of it is written under `.casebench/corpus-cache/`.
- **What the user is told.** Adding a profile that keeps less than the default says what will not be kept and what that costs: every read is a fetch, every search a search.

### Consequences

- Good, because a provider whose terms forbid a local copy can be connected without breaking them.
- Bad, because a corpus that keeps nothing pays for every fetch and search on every run and re-score, and a re-score is no longer free of corpus calls; the dry run's cached counts stay at zero for it.

## Revisit when

A provider's terms allow keeping texts only for a period; `keep` would then need a lifetime.

## More information

- [0033](0033-data-provider-profiles.md): "Assumed and not checked: that commercial providers' terms allow a local cache of full texts".
