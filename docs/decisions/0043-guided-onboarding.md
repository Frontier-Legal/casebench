---
status: accepted
date: 2026-10-14
decision-makers: Casebench maintainers
---

# Onboarding detects first, asks last, and finds keys in the project's .env files; Rich draws it

Amends [0030](0030-set-up-here-run-there.md) (what `casebench init` asks and shows), [0040](0040-init-reads-the-code.md) (what the code scan reports) and [0032](0032-provider-catalog-and-sdk-providers.md) (where a model's key is read from). Adds Rich as a dependency.

## Context and problem statement

The first real `casebench init` on a production legal agent's repository (1,454 Python files, 2026-10-14) was not usable:

- the scan printed about 60 lines of HTTP clients and model names from tests;
- it offered several hundred functions, most of them tests, as the agent's entry point, in one comma-separated line;
- it stopped the corpus question because the key was in a `.env` file, not in the shell, while the repository has many `.env` files.

Each question was plain text, typed paths were the norm, and a refused step meant starting again. A legal team evaluating its agent would leave before the first run.

A first run that people finish follows a short list of practices:

- detect before asking;
- two lanes, one that takes what was found and one that asks every part;
- summaries rather than logs;
- pickers rather than typed values;
- say where each key came from;
- check with a real call, and on a failure loop back to the step rather than start again;
- review before writing, with re-runs that repair.

## Considered options

1. A guided flow on Rich (for logo, steps, notes, spinners, review) and questionary (for pickers, already a dependency), with a plain fallback when there is no terminal
2. A full-screen Textual application
3. Keep plain Click prompts and only shorten the output

## Decision outcome

Chosen option 1, because it gives the look and flow of the tools studied while staying a line-by-line command. It works over SSH, in CI and in tests, where a full-screen application does not.

- **The flow.**
  - **Opening:** a logo, then a reading of the project with a spinner, shown as a summary with one line per kind: suggested agent function, model clients, keys found.
  - **Lane:** "Quick start (recommended)" uses what was found and asks only what detection could not answer. "Custom" asks every part.
  - **One step per part:** target, corpus, judge, capture routes; extraction only in Custom. Each step has its answer preselected where one was found.
  - **Live checks:** a corpus is checked with one search and fetch, and the judge answers one question. A failure says why in plain words and offers retry, another choice or skip; the run never restarts.
  - **Review:** a box with what `casebench.yaml` will hold, and a confirmation before it is written.
  - **Close:** the next two commands to run.
  - **Interruption:** Ctrl-C at any point writes nothing.
- **Pickers.** A question with options is a type-to-filter list. The agent function is picked from the scan's candidates, never typed, though "another function…" lets a path be typed. Without a terminal, a picker prints numbered options and reads a number, so flags, pipes and tests keep working.
- **Nothing is decided by a name.** No step ranks or picks anything because a name looks like a question, a key or a field. What is offered comes from structure and contracts:
  - **The scan.**
    - It skips test files by pytest's own file patterns (`test_*.py`, `*_test.py`, `conftest.py`) and suggests no private function (a name starting with `_`).
    - An entry point is a public function a Python target can call with a case's inputs, `core.case.INPUTS`, and that reaches a model call through the project's own functions. Functions are told apart by file and name, so two files' `answer` are both offered. They are listed in file order, and in Quick start a single one is taken.
    - An HTTP client is listed only when the code gives it a base URL. A capture route is named after the full host it stands in front of, such as `api-fireworks-ai`.
    - The summary has one line per kind; the full detail stays available with `casebench init --details`.
  - **A corpus's fields** are picked from a real search and fetch: each field is offered with its path and a sample value, in both lanes. A script names them with flags. The only suggestions are structural: the id is the field whose value is the fetched id, the text is the longest string and a date is a value in ISO form.
  - **Keys** are matched by the exact name the config expects, and otherwise picked from a file's names.
- **Keys in .env files.** A key named in the config is read from the environment first. When it is not set there, Casebench looks for that name in the project's `.env` files: files named `.env`, `.env.*` or `*.env` (such as `env/eval.env`), except placeholder files such as `.env.example` or `eval.env.example`, outside virtual environments, `node_modules` and hidden folders.
  - **One file has it:** that file is used, and the step says so (`✓ CORPUS_API_KEY in research/.env`).
  - **Several files have it with different values:** the user picks the file, each shown with a masked preview (first and last four characters).
  - **None has it:** the user picks a `.env` file, then a key from the names in it. The config then refers to that name.

  `casebench.yaml` gains `keys`, a map from a variable's name to the file it is read from, never its value. Every command reads exactly those variables from those files, when the environment does not already set them. No other line of a `.env` file is read into the process.
- **Re-runs.** On a folder that has a config, `init` runs the repair pass of [0042](0042-upgrade-in-place.md) in the same look.
- **Rich.** Rich 15 (MIT) draws the logo, the steps, notes, spinners and the review box. It writes plain text, without colour or cursor control, when the output is not a terminal.

### Consequences

- Good, because a project like that first one is set up with a handful of Enter presses: the agent function, the corpus key and the judge's key are found or picked, not typed.
- Good, because keys stay where the team keeps them, and the config says where each one is read from.
- Bad, because Casebench now reads named variables from files in the project; it reads only the names the config lists, and never writes a value.
- Bad, because a new dependency, Rich, is added; it is widely used, pure Python and has no dependencies beyond `markdown-it-py` and `pygments`.
- Bad, because Esc does not step back in a questionary prompt, unlike the tools studied; Ctrl-C ends the run without writing, and every step can be redone by running `init` again.

## Revisit when

- Users ask for a back key in the flow; that needs a full-screen interface (option 2).
- A team keeps keys in a secret manager rather than `.env` files; a key could then name the command that prints it.

## More information

- [Rich](https://github.com/Textualize/rich) and [questionary](https://github.com/tmbo/questionary).
