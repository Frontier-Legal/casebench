---
title: Invite lawyers to a team server
description: Name the team server in casebench.yaml, check it takes your key, push runs and suites to it, invite lawyers by email, and pull their verdicts and approvals back for CI to score on.
sidebar:
  order: 2
---

Lawyers cannot reach your laptop or your CI. A [team server](/developers/guides/team/team-server/) is the workbench on a machine they can reach. Your machine stays where runs happen: you push runs and suites to the server, lawyers review there, and you pull their decisions back.

## Name the server

```sh
casebench init --team-server https://casebench.firm.example --no-routes --yes
```

In an existing setup this adds only the server's address to `casebench.yaml`:

```yaml title="casebench.yaml"
cloud:
  url: https://casebench.firm.example
```

A new `casebench init` at a terminal asks "Will lawyers review on a team server?" after every other part, with three answers: not now, we have one, or set one up. Set one up prints what to run on the machine lawyers reach, and installs nothing. Without a terminal init does not ask; pass `--team-server URL`.

The server's host joins the hosts a run may call.

## Set the key

An admin creates an API key with the engineer role on the server's Team page. Set it on your machine as `CASEBENCH_CLOUD_KEY`, in the shell or in a `.env` file in the project. `casebench.yaml` never holds it.

When the shell does not set it, Casebench reads it from the file `keys:` names for it, or else from the project's `.env` files. When two files hold different values, the command stops and names both by fingerprint; name the current one under `keys:`:

```yaml title="casebench.yaml"
keys:
  CASEBENCH_CLOUD_KEY: .env
```

`casebench keys CASEBENCH_CLOUD_KEY` says where the variable is set, without printing it. In CI, set it from a secret.

## Check it

When `cloud:` is set, `casebench check` has a `team server` part. It makes the cheapest call an engineer key may make, and says whether the server answers and takes the key:

```text frame="terminal"
team server passed: https://casebench.firm.example took the key as an engineer's
```

| Result | Means |
| --- | --- |
| passed | The server answered and took the key with the engineer role |
| no API key in CASEBENCH_CLOUD_KEY | The variable is set nowhere Casebench reads |
| 401 | The server refused the key |
| 403 | The key's role cannot push runs |
| any other refusal | The address is not a team server |
| not reachable from here | No connection could be made from this machine |

Each failure names its next step.

## Push runs

```text frame="terminal"
$ casebench push
pushed 2 runs and 1 suites to https://casebench.firm.example; no steps (add --traces to send them)
```

`casebench push` sends every run under `.casebench/runs` and the suites they ran. Name runs to send only those: `casebench push nightly-41 nightly-42`. Suites are found under the current folder, or under `--suites`. A run whose suite is not found is pushed without it, and the command says so.

Push is safe to repeat. A run is identified by its id: pushing it again rewrites what changed, and the server shows one run. Lawyers' verdicts and preferences are merged line by line, so a push never removes a verdict given on the server.

```text frame="terminal"
$ casebench push --traces
pushed 0 runs and 0 suites to https://casebench.firm.example; 3 were there already; steps as ids and numbers
```

When lawyers have changed a suite on the server since your last push, by approving drafts or editing cases, a push of a different version is refused until you pull.

### What crosses the line

Sent:

- each suite the pushed runs ran: its cases, with their evidence excerpts, and its manifest;
- each run's `run.json`, `results.jsonl`, score sets, `report.json`, `reviews.jsonl` and `preferences.jsonl`.

Never sent:

- the judge's kept replies, `judge.jsonl`, which hold the text the judge read;
- the corpus, its cache and full decision texts;
- the agent's code, `casebench.yaml`, `.env` files and keys;
- any other file in a run's folder.

Without `--traces`, results go up without their steps. With it, each step goes up as ids and numbers only: its kind, name, provider, model, document ids, tokens, sizes, start, end and duration. Tool arguments, notes and message content are never sent. The workbench's harness view on the server needs `--traces`.

The server accepts only these files and refuses any other path. A pushed suite carries evidence excerpts, which are passages from decisions. A team whose provider's terms forbid sharing them keeps reviewing on the engineer's machine with `casebench ui`.

## Invite lawyers

```text frame="terminal"
$ casebench invite ayse@firm.example --role reviewer --name "Ayşe Yılmaz"
invited ayse@firm.example as reviewer, emailed; 12 items wait, about 24 minutes
```

`--role` takes `viewer`, `reviewer` (the default), `editor`, `engineer` or `admin`. `--name` is how the person is shown; without it, the name is made from the email. An engineer key invites viewers, reviewers and editors. Only an admin invites an engineer or an admin:

```text frame="terminal"
Error: the engineer role cannot administer the team
```

The email says how many items wait in the queue for that role and about how long they take: two minutes for an answer to review, three for a court draft or a change to approve. When the server sends no email, the command prints the sign-in link for you to pass on:

```text frame="terminal"
invited ayse@firm.example as reviewer, not emailed: this server sends no email; 12 items wait, about 24 minutes
  send them this sign-in link, which works once within 15 minutes: https://casebench.firm.example/auth/link?token=...
```

## Pull their decisions back

```text frame="terminal"
$ casebench pull
pulled 0 changed suites, 2 verdicts and 0 preferences
```

`casebench pull` brings back:

- each suite the server has and your machine has too, written into its local folder when the server's version differs, so drafts lawyers approved are approved locally;
- each run's verdicts and preferences, merged into `reviews.jsonl` and `preferences.jsonl` in its local folder.

Pull never changes a score. The next `casebench gate` or `casebench report` applies lawyers' verdicts over the judge's, and the next run of a changed suite scores against what lawyers approved. A suite pulled with changes has a new hash, so runs before and after it are not compared or gated against each other.

## In CI

Set `CASEBENCH_CLOUD_KEY` from a secret, and add `casebench push` after the run and the gate. [A nightly run in CI](/examples/walkthroughs/scheduled-ci-run/) shows the whole workflow.

## Related

- [Run a team server](/developers/guides/team/team-server/).
- [Privacy and what leaves your machine](/developers/concepts/privacy/).
- [Review in a spreadsheet](/developers/guides/runs/spreadsheet-review/), for a firm with no server.
