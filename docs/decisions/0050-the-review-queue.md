---
status: accepted
date: 2026-10-15
decision-makers: Casebench maintainers
---

# The review queue: run folders stay the truth, a database keeps what people do, and one web app serves lawyers and engineers

Adds to [0005](0005-cloud-never-computes-a-score.md) (the cloud never computes a score), [0015](0015-suite-and-run-log-formats.md) (suite and run log formats), [0039](0039-one-case-by-a-lawyer.md) (one case by a lawyer) and [0047](0047-the-judge-rests-on-evidence.md) (the judge rests on evidence). Follows the workbench design ([workbench.md](../design/workbench.md)).

## Context and problem statement

Lawyers bill hours, so every verdict they give Casebench has to cost seconds, and the first screen has to be work to do. Today a lawyer's verdict goes through `casebench review criterion` at a terminal, and a court draft is approved only by writing a new case with `case new`. The workbench design chose FastAPI, React and a database. It left open which holds the truth: the run folders and suites that `run`, `report`, `gate` and re-scoring read, or the database. It also left open how one screen serves a lawyer, who must never see spans, tokens or JSON, and an engineer, who needs them.

## Considered options

1. Run folders and suites stay the truth. A database keeps who is working on what, unfinished verdicts and an append-only log of every decision. A verdict a lawyer gives is also written where the files keep it.
2. The database becomes the truth, and the files are imported into it and exported from it.
3. No database: the web app writes only files.

## Decision outcome

Chosen option 1, because every command that reads a run keeps working with no database, and the score stays computed by the runner on the engineer's machine ([0005](0005-cloud-never-computes-a-score.md)). Option 2 makes the gate and re-scoring depend on a server. Option 3 has nowhere to keep a reservation, an unfinished verdict or who decided what before a file is written.

- **Where things live.**
  - A run's results and scores stay in its folder, and suites stay frozen folders ([0015](0015-suite-and-run-log-formats.md)).
  - A lawyer's verdict on a criterion is appended to the run's `reviews.jsonl`, as `casebench review criterion` appends it ([0047](0047-the-judge-rests-on-evidence.md)). It replaces the judge's in the report's scores and in the gate.
  - An approved court draft is written back into its suite, which is frozen again and gets a new hash ([0039](0039-one-case-by-a-lawyer.md)).
  - The database, SQLite at `.casebench/casebench.db` by default, holds people, reservations, auto-saved drafts and the event log. SQLAlchemy writes it and Alembic migrates it when the app starts. `--database` takes another URL, so a team server can use Postgres later.
- **The queue.** `casebench ui` reads the runs under `--runs-dir` and the suites under `--suites`. A run finds its suite by the suite's id. The queue holds two kinds of item:
  - *Answers to review*: each result scored for criteria or citations that no lawyer has reviewed yet. Those where two judges disagreed come first, then those that failed a criterion, then the rest.
  - *Court drafts*: each draft case built from a court decision.

  Every person sees every item. Assigning items to people comes with team mode.
- **Reservation.** Opening an item reserves it for its reader for 15 minutes, renewed while it stays open, and the queue skips items others hold. Each choice is saved as a draft as it is made, so a closed tab loses nothing.
- **Answer review.** The evidence is on one side, the answer on the other.
  - Each criterion shows the judge's verdict, pre-filled and marked as the judge's.
  - A verdict that differs from the judge's needs a note.
  - Each citation is coloured verified, misgrounded, fabricated or unchecked, and opens its passage in the corpus document.
- **Court draft approval.** Each fact is shown beside its passage, highlighted in the decision's text when the corpus is configured, else as its quote. The reader approves, edits or rejects each fact.
  - An edit asks for a reason, and the edited fact's evidence becomes the reader's note with that reason.
  - A rejected fact is dropped with every criterion that comes from it.
  - When every fact is decided, the case is approved with the reader as the reference's author.
  - A draft that is not approved can still be run, and its scores stay in the report's unreviewed row.
- **Every decision is an event.** Each verdict, approval, edit and rejection is appended to the event log with who, when, before, after and the reason. Nothing in it is changed or removed.
- **Two views.**
  - The *review* view shows legal text, citations and passages, never a span, a token count or JSON.
  - The *engineering* view adds the agent's steps, tokens, latency and the raw records.
  - Each person picks a view when they first open the app and can switch. `casebench ui --role reviewer` serves the review view only: the API leaves the engineering fields out, so no setting in the browser shows them.
  - Roles with logins come with team mode ([0004](0004-open-core-and-ee-boundary.md)).
- **Keyboard first, touch too.** The digits 1 to 9 pick the numbered choice on the focused row, and the arrow keys or J and K move between rows. Cmd+Enter, or Ctrl+Enter, finishes the item and opens the next; `?` lists the shortcuts. On a narrow screen the evidence and the answer become tabs, and the choices become buttons large enough to tap.
- **The web app.**
  - React, Vite and TypeScript, with Tailwind and shadcn/ui components. The components' source is copied into the repository, so nothing loads at runtime from elsewhere.
  - The source is in `workbench/`, with exact versions in its lockfile. The build goes into `casebench/workbench/static/` and ships in the wheel.
  - The API is FastAPI on the Starlette and uvicorn the recording proxy already uses ([0019](0019-recording-proxy.md)).
- **Local and safe.** `casebench ui` binds 127.0.0.1 and has no login. It answers only requests whose `Host` is the loopback address it serves, so a web page elsewhere cannot reach it through DNS rebinding. It accepts writes only from its own origin.

### Consequences

- Good, because `run`, `report`, `gate` and re-scoring read the same files with or without the workbench, and a lawyer's verdict reaches them all.
- Good, because a lawyer works through the queue with one key per verdict, on a laptop or a phone, and never sees how the agent works inside.
- Bad, because two places hold data: what the files hold and what only the database holds, such as reservations and drafts. The event log records each decision that reached the files.
- Bad, because building the app needs Node, so a release builds it before the wheel.

## Revisit when

- Team mode needs assignments and roles with logins.
- A suite grows past what is quick to read from files for each request.

## More information

- The workbench design, its screens and interaction rules: [workbench.md](../design/workbench.md).
