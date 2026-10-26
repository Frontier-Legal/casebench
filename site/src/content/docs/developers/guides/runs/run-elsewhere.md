---
title: Run where the agent is reachable
description: Set Casebench up in the agent's checkout, then check and run it on a machine inside your network, with no tunnel and no new access.
sidebar:
  order: 3
---

Some agents and corpora are reachable only inside your network, or only from a deployed environment. Casebench needs no tunnel, no login to your app and no API in front of the agent. Set it up where the code is, then check and run it where the agent and the corpus are reachable.

## Set up where the code is

Set up with a [coding agent](/developers/guides/setup/coding-agent/), or run `casebench init` yourself. Either way you get `casebench.yaml` and, for a Python agent, the adapter in `.casebench/target.py`.

`casebench init --no-live` runs only the checks that need no network: the config is valid, every plugin it names loads, and a Python entry exists. A check that cannot reach its endpoint from your laptop is reported as not reachable from here, and is not an error.

## Commit the config

`casebench.yaml` holds no secrets. Every key is named by its environment variable, or by the `.env` file `keys:` reads it from, never by its value. Commit it with the suite folder and `.casebench/target.py`, and they deploy with the code.

## Check and run there

On the machine that reaches the agent, the corpus and the judge's provider, with Python 3.11 or later and the keys in its environment:

```sh
casebench check
casebench run --suite suites/employment --runs-dir /mnt/results/casebench
```

`check` reaches every part the config names and exits non-zero if any fails. It prints one line per part:

```text frame="terminal"
corpus   passed: 1 document sampled
team server passed: https://casebench.firm.example took the key as an engineer's
```

Run it before the first run on a new machine. In a script, `casebench check --json` gives each part's status, reason and next step.

## What the machine must reach

A run calls only the hosts `casebench.yaml` names: the target's URL, each judge's and extraction model's provider, each corpus, each capture route's upstream, the team server, and every host under `network: allow:`. Loopback is always allowed. Any other host stops the run. See [Allow the hosts your agent calls](/developers/guides/setup/network/).

Before it holds itself to those hosts, `casebench run` reads two public price lists, `https://openrouter.ai/api/v1/models` and the model catalog at `https://models.dev/api.json`, to price what the run spends. If your firewall blocks them, the run prices from the last lists it read, kept in `.casebench/prices.json`, or reports models as unpriced.

## Keep the results

Point `--runs-dir` at storage that survives when the machine is rebuilt. The run's folder holds everything the report was made from. `report.json` alone is enough to read the scores elsewhere. Copy the whole folder to keep it as a [baseline](/developers/guides/runs/gate-in-ci/#keep-a-baseline).

The last line of a run says how to open it:

```text frame="terminal"
open it in the workbench: casebench ui --runs-dir /mnt/results/casebench
```

On a machine nobody browses from, send the runs to a team server instead with `casebench push`; see [Invite lawyers to a team server](/developers/guides/team/invite-lawyers/).

## Related

- [Privacy and what leaves your machine](/developers/concepts/privacy/).
- [The perimeter](/developers/concepts/perimeter/).
