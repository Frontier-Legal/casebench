---
status: accepted
date: 2026-10-15
decision-makers: Casebench maintainers
---

# The hosted service builds on the team server through two seams, a seat check and erasing a team, and the public server needs neither

Adds to [0058](0058-the-team-server.md) (the team server) and [0059](0059-push-invite-pull.md) (push, invite, pull).

## Context and problem statement

Casebench Cloud hosts one team server per organisation. Sign-up, organisations, seat metering and billing belong to the hosted service alone. They live in a private repository that imports the public packages, never the other way round. The public team server must still give the hosted service what it cannot add from outside: a way to refuse an invitation when the organisation has no seat left, and a way to remove everything an organisation has. A firm that self-hosts must run the same server with none of it.

## Considered options

1. Two seams in `casebench-ee`: a seat check `build()` takes, consulted before each invitation, and `erase`, which removes a team's tables and folders. The hosted service builds one server per organisation, each with its own database and folders.
2. Organisations, seats and billing inside `casebench-ee`, switched off for self-hosting.
3. One shared database for all organisations, with an organisation column on every table.

## Decision outcome

Chosen option 1, because the public code stays free of anything only the hosted service needs, and isolation comes from construction: two organisations share no database and no folder, so no query can cross them. Option 2 ships billing code to every firm that self-hosts. Option 3 makes every query responsible for isolation.

- **The seat check.** `build(..., seats=...)` takes a function. Before an invitation, the server asks it how many seats the team has and where more are added. When every seat is taken, the invitation is refused with the count and that address, and nothing is written. The public server passes none, and its invitations are not counted.
- **Erasing a team.** `casebench-team erase` removes the team's tables, its runs and its suites, after the admin types the team's database name back. The hosted service runs it when an organisation deletes itself, and emails the confirmation. A self-hosting firm can use it to remove a server's data.
- **One server per organisation.** The hosted service calls `build()` for each organisation, with that organisation's database and folders.
- **The public server runs alone.** It has no sign-up, seat or billing route, and works with no hosting code installed. A test checks both.

### Consequences

- Good, because a firm that self-hosts runs exactly what the hosted service runs, minus billing.
- Good, because isolation needs no rule in each query.
- Bad, because the hosted service runs a server per organisation, which costs more than one shared server.

## Revisit when

- The number of organisations makes a server each too costly.
