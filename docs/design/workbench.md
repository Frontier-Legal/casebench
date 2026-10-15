# Casebench workbench: the lawyer-facing UI

## Summary

- Lawyers on legal AI teams use Casebench directly in a browser: write and approve golden data, try questions against the team's agent, review answers beside the evidence, overrule the judge, compare runs, export a partner report.
- Standalone. Casebench stores its own cases, runs, eval traces and reviews. Any other tool is optional export, never required.
- One app, three places. `casebench ui` runs locally with no login and a SQLite file. Casebench Cloud is the same app as a hosted service, reached from an email invite. The same image self-hosts for firms that cannot push. The cloud and the team server store and show; the runner on the engineer's machine computes every score ([decision 0005](../decisions/0005-cloud-never-computes-a-score.md)).
- A lawyer's first session is a queue, never an empty case editor: answers to review with the judge's verdict pre-filled, one key per verdict. Writing cases comes after, in the workbench or in a spreadsheet.
- Not an observability platform. No production dashboards, cost analytics or prompt management. Traces exist only to explain eval results.

## What crosses the line (checked 2026-10-11)

| Goes to the cloud or team server with `casebench push` | Stays on the engineer's machine |
|---|---|
| cases, approved and draft, with their evidence excerpts | the agent under test and its code |
| run outputs: answers, scores, error labels, cost and latency | the corpus and full decision texts |
| spans as ids and numbers (model, tokens, durations, document ids), only with `--traces`; never message content | API keys for the target and the judge |
| reviews: who decided what, when, why | anything not pushed |

`casebench pull` brings approved cases and reviews back, so CI runs on what the lawyers approved. Nothing in the shared place computes a score.

## Why lawyers need their own UI (checked 2026-09-30)

| Evidence | Source |
|---|---|
| A custom annotation tool is "the single most impactful investment" in an eval workflow | [Hamel Husain](https://hamel.dev/blog/posts/evals-faq/should-i-build-a-custom-annotation-tool-or-use-something-off-the-shelf.html) |

## Screens (v1)

| Screen | Who | What they do |
|---|---|---|
| Inbox | everyone | items assigned to me: drafts to approve, answers to review, judge disagreements; one item at a time with auto-advance |
| Golden data | lawyer editor | grid of cases (spreadsheet-like), XLSX import/export; open a case to edit question, facts, reference answer, weighted pass/fail criteria and authorities; every case names its practice area and who approved it; every save needs a reason, shows a diff, and waits for a second approver when the team turns that on ([decision 0053](../decisions/0053-second-approval-is-opt-in.md)) |
| Court drafts | lawyer editor | cases Casebench extracted from decisions: each fact shown beside its highlighted passage in the decision; approve, edit or reject with one key; a draft can be run at once, and its scores stay in the unreviewed row until approved |
| Try a question | lawyer | type a question, send it to a target the engineer configured, see the answer with every citation checked; "save as case" turns a spot check into golden data |
| Answer review | lawyer reviewer | evidence on the left (court record or reference), the agent's answer on the right; citations coloured verified, misgrounded or fabricated, each opening its source passage; per-criterion judge verdict with overrule plus required note; failure tags |
| Compare runs | lawyer, engineer | two runs per case, blind A/B/Equal with a reason; filters for regressions and improvements; significance summary |
| Judge agreement | engineer, lead lawyer | human vs judge per criterion and Cohen's κ; overruled verdicts become calibration data |
| Harness view | engineer | per case per run, a waterfall: each model call and tool call a bar with model, latency, input and output tokens and cost; a table per step and per model; the same case diffed across two runs; the authority funnel ([harness-eval.md](harness-eval.md)); time no span accounts for shown as a gap; hidden from reviewer roles |
| Report | lawyer lead | per run, the rates of fabricated citations, unsupported claims, wrong outcomes and wrong statutes, each opening its failing answers beside their evidence; a partner-readable PDF/DOCX per suite: metrics by task and practice area with intervals, worked examples, who approved the golden data ([decision 0054](../decisions/0054-compare-blind-and-a-report-for-partners.md)) |
| Settings | admin | targets, corpus, judge model and key, users and roles, spend limits |

## Interaction rules

- Keyboard first: 1 to 9 picks a label, A/B/E for compare, Cmd+Enter completes and advances, ? lists shortcuts.
- Binary criteria with weights, never Likert scales. A judge's suggestion is pre-filled and marked, and a human decision always wins.
- Blind mode for compare and multi-reviewer items: reviewers do not see each other's or the judge's verdict until they submit.
- A lawyer can reserve items while working on them; drafts save automatically.
- Lawyers never see spans, token counts or JSON. Everything is shown as legal text, citations and passages.

## Roles and audit

| Role | Can |
|---|---|
| Admin | users, roles, targets, keys, spend limits |
| Engineer | suites, runs, targets, harness view |
| Editor (lawyer) | create and change golden data; approve others' changes |
| Reviewer (lawyer) | review answers, overrule judges, compare runs, try questions |
| Viewer | read results and reports |

- Every change to golden data and every overruled verdict is an append-only event: who, when, before, after, reason. Scores keep their history.
- Golden data takes effect only after a second editor approves it.
- The report states who approved the golden data it was scored against.
- No regulation we found requires this for eval data. It follows from lawyers' duties of competence and supervision (ABA Opinion 512) and is what firms will ask.

## Architecture

| Part | Choice |
|---|---|
| Backend | FastAPI inside the `casebench` package; the same service layer the Python SDK and CLI use |
| Frontend | React + Vite + TypeScript, built into a static bundle shipped inside the wheel (target under 10 MB) |
| Storage | SQLAlchemy + Alembic; SQLite at `./.casebench/casebench.db` by default, never a temp folder; Postgres by URL for teams |
| Files | cases, runs and reviews export to and import from JSONL, so a suite can live in Git and be diffed |
| Traces | OTLP receiver and SDK spans stored per run in the same database; kept only for eval runs |
| Local mode | `casebench ui` binds 127.0.0.1, no login, opens the browser |
| Team mode | Docker image; password login with no default password (first admin set at setup), OIDC for Entra ID or Google, API keys for CI, roles above |
| Cloud | the same `ee/` app as a hosted service, one tenant per organisation; magic-link email, Microsoft and Google login; `casebench invite <email> --role` from the CLI; retention, SSO and scheduled runs |
| Sync | `casebench push` and `casebench pull` between the local store and the cloud or team server; the table above says what crosses |
| Spreadsheet review | `casebench export --review` writes an XLSX with answer, evidence links and verdict columns; lawyers fill it; `casebench import` merges the verdicts as reviews. The lawyer path when there is no server and no cloud |
| Model calls | only through targets and the judge the admin configured, with per-user and per-day spend limits |

The same package serves local, team and cloud use. Review, overrule, compare and agreement are in the Apache-2.0 core and work locally with no login. The multi-user layer (roles, SSO, audit, invites) is in `ee/`, free to self-host for your own organisation ([open-source.md](open-source.md)).

## What it will not become

- A tracing or monitoring product: no production traffic dashboards, latency or cost analytics beyond a run's own cost.
- A prompt editor or playground for engineers. "Try a question" calls a configured target only.
- Dependent on Elasticsearch, Redis, ClickHouse or any second service.
- A place where an LLM judge can overwrite a lawyer's decision.
