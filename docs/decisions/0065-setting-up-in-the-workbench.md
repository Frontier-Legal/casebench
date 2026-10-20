---
status: accepted
date: 2026-10-20
decision-makers: Casebench maintainers
---

# Setup starts in the workbench: init opens it, a guide walks a first-time user through each part, and jurisdictions and models get their own pages

Adds to [0043](0043-guided-onboarding.md) (guided onboarding), [0063](0063-the-workbench-sets-up-and-runs.md) (the workbench edits casebench.yaml) and [0036](0036-several-corpora.md) (several corpora routed by jurisdiction). Follows [0024](0024-no-jurisdiction-adapters.md): a jurisdiction is data, never code.

## Context and problem statement

After `casebench init` the workbench is one command away, but nobody is told to open it, and a first-time user meets a review queue that is empty. Adding a second country or swapping the judge for another model means knowing which `casebench.yaml` section to edit, or reading the Settings page's raw fields: connector options, JSONPaths, provider options. A lawyer or a product person cannot tell which part is which, and an engineer who would rather click than type has to learn the command line first.

## Considered options

1. `casebench init` opens the workbench when it finishes, or right away for a person who chooses to set up in the browser. The workbench gains a guide for a first-time engineer, a Home page that says what is set up and what is next, and two pages that say in plain words what each part is for: Jurisdictions and Models. Each saves the same `casebench.yaml` sections the Settings page saves.
2. The same pages, without changing init: the user starts `casebench ui` when they want it.
3. A richer terminal wizard, with no new pages.

## Decision outcome

Chosen option 1, because the browser is where both a lawyer and an engineer can see what each part does, and opening it from init costs a person nothing. Option 2 leaves the pages undiscovered. Option 3 keeps out everyone who does not use a terminal.

- **init opens the workbench.** At a terminal, `casebench init` starts the workbench when it has written the file, and the browser opens on Home. Its first question offers a third way, "In the browser": it reads the project, writes nothing, and opens the guide. Without a terminal, as a coding agent or CI runs init, it never starts a server, since a server that never returns would hang them; `--ui` and `--no-ui` decide either way. When the workbench's usual port is taken, the operating system names a free one.
- **The guide.** An engineer at a workbench on their own machine with no `casebench.yaml` is guided through four steps, each saving its own section as it goes: the agent (picked from the functions the code scan found, or an HTTP endpoint, or a command), jurisdictions and their sources, the judge, and a check. A step can be skipped; leaving and coming back resumes from the file.
- **Home.** For an engineer, Home lists each part of the setup with whether it is done, what is missing, and the button that does it, then the first run and the review queue. It is where the workbench opens until the setup is complete.
- **Jurisdictions.** Each jurisdiction shows the sources that cover it, whether they hold decisions, statutes or both, and a test search. Adding one is a country picked by name, then a source, offered in the order sources usually come: a document API (a legal data provider's or the firm's own), an MCP server, a provider's profile, a source already connected, and last a folder of sample files for trying Casebench out. For an API or an MCP server the workbench makes one search and shows the first result field by field, with its values; the person picks which field is the id, and may pick the citation, type and passage. One document is then fetched and its id, text and date suggested from their values, as `casebench corpus add` does at a terminal, so nobody writes a JSONPath. Nothing is guessed from a field's name ([0043](0043-guided-onboarding.md)). A source that answers but holds no document it can read does not pass its test, here or in `casebench check`. Country names come from the browser's own list (`Intl.DisplayNames`); the codes come from Casebench's ISO 3166 list, so the page offers only codes the file accepts.
- **Models.** Each model Casebench calls is a card that says what it does: the judge, a second judge from another family, and the two extraction models. Changing one is picking it from the model catalog; its key can be set and the model tested on the card, alone. A second judge of the judge's own family is refused, as a run refuses it ([0035](0035-comparable-and-strict-scores.md)).
- **A reviewer's first visit.** A person who has just named themselves as a reviewer is shown, once, how reviewing works: the evidence beside the answer, the judge's suggestion filled in, one key per verdict.
- **Nothing new is stored.** Every page writes `casebench.yaml` through the Settings page's sections ([0063](0063-the-workbench-sets-up-and-runs.md)), so the command line and CI read what the browser wrote.

### Consequences

- Good, because a new country is a few choices in a dialog and no code, which is what [0024](0024-no-jurisdiction-adapters.md) promises.
- Good, because a person who does not read YAML can tell which model does what and change it.
- Bad, because init at a terminal no longer returns until the workbench is stopped; `--no-ui` keeps the old behaviour.
- Bad, because capture routes, the network allow-list and a connector plugin's options stay on the Settings page and the command line.

## Revisit when

- A setup the guide does not cover becomes common, such as capture routes: then it gets its own step.

## More information

- `Intl.DisplayNames`: [ECMA-402](https://tc39.es/ecma402/#intl-displaynames-objects), supported by every current browser.
- The codes: `casebench/core/jurisdiction.py`, from Unicode CLDR ([0036](0036-several-corpora.md)).
