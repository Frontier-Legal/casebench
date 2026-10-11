---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# Record architecture decisions in MADR 4

## Context and problem statement

Casebench is an open-source project that firms and vendors are asked to trust as a yardstick. A reviewer who cannot see why a choice was made has to either take it on faith or re-argue it in a pull request. The design started in private notes, and a public project whose reasons are private cannot be contributed to.

## Considered options

- MADR 4, one Markdown file per decision under `docs/decisions/`
- Nygard's original five-section format
- A single design document that is edited in place
- GitHub Discussions or issues as the record

## Decision outcome

Chosen option: "MADR 4, one file per decision", because it names the options weighed and the consequences, which is what a later reader needs, and it is plain Markdown in the repository, so it versions with the code and survives a move off GitHub.

Every record also carries a "Revisit when" section, which MADR does not require. A decision without a trigger to reopen it either never gets revisited or gets re-argued at random.

### Consequences

- Good, because a pull request that adds a dependency, changes a public interface or changes a storage format links one record, and the review discusses that record instead of restarting the debate.
- Good, because superseding is explicit: an old record stays, marked superseded, with a link forward.
- Bad, because writing a record costs a contributor some minutes before the code. The pull request template asks for it so the cost is visible rather than surprising.

## Revisit when

The number of records makes the index hard to scan, or contributors consistently skip records because the template is too heavy.

## More information

- [MADR](https://adr.github.io/madr/)
- [Michael Nygard, Documenting architecture decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- The design documents in [../design/](../design/) describe the system; the records here say why it is shaped that way.
