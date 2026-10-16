---
status: accepted
date: 2026-10-16
decision-makers: Casebench maintainers
---

# Setup asks whether lawyers review on a team server, names it, and checks that it takes the engineer's key; it never installs one

Adds to [0043](0043-guided-onboarding.md) (guided init), [0044](0044-onboarding-by-a-coding-agent.md) (setup from one prompt), [0058](0058-the-team-server.md) (the team server) and [0059](0059-push-invite-pull.md) (push, invite, pull).

## Context and problem statement

The team server is the `casebench-ee` package, published to PyPI with each release from 0.3.0. Before this decision, nothing in setup mentioned it. `casebench init`, `casebench guide` and the setup skill ended with lawyers reviewing on the engineer's machine. The only hint was `casebench push` failing with "names no team server", which did not say where a server comes from. A team that wanted lawyers elsewhere had to find `ee/README.md` on its own.

Init runs in the agent's repository, on the engineer's machine. A team server runs where lawyers can reach it, usually a company server that someone else may administer. Installing the server from init would put it on the wrong machine.

## Considered options

1. Init asks the question last and writes only the server's address. `casebench check` reaches the server with the key. The skill asks after the first evaluation, and push's error says where a server comes from.
2. Init installs `casebench-ee` and starts a server on this machine.
3. Documentation only: a section in the README.

## Decision outcome

Chosen option 1. The engineer's machine keeps needing only `casebench`, and the person who runs the server installs it where lawyers can reach it. Option 2 starts a server that lawyers on other machines cannot reach, in the agent's environment. Option 3 leaves the engineer to find the answer after `casebench push` fails.

- **The question.** Init asks "Will lawyers review on a team server?" after every other part, before the review of what it writes. It has three answers:
  - **Not now** is the default: nothing is written, and the outro says how to name a server later.
  - **We have one** asks the address, and writes `cloud: url:` with nothing else.
  - **Set one up** prints what to run on the machine lawyers reach:
    1. `pip install casebench-ee`, then `casebench-team serve` with the database and public address set, or the container image;
    2. the one-time setup code;
    3. the engineer key the admin makes;
    4. `casebench init --team-server URL` back here.

  It installs nothing.
- **Without a terminal it is not asked.** Scripts and coding agents give `--team-server URL`, so a script's existing answers stay valid. In an existing setup, `casebench init --team-server URL` offers the change like any other addition, and `--yes` takes it without asking.
- **The key is never handled.** `cloud: url:` holds the address, and the key stays in `CASEBENCH_CLOUD_KEY` (decision 0059). Init tells the user to set it themselves, and no message carries its value. Init's own live checks leave the server out, because the key is set after init.
- **The check.** When `cloud:` is set, `casebench check` adds a `team server` part. It asks the server for the state of no suites and no runs, the cheapest call an engineer key may make. That call says whether the server answers and whether it takes the key with the engineer role.
  - An answer passes.
  - A 401 means the key was refused; a 403 means the key's role cannot push runs.
  - Any other refusal means the address is not a team server.
  - A connection that cannot be made is "not reachable from here".

  Each failure names its next step.
- **The coding agent.** The guide gains "A team server", and the skill asks the question as step 4, after the first evaluation. A first run stays as quick as before.
  - With an address, the agent names it with init, asks the user to set the key, runs `casebench check`, then `casebench push`, and offers `casebench invite`.
  - To set one up, it gives the commands. It installs on a server only if the user asks and it has access to that machine.

### Consequences

- Good, because a team learns where lawyers review elsewhere during setup, not from a failed push.
- Good, because a wrong address or key shows in `casebench check`, not at the first push.
- Bad, because a team that answers "Not now" is not asked again by a later `casebench init`; it names a server with `--team-server`.

## Revisit when

- The hosted service exists: "We have one" can offer to sign in to it.
