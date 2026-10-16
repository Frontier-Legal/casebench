---
status: accepted
date: 2026-10-15
decision-makers: Casebench maintainers
---

# The first ten minutes: a demo with no key, a first run that builds its own suite, the search store named by init, a setup skill, and answers from a tool Casebench cannot reach

Adds to [0043](0043-guided-onboarding.md) (guided init), [0044](0044-onboarding-by-a-coding-agent.md) (setup from one prompt) and [0045](0045-setup-spends-little.md) (setup spends little).

## Context and problem statement

An engineer who has never heard of Casebench decides within minutes whether to keep it. Before this decision, seeing a report took a key, a corpus, an extraction, a generated suite and a run, each its own command. A team that uses a closed legal research tool through its web page could not evaluate it at all, because Casebench had nothing to call. And `casebench init` named the model SDKs a project uses but not the search store its agent retrieves from, which is where many wrong citations start.

## Considered options

1. A bundled demo; `casebench run` with no suite builds one; init names the search store from the lockfile and reads its searches; a skill in the repository; a CSV of questions out and answers back in.
2. A hosted demo page instead of a local one, and a separate `casebench quickstart` command for the first run.
3. Documentation only: a tutorial that walks through the existing commands.

## Decision outcome

Chosen option 1, because each part works on the user's machine with what they already have, and adds no command they must learn beyond `init`, `run` and `ui`. Option 2 sends the user's first impression to a server and adds a fourth command. Option 3 was the state before, and needed every command to be learned first.

### The demo

- `casebench demo` copies a bundled project into a new folder (a temporary one unless `--dir` names it), runs it, and opens the workbench on it. `--no-serve` stops after the run.
- The project holds a small suite, a folder corpus, the answers of a demo agent and the judge's replies. The cases, documents and answers are written for the demo and say so: the documents are not real decisions and the demo's verdicts are not legal advice.
- The demo agent answers from a file, as an echo target would. Some of its answers cite a document that says something else, or one that is not in the corpus, so the run has failures.
- The judge's replies are kept in the run's judge memo (`judge.jsonl`), keyed by the question as every run keys them. The demo copies them into its run before scoring, so every judge question is answered from the memo. They were written with the demo's cases, by a scripted judge, so they show what the workbench does, not what a model concludes.
- The demo's config allows no host outside the machine (decision 0046), so a missed memo entry stops the run rather than calling a model. A test runs the demo with every outside connection refused.
- The workbench lists the run's failed answers first, as its queue always does; each shows the cited passage beside the answer.

### The first run

- `casebench run` with no `--suite` uses the suite at `.casebench/suites/first`. When it is missing, the run builds it: it extracts answer keys from a sample of the corpus with the config's two extraction models, generates the suite from them, and then runs it.
- Before spending anything it prints what extraction would cost, from the estimate `extract --dry-run` gives, and how many cases the suite will send to the agent, and waits for a yes. `--yes` answers it; with no terminal and no `--yes`, the run stops and names the flag, as 0044 has every command do. The run's own judge calls are counted by `run --dry-run` once the suite exists, as for any suite.
- With several corpora, the first suite is built from the first one the config names; `casebench extract` and `generate` build a suite that mixes them.
- Each step keeps what it made. A second `casebench run` skips the extraction when its keys exist, the generation when the suite exists, and resumes the last run of that suite when it stopped before every case was answered.
- A corpus that cannot list its decisions is sampled through its `probe` search (0044).
- The sample size and the suite's size default to 20 decisions and 10 cases; `--sample` and `--cases` change them.
- Every run, first or not, ends with the command that opens it in the workbench.

### Init names the search store

- A project's lockfile or dependency list names its search store's client. For the Qdrant client, init says the store's searches are recorded as retrievals.
- A Python target's worker already sends every call through the proxy's follow path (0044). A followed call that no route or parser reads is now matched against each known search API by its path: Qdrant's `points/search` and `points/query`, and their batch forms. Its result ids become a retrieval step.
- Qdrant is the first known API because its Python client sends REST calls through httpx, which the worker redirects. A store whose client sends through another HTTP library, or through gRPC, is recorded through a route, as before.
- These ids are the store's own. When the store keeps a document's corpus id in a payload field, a route at the store's host with a `doc_ids` JSONPath reads that field instead, as any backend route does.
- `casebench.yaml` starts with a `# yaml-language-server: $schema=` line. It points at `.casebench/casebench.schema.json`, which init writes from the installed version's config model, so an editor checks the file against the version that reads it.
- The greeting init sends the agent (0045) now shows the agent's parsed answer and the kinds of calls recorded for it, such as one model call and one retrieval. A greeting cites nothing, so citations are shown by the first run, which pays for the judge.
- For an HTTP target, an agent that is already running, init sets a capture port and prints the variables to set in the agent's environment, as `casebench proxy env` does. For a Python or command target, Casebench starts the agent and sets them itself, and init says so.

### The setup skill

- The repository holds `skills/casebench-setup/SKILL.md` in the Agent Skills format. It tells a coding agent to run `casebench guide` and follow it, to answer from the repository what it can, to ask the user only where the corpus is and which judge to use, and to finish with `casebench run` and `casebench ui`.
- The README says how to install it for a coding agent that reads skills from a folder. The guide stays the single source of the steps; the skill only points to it, so the two cannot disagree.

### Answers from a tool Casebench cannot reach

- `casebench export --suite DIR --format csv` writes one row per case: its id, the repeat, each input the case gives, and an empty `answer` column.
- Someone pastes each question into the closed tool and writes its answer in the row.
- `casebench import answers.csv --suite DIR` reads the sheet as a run whose target is `offline`, scores it with the config's judge and corpus as `casebench run` scores a run, and prints the same report. A case left blank is reported as unanswered and is not scored; a row naming a case the suite does not have is refused with its row number.

### Consequences

- Good, because the first report needs no key and no data, and the second needs one config and one command.
- Good, because a closed tool is measured against the same suite and the same scoring as the team's own agent.
- Good, because the search store's retrievals appear in the authority funnel without a route written by hand.
- Bad, because the demo's memo must be rebuilt whenever a judge prompt changes. The demo's test fails when a reply is missing, so the change cannot ship unnoticed.
- Bad, because an offline run has no steps, so its harness view is empty.

## Revisit when

- A user reports that the demo's documents were taken for real decisions.
- A search store other than Qdrant, whose client sends through a library the worker redirects, is used by more than one team that sets Casebench up.

## More information

- [docs/design/open-source.md](../design/open-source.md), the first fifteen minutes.
- Qdrant's REST API, `POST /collections/{name}/points/search` and `POST /collections/{name}/points/query`, read on 2026-10-15.
- The Agent Skills format: a folder with a `SKILL.md` whose front matter holds a `name` and a `description`.
