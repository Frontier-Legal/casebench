---
status: accepted
date: 2026-10-15
decision-makers: Casebench maintainers
---

# An engineer pushes runs and suites to a team server, invites lawyers, and pulls their decisions back; the server never scores

Adds to [0005](0005-cloud-never-computes-a-score.md) (the cloud never computes a score), [0050](0050-the-review-queue.md) (run folders stay the truth) and [0058](0058-the-team-server.md) (the team server). Follows the workbench design ([workbench.md](../design/workbench.md), "What crosses the line").

## Context and problem statement

Lawyers cannot reach an engineer's laptop. The team server ([0058](0058-the-team-server.md)) reads runs and suites from its own folders, so today someone copies files onto it. A lawyer should be in the queue minutes after the engineer's run finishes. Their approvals and verdicts have to come back to the engineer's machine, where CI scores. The agent, the corpus, full decision texts and keys must not leave that machine.

## Considered options

1. `casebench push`, `invite` and `pull` in the core CLI, talking to the team server's sync routes with an API key. The server writes what it receives into the same run and suite folders the workbench reads.
2. A shared database both sides write to.
3. Copying run folders to the server by hand or with rsync.

## Decision outcome

Chosen option 1, because run folders stay the truth on both sides ([0050](0050-the-review-queue.md)). The server only stores and shows what the runner computed ([0005](0005-cloud-never-computes-a-score.md)), and the engineer needs nothing but a URL and a key. Option 2 makes CI depend on a server. Option 3 sends whatever the folder holds, including the judge's replies, and needs shell access to the server.

- **Where.** `casebench.yaml` names the server: `cloud: {url: https://casebench.firm.example}`. Its API key, one an admin created with the engineer role ([0058](0058-the-team-server.md)), is read from `CASEBENCH_CLOUD_KEY`, from the environment or a `.env` file, and never written. The server's host joins the hosts the network allow-list permits ([0046](0046-the-perimeter.md)).
- **What crosses the line.**
  - **Sent:**
    - each suite the pushed runs ran: its cases with their evidence excerpts, and its manifest;
    - each run's `run.json`, results, score sets, `report.json`, `reviews.jsonl` and `preferences.jsonl`.
  - **Never sent:**
    - the judge's kept replies (`judge.jsonl`), which hold the text the judge read;
    - the corpus and its cache, and full decision texts;
    - the agent's code, `casebench.yaml`, `.env` files and keys;
    - any other file in a run's folder.
  - **Steps only with `--traces`.** Without it, each result goes up without its steps. With it, steps go up as ids and numbers only: kind, name, model, provider, tokens, times, durations, document ids and sizes. Tool arguments, notes and message content are never sent.
  - The server accepts only these files and refuses any other path.
- **Push is idempotent.**
  - A run is identified by its id. Pushing it again rewrites what changed and leaves the rest, so the server shows one run.
  - Reviews and preferences are merged line by line, so a push never removes a verdict lawyers gave on the server.
  - A suite is identified by its id. The server records the hash the engineer last pushed. When lawyers have changed the suite on the server since, approving drafts or editing cases, a push of a different version is refused until the engineer pulls.
- **Invite.** `casebench invite EMAIL --role ROLE [--name NAME]` asks the server to invite the person ([0058](0058-the-team-server.md)). An engineer, signed in or with a key, invites viewers, reviewers and editors; only an admin invites an engineer or an admin. API keys stay below admin. The email says how many items wait in the queue for that role, and about how long they take: two minutes for an answer to review, three for a court draft or a change to approve. One sign-in from the email opens the queue.
- **Pull.** `casebench pull` brings back:
  - each suite the server has and this machine has too, written into its local folder when the server's version differs, so drafts lawyers approved are approved locally;
  - each run's reviews and preferences, merged into its local folder, so lawyers' verdicts replace the judge's in the report and the gate ([0047](0047-the-judge-rests-on-evidence.md)).

  Pull never changes a score: the next run, or `casebench gate`, computes on what lawyers approved.
- **The server never grades.** It has no route that scores, re-scores or calls a judge, and it keeps the score sets exactly as the runner wrote them. A test checks both.

### Consequences

- Good, because a lawyer reviews a run minutes after it finishes, and their decisions reach CI with one command.
- Good, because the line between what is sent and what stays is in code: a list of files, and steps reduced to numbers.
- Bad, because a suite changed on both sides at once needs a pull before the next push.
- Bad, because a pushed suite carries its evidence excerpts, passages a provider's terms may limit; a team that may not share them keeps reviewing locally.

## Revisit when

- Teams want the server to start runs (scheduled runs, R2).
- Lawyers need the full decision on the server, where the provider's terms allow it.

## More information

- What crosses the line: [workbench.md](../design/workbench.md).
