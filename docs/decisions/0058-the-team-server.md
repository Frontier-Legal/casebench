---
status: accepted
date: 2026-10-15
decision-makers: Casebench maintainers
---

# The team server: the workbench with logins, five roles and an append-only audit log, from one image

Adds to [0050](0050-the-review-queue.md) (the review queue), [0053](0053-second-approval-is-opt-in.md) (second approval until people log in) and [0057](0057-ee-under-the-elastic-license.md) (`ee/` under the Elastic License 2.0). Follows the workbench design ([workbench.md](../design/workbench.md), "Team mode").

## Context and problem statement

`casebench ui` serves one machine: no login, a name typed in the browser, and a database file. A team needs several lawyers and engineers on one store, each with a role, and a firm needs to know who changed what and when. Lawyers at firms cannot wait for IT to set up accounts, and a server on the internet must not start with a default password.

## Considered options

1. The same app with an access hook in the core. `casebench-ee`, under `ee/`, provides team logins, roles, the audit log and admin pages, and ships as one container image.
2. A separate team application that talks to the core's API.
3. Logins and roles in the core, with `ee/` only for hosting.

## Decision outcome

Chosen option 1, because the workbench lawyers already use stays the one they use in a team, and the core runs unchanged without `ee/` ([0057](0057-ee-under-the-elastic-license.md)). Option 2 doubles every screen. Option 3 puts the team layer under Apache-2.0.

- **The access hook (core).**
  - The workbench asks one object who is calling and what they may do: read, review, compare, try a question, edit golden data, use the engineering view, administer.
  - Locally that object is today's behaviour: the name typed in the browser, every permission but administering, and `--role reviewer` limited to reviewing.
  - The API checks each action against the caller's permissions. The web app hides what the caller cannot do.
  - `casebench-ee` passes its own access object and its own routes when it builds the app.
- **The event log is append-only in the database.** Triggers refuse any update or delete of an event, in SQLite and in Postgres. It is not enough that the app offers no way to change one ([0050](0050-the-review-queue.md)).
- **A judge never overwrites a lawyer.** Scoring a run again keeps the judge's new verdicts in the score set, and every report, gate and screen applies the lawyer's latest verdict over them ([0047](0047-the-judge-rests-on-evidence.md)).
- **`casebench-ee`.** A package built from `ee/`, on top of `casebench`. `casebench-team serve` runs the workbench with team access on the address and database it is given. Postgres is the database for a team; SQLite still works for a trial.
- **First admin, no default password.**
  - A deployment with no users prints a one-time setup code to its log at start.
  - Opening the app asks for that code, then the first admin's name, email and password.
  - The password must have 12 characters at least, and is refused when it is a common or default one, such as `admin`, `password` or `changeme`, or contains the email's name.
  - Passwords are stored as scrypt hashes. Once an admin exists, setup is closed.
- **Login without IT.**
  - An admin invites a person by email with a role. Casebench emails a sign-in link, valid for 15 minutes and usable once.
  - The person can also sign in with Google or Microsoft, when the server has those clients configured, using the same email. No one can sign up uninvited.
  - The email goes through the SMTP server the deployment configures, by default the firm's own. Without SMTP, the admin sees the link and sends it themselves.
  - A session is a random token in an HttpOnly, SameSite cookie, stored hashed, and lasts 14 days.
  - Signing in lands the person in their queue.
- **Five roles,** each including the one before:

  | Role | Can |
  |---|---|
  | viewer | read the queue, results, reports and comparisons |
  | reviewer | also give verdicts, compare runs blind and try questions |
  | editor | also change golden data, approve others' changes and approve court drafts |
  | engineer | also use the engineering view and the harness view, and run suites through API keys |
  | admin | also invite people, change roles, create API keys and set spend limits |

  - There is always one admin at least.
  - With logins, a second editor's approval ([0053](0053-second-approval-is-opt-in.md)) means a different signed-in person, when the team turns it on.
- **The audit log.** Every decision the event log keeps is shown to editors, engineers and admins: who, when, before, after and why. So is every team event: an invitation, a role change, a sign-in, an API key created or revoked, a limit changed. Nothing in it can be changed or removed.
- **API keys for CI.** An admin creates a named key with a role, shown once and stored hashed. It is sent as `Authorization: Bearer`.
- **Spend limits.** An admin sets the team's daily limit for "try a question" and a limit per person, in dollars. They take the place of `workbench.try_daily_limit_usd`.
- **Targets stay in `casebench.yaml`.** The admin page shows them read-only. Editing them in the browser is left for later.
- **One image.** `ee/Dockerfile` builds an image with `casebench` and `casebench-ee`. It is configured through the environment: the database URL, the public URL, SMTP, the Google and Microsoft clients, and the runs, suites and config paths. CI tests the team server against Postgres. Publishing the image belongs to hosting.
- **The web app.** The team screens (setup, sign-in, admin, audit log) live in `ee/web/`. The `casebench-ee` build of the workbench includes them; the core build does not.

### Consequences

- Good, because a lawyer gets a link and starts reviewing, with no IT ticket and no password to remember.
- Good, because the audit log cannot be edited even by someone with access to the app, short of the database itself.
- Bad, because targets are still edited in a file, by whoever runs the server.
- Bad, because sign-in by email depends on the deployment's SMTP; without it the admin passes links on by hand.

## Revisit when

- Firms ask for their own single sign-on (OIDC or SAML), planned for R2.
- Admins ask to edit targets in the browser.

## More information

- Workbench design, "Roles and audit" and "Team mode": [workbench.md](../design/workbench.md).
