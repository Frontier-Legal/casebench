---
status: accepted
date: 2026-10-16
decision-makers: Casebench maintainers
---

# The workbench on an engineer's machine edits every setting in casebench.yaml, sets keys, and starts runs

Adds to [0042](0042-upgrade-in-place.md) (rewriting casebench.yaml), [0043](0043-guided-onboarding.md) (keys read from .env files), [0050](0050-the-review-queue.md) (the workbench), [0052](0052-golden-data-needs-a-second-editor.md) (what trying a question spends) and [0061](0061-the-first-ten-minutes.md) (the first run builds its suite). Follows [0005](0005-cloud-never-computes-a-score.md): the team server never scores.

## Context and problem statement

After `casebench init`, everything an engineer changes later happens in a text editor or a terminal: the judge, its model and price, the corpus, the daily limit for trying a question, the hosts a run may call, the keys, and every run. Nothing shows in one place which model does what, what it costs and what it may spend. An engineer who uses the workbench to read results also wants to change these settings and start a run there.

## Considered options

1. A Settings page in the local workbench that reads `casebench.yaml`, shows what each part is used for, and saves each section back to it, with an editor for the whole file. Keys are set into a git-ignored file. A Run page starts `casebench run` as a child process and shows what it prints.
2. The same, with settings in the workbench's database instead of `casebench.yaml`.
3. A read-only Settings page, with every change still made in the file.

## Decision outcome

Chosen option 1, because `casebench.yaml` stays the one place a setting lives: the command line, CI and the workbench read the same file, and a change shows in `git diff`. Option 2 splits the truth between a file and a database, so CI would run with settings nobody can see in the repository. Option 3 leaves the engineer in a text editor for every change.

- **What the page shows.**
  - The agent: how it is called, and the models it uses with their family and price.
  - The corpora: their connector, jurisdictions and options.
  - The judges and extraction models: provider, model, family, output limit, price and the key each one reads.
  - Spend and limits: the daily limit for trying a question, what it spent today, and what each recent run cost the agent and the judge.
  - The network allow-list, the capture settings, the team server, and each key with where it is read from.
  - `casebench check`, run on request, since it calls the agent, the judge and the corpus.
- **Saving.** A section is saved whole. The file is rewritten with its header, as `casebench init` rewrites it ([0042](0042-upgrade-in-place.md)), and other comments are lost, so the page warns before the first save of a file that has them. Every save is validated as `casebench` reads the file, and a save that does not validate changes nothing. The workbench then reads the new settings without restarting.
- **Models from the catalog.** A judge or an extraction model can be picked from the public model catalog, as init picks one ([0032](0032-provider-catalog-and-sdk-providers.md)), filling in its price, context window and options. The catalog is fetched only when the engineer opens the picker.
- **Keys.** The page never returns a key's value; it says whether each key is set in the shell, read from a file, or missing. A key typed into the page is written to the `.env` file `keys:` names for it when git ignores that file. Otherwise it goes to `.casebench/.env`, which `.casebench/.gitignore` keeps out of git, and `keys:` is pointed there. The workbench holds the key for its own calls at once ([0043](0043-guided-onboarding.md)).
- **Runs.** The Run page shows what a run will send and cost before anything is sent: `casebench run --dry-run` for a suite that exists, or the first run's extraction estimate when there is no suite yet ([0061](0061-the-first-ten-minutes.md)). Starting the run needs a confirmation. The run is `casebench run`, a child process of the workbench, so it behaves exactly as it does in a terminal: the same capture, resume and scoring. The page shows its progress live and can stop it. One run at a time.
- **Local only.** A team server neither edits its settings from the page nor runs anything, because the cloud never scores ([0005](0005-cloud-never-computes-a-score.md)). Its admin pages keep their own limits ([0058](0058-the-team-server.md)). Locally, these pages are for the engineering role; `casebench ui --role reviewer` does not show them.

### Consequences

- Good, because one file still holds every setting, and the page, the command line and CI agree.
- Good, because a run started from the page is the same run a terminal starts.
- Bad, because saving from the page drops comments the engineer wrote in `casebench.yaml`, other than its header.
- Bad, because a run started from the page stops if the workbench stops.

## Revisit when

- Engineers keep comments in `casebench.yaml` that saving would drop: then the file is edited in place, which needs a YAML library that keeps comments.
