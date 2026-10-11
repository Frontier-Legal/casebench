---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# Click for the command line

## Context and problem statement

The command line is the main interface for the first releases: `init`, `run`, `ui`, and power-user groups such as `corpus check`, `target check`, `plugin test`. It needs nested command groups, typed options, testable invocation and help text that reads well. Plugins may add commands later.

## Considered options

- Click
- Typer
- `argparse` from the standard library

## Decision outcome

Chosen option: "Click", because it has nested groups and a test runner (`click.testing.CliRunner`) built in, it is maintained by Pallets and used by Flask and many others, and it adds a single dependency with no transitive ones.

Typer is built on Click and adds Rich and shellingham as dependencies for features the project does not need yet. `argparse` has no test runner and makes nested groups and plugin-registered commands verbose.

### Consequences

- Good, because every command is testable in-process, which the scenario tests rely on.
- Good, because plugins can register command groups through an entry point later.
- Bad, because options are declared with decorators rather than inferred from type hints.

## Revisit when

The command surface needs rich terminal output that Click cannot produce cleanly, or Click stops being maintained.

## More information

- [Click documentation](https://click.palletsprojects.com/)
- [Click testing](https://click.palletsprojects.com/en/stable/testing/)
