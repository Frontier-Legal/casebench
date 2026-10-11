---
status: accepted
date: 2026-10-12
decision-makers: Casebench maintainers
---

# Set up where the code is; check and run where the agent and the corpus are reachable

## Context and problem statement

Some teams can run their agent on a laptop: the code is there, the model provider's key is set, and the corpus answers over the network. Others can reach the agent or the corpus only inside their own network, or only behind the login of the app built on the agent. Casebench must work both ways, and in neither may it need the app's login, an API in front of the agent, or a tunnel into production.

## Considered options

- Set up in the agent's checkout, then check and run wherever the target, the corpus and the judge's provider are reachable; the config file travels with the code
- Run from the laptop through a tunnel or the app's authenticated endpoint
- A hosted Casebench that calls into the team's network

## Decision outcome

Chosen option: "set up here, check and run there", because it reaches the agent and the corpus the way the team's own code does and asks for no new access. Where the laptop reaches everything, "here" and "there" are the same machine. A hosted runner may come with the cloud release; it does not change this.

- **The target is the agent's own entry**, never the app in front of it: a Python function or a command calls the agent's code directly, with no API; an HTTP endpoint is for agents that already serve one ([0017](0017-target-contract.md)). What that entry calls inside (databases, search engines, vendor APIs) is the agent's business; Casebench never needs to know.
- **`casebench init`** runs in the agent's checkout. It reads the project's dependency files (`uv.lock`, `pyproject.toml`, `requirements.txt`, `package.json`, parsed with `packaging`, the Python Packaging Authority's library) to name the model SDKs it found that an installed capture parser reads (each parser lists its SDK packages, Python's and Node's), asks for the target, the corpus and the judge, and writes `casebench.yaml`. It checks what needs no network: the config is valid, every plugin it names loads, and a Python target's entry imports. It then tries the live checks; one that cannot reach its endpoint from here is reported as "not reachable from here, run `casebench check` where it is", and is not an error.
- **`casebench.yaml` holds no secrets.** API keys are named by their environment variable ([0026](0026-judge-and-citation-checks.md)), so the file is committed with the code and deployed with it, together with the suite folder.
- **`casebench check`** runs every live check the config calls for: the corpus on a sample ([0025](0025-corpus-connectors.md)), the target on one sample case, and the judge on one short question. It exits non-zero when any fails, and is run before `casebench run` wherever the run happens.
- **Where to run** is any place with Python 3.11 or later that reaches the target, the corpus and the judge's provider. Casebench assumes nothing about how that place is deployed.
- **Results.** A run writes under `--runs-dir`; on a machine that is rebuilt, the user points it at storage that survives. `report.json` is the file to copy back.

### Consequences

- Good, because no new access path into the team's network is needed, and the data stays where it is.
- Good, because a team whose agent and corpus are reachable from the laptop sets up, checks and runs in one place.
- Bad, because `init` cannot prove a config works when the target or the corpus is out of reach; `check` has to run before the first run, on the machine that runs it.
- Bad, because reading results means copying `report.json` back until a workbench or a hosted runner exists.

## Revisit when

A hosted runner exists, or users report that `init` passes and `check` fails often enough that `init` should do more.
