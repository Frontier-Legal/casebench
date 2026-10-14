---
status: accepted
date: 2026-10-14
decision-makers: Casebench maintainers
---

# An existing setup upgrades in place: init updates the config, old files are read as they are, caches carry over

Amends [0030](0030-set-up-here-run-there.md) (`init` refuses a folder with a config), [0034](0034-versioned-formats.md) (a file that names no format is refused) and [0025](0025-corpus-connectors.md) (what a corpus's cache is keyed by).

## Context and problem statement

A team that set Casebench up before a release has a `casebench.yaml`, cached documents and stored runs. With the release that adds search-result descriptions, model settings and code scanning, the only way to use them was to move `.casebench/` and the config aside, run `init` again and copy things back:

- `init` refuses a folder that has a config;
- a suite frozen before versioned formats is refused, and its document ids, written before ids named their corpus, no longer match the qualified ids a corpus returns;
- a score set written before score-set headers loses its first score when read;
- mapping a corpus's search results changes its options, which key its cache, so every document is fetched, and paid for, again.

A firm that has run Casebench will not do that for each release, and should not have to: everything needed to upgrade is on its machine already.

## Considered options

1. Upgrade in place: `init` on an existing setup offers only what is new and keeps the rest, old files are read and converted when loaded, cache keys ignore options that do not change documents, and `check` says what is out of date
2. A `casebench migrate` command that rewrites `.casebench/` and `casebench.yaml` into the current version
3. Release notes listing the manual steps

## Decision outcome

Chosen option 1, because the user's steps stay the same as for any day's work (`check`, `init`, `run --run-id`), and nothing is rewritten that does not have to be.

- **Init updates.** In a folder with a `casebench.yaml`, `casebench init` no longer refuses. It scans the code ([0040](0040-init-reads-the-code.md)) and the model catalog and offers only what the config lacks: a capture route for each client not yet routed, and each configured model's price and context window ([0037](0037-match-by-the-corpus-description.md), [0038](0038-model-settings-by-measurement.md)). It shows the changes and writes them only when the user agrees. Every setting already written stays as it is. The file is written again with its header; other comments in it are not kept, because PyYAML does not read them, and the file is meant to be in git, which shows the change.
- **Old files.**
  - A suite manifest that names no format was frozen before formats existed and has the 1.0 shape. It is read as 1.0, with a note, and its hash is checked as before.
  - A stored id that names no corpus was written before ids did ([0036](0036-several-corpora.md)). When the setup has one corpus, it is read as that corpus's id, in the court's authorities and in a case's source decision alike.
  - A score set's first line is skipped only when it is a header.
- **Caches.** A corpus's cache is keyed by its connector and the options that decide what a fetched document holds. `search_results` and `result_fields` only describe search results, so they are left out of the key, and mapping them keeps every document already cached. A search kept before them lists ids alone and is still read; its candidates are described from the stored documents.
- **Check.** `casebench check` also lists what a newer version can use and the setup lacks: a corpus whose search results are not described, a model with no price or context window. Each line names the command that fills it in. These are advice and do not fail the check.

### Consequences

- Good, because an upgrade is `uv sync`, `casebench check`, `casebench init` and, for a stored run, `casebench run --run-id`.
- Bad, because comments a user added inside `casebench.yaml` are lost when `init` updates it; it says so before writing.
- Bad, because a stored id is read as the one corpus's only while there is one; a setup with several corpora and ids from before 0036 has to regenerate those suites.

## Revisit when

- A format reaches its next major version: 0034's conversion on read then applies, and this record's read-as-1.0 rule ends with 1.x.
- Users keep comments in `casebench.yaml` often enough to need a round-trip YAML editor.

## More information

- [PyYAML](https://pyyaml.org/wiki/PyYAMLDocumentation) loads and dumps data, not comments.
