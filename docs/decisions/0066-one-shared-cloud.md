---
status: accepted
date: 2026-10-20
decision-makers: Casebench maintainers
---

# Casebench Cloud is one shared service for every organisation, and the database enforces which organisation a request reaches

Replaces the hosting model of [0060](0060-hosting-seams.md), one server per organisation; its two seams, the seat check and erasing a team, stay. Follows [0005](0005-cloud-never-computes-a-score.md): the cloud stores and shows, and never scores.

## Context and problem statement

[0060](0060-hosting-seams.md) had the hosted service run a team server for each organisation, so that no query could cross from one to another. The operator decided on 2026-10-20 that the cloud is one service serving every organisation, as hosted software usually is: one server per organisation costs more to run, to deploy and to upgrade, and keeping organisations apart is the job of access control, not of separate machines. What has to be decided is how that separation is enforced, so that one forgotten filter cannot show one firm another firm's cases or verdicts.

## Considered options

1. One service. Every table carries the organisation's id, and Postgres row-level security returns only the rows of the organisation the request was signed in to. Stored files live in object storage under the organisation's prefix and are reached only through the service.
2. One service, with each query filtering by organisation in application code.
3. One server per organisation ([0060](0060-hosting-seams.md)).

## Decision outcome

Chosen option 1, because the database refuses a row of another organisation even when a query forgets to ask for it, and the service costs what one deployment costs. Option 2 leaves isolation to every query anyone ever writes. Option 3 multiplies servers, databases and upgrades by the number of customers.

- **Every row belongs to an organisation.** Cases, suites, runs, results, scores, reviews, events, people, invitations and API keys each carry the organisation's id.
- **The database enforces it.** Each table has row-level security enabled and forced, so it binds the tables' owner too, with a policy that admits only rows whose organisation is the one set for the transaction. A middleware sets the request's organisation once, from the signed-in person or the API key, before any route runs, and every transaction begins by telling Postgres with `set_config(..., true)`, which is `SET LOCAL`, so it ends with the transaction. The service connects as a role that is no superuser and has no `BYPASSRLS` ([PostgreSQL: row security policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)); where the role can bypass them, or the database is SQLite, the server refuses to add a second organisation.
- **Signing in reads across organisations, and only that.** Finding a session, a sign-in link, an API key or a person by token or email happens before the organisation is known, so those reads, and no others, may see the sign-in tables of every organisation; what follows, such as starting the session, is written in the person's own organisation. An email names one person on the whole server, so someone in two firms uses two emails until that is needed.
- **Files are stored by organisation.** A pushed run's files and a suite's files go to object storage under the organisation's prefix. The browser reaches them only through the service, which reads them for the signed-in organisation; no address of a stored file is ever given out. Until object storage is in place, each organisation has folders of its own under the server's organisations folder; the organisation a self-hosted server has keeps the folders it was given.
- **Not found, never forbidden.** A request for another organisation's object is answered as if it did not exist, so ids reveal nothing.
- **Tested from outside.** A test signs in as two organisations and asks for every object of one as the other, on every route, and gets not found each time; another runs a query with no organisation filter and gets no row of the other organisation.
- **Self-hosting runs the same code.** A firm's own team server is the same service with one organisation, so a firm that self-hosts runs what the cloud runs ([0058](0058-the-team-server.md)).
- **The seams stay.** Before an invitation the service asks the seat check how many seats the organisation has. Erasing an organisation removes its rows, its event log included, which the log's guard allows only inside that one transaction, and its files; the hosted service then emails the confirmation.

### Consequences

- Good, because one deployment serves every customer, and a new organisation is a row, not a server.
- Good, because isolation does not depend on every query being written right.
- Bad, because a mistake in setting the organisation for a request reaches everyone, so that one place is tested on every route.
- Bad, because the team server's tables change: each gains an organisation id, in a migration.

## Revisit when

- A customer's contract requires its own database or its own region: then that customer gets a separate deployment of the same service.

## More information

- [PostgreSQL: row security policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html), read on 2026-10-20: `FORCE ROW LEVEL SECURITY` applies policies to the table's owner too; superusers and roles with `BYPASSRLS` bypass them.
