---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# httpx, jsonpath-ng and PyYAML

## Context and problem statement

The HTTP target sends cases to endpoints and reads answers out of their JSON, and users describe targets and corpora in `casebench.yaml`. Each needs a library; writing an HTTP client, a JSONPath engine or a YAML parser in the project would be code nobody should have to maintain.

## Considered options

- HTTP: httpx; requests; urllib from the standard library
- JSONPath: jsonpath-ng; python-jsonpath
- YAML: PyYAML; ruamel.yaml

## Decision outcome

Chosen options: httpx, jsonpath-ng and PyYAML.

- **httpx** has one API for synchronous and asynchronous calls, which the async runner needs, takes an explicit timeout per request, and accepts a mock transport in tests. requests has no async API; urllib has neither.
- **jsonpath-ng** is the most widely used JSONPath library for Python and was released on 2026-10-09. python-jsonpath follows RFC 9535 more closely and is the alternative if users hit a gap; the expressions targets need (`$.answer`, `$.sources[*].ref`) behave the same in both.
- **PyYAML** is the YAML parser most Python projects already have. Casebench reads config only with `yaml.safe_load`, which never constructs Python objects. ruamel.yaml keeps comments on round trips, which Casebench does not need because it never rewrites a user's config.

### Consequences

- Good, because all three are pure-Python or ship wheels for every supported platform.
- Bad, because httpx's last release is from 2024-12; if it stops being maintained, the client sits behind the targets and the provider call helper and can be swapped.

## Revisit when

httpx goes unmaintained, a user's JSONPath expression behaves differently from RFC 9535, or Casebench needs to rewrite YAML files.

## More information

- [httpx](https://www.python-httpx.org/)
- [jsonpath-ng](https://github.com/jsonpath-ng/jsonpath-ng)
- [PyYAML safe_load](https://pyyaml.org/wiki/PyYAMLDocumentation)
