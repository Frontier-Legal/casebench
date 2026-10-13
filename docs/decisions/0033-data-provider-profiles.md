---
status: proposed
date: 2026-10-12
decision-makers: Casebench maintainers
---

# Data providers are profiles the built-in connectors run; a code plugin only where a profile cannot reach

Amends [0025](0025-corpus-connectors.md): provider profiles replace "no provider presets", and resolved citations are cached. Changes the corpus question in `casebench init` ([0030](0030-set-up-here-run-there.md)).

## Context and problem statement

`casebench init` asks where the corpus is, and for a provider's API it then asks for a base URL, a key variable, tool names and a JSONPath for each field ([0025](0025-corpus-connectors.md)). A provider's engineers know these answers; few users do. A data provider wants its store to be one choice in onboarding. The corpus does two jobs, and the question has to say both: generated cases come from it, and every citation in an answer is checked against it (rule 6). A team without a corpus can still bring lawyer-written cases, but its citations then have nothing to resolve against.

- Every provider seen so far has the same shape: search, then fetch. The built-in `http` and `mcp` connectors already run that. Providers differ in authentication, metering and access rules.
- Commercial providers meter their APIs. A legal-data MCP server checked for this record counts each search against the customer's monthly quota, and lets a document be fetched only after a search has returned it. Casebench fetches each document once ever, but it repeats every citation search on every run (0025). A metered provider therefore bills the user again on every run.
- The `mcp` connector cannot send a key to a remote server. `McpCorpusConfig` has a `url` but no `headers`, so a commercial provider's hosted MCP server cannot be reached without code.
- Casebench is neutral (rule 8, 0025). Once any provider appears in onboarding, every provider must be held to the same bar, whoever they are.

## Considered options

1. Provider profiles: one data file per provider, run by the built-in `http` or `mcp` connector, either contributed by pull request with recorded samples or handed to the user as a file. A `casebench-<name>` code plugin only where a profile cannot reach.
2. The provider's connector as code inside the core, as a built-in plugin.
3. The provider's own `casebench-<name>` package and nothing in the core (0025 as it stands).
4. Providers discovered during onboarding from the public MCP Registry.
5. Keep `corpus add` as it is and only reword the onboarding question.
6. Profiles shipped in the provider's own Python package and found through an entry point.

## Decision outcome

Chosen option: "provider profiles", because what a provider knows (address, key, tools, fields) is data the core already runs. The provider can contribute it without the maintainers taking on code that breaks whenever the provider's API changes, and onboarding can list it without a network call.

- **Profile.** A YAML file holding:
  - the provider's name, the jurisdictions it covers, and links to its docs and terms;
  - the connector (`http`, `mcp` or a plugin's name) and that connector's options, with `${VAR}` standing in for the key;
  - the environment variables the key can live in;
  - `metered`: `search`, `fetch` or `none`.

  The options are exactly what `corpus add` would write: a profile is a saved answer to it.
- **Where profiles come from.** Two places, both read without running any code:
  - **Bundled** with Casebench under `casebench/corpus/profiles/`, after review. Only these are listed in onboarding.
  - **A file** the user names: `casebench init --profile acme.yaml` or `casebench corpus add --profile acme.yaml`. A provider that never contributes to Casebench hands its users this file, from its docs for example. The path must be a local file; Casebench does not fetch a profile from a URL (rule 5).
- **Admission to the bundled list.** One bar for every provider:
  - `samples/` holds a recorded search and fetch that the provider may redistribute;
  - `casebench plugin test` passes on them offline;
  - the profile names a maintainer who answers issues.
- **Code plugins.** A provider whose API needs logic a profile cannot hold (OAuth, signed requests, paging that changes shape) publishes `casebench-<name>` with a connector plugin ([0016](0016-plugin-contract.md)), plus a profile, bundled or as a file, that names that plugin as its connector. Onboarding marks a bundled one as needing that package.
- **Onboarding.** `init` asks one question: "Connect a source of court decisions? Casebench builds test cases from it and checks every citation against it." The choices are:
  - every bundled profile, sorted by name. A profile whose key variable is set here is marked as found and preselected; nothing else is ever preselected.
  - a folder on this machine;
  - another HTTP or MCP service, which is today's `corpus add`;
  - "not now, I'll bring lawyer-written cases", which says that citation checks wait until a corpus is added.

  Picking a profile asks nothing more when its key is set, and runs one live search and fetch, as `corpus add` does. `init --profile FILE` skips the question and runs the same live search and fetch on that file's profile, so a broken file fails there, before anything is written.
- **What init writes.** `init` writes the profile's options into `casebench.yaml`, along with `profile: <id>` and, for a file, the file name it came from. The config stays reproducible when a later release or a newer file changes the profile.
- **Metering.** For a metered provider:
  - `init` and `corpus check` say how many searches they will spend before spending them;
  - each resolved citation is kept under `.casebench/corpus-cache/<corpus key>/citations/`, so a citation costs one search ever, as a document costs one fetch;
  - `corpus cache clear` empties both.
- **MCP keys.** The `mcp` connector gains `headers` with `${VAR}`, as the `http` connector has, sent over Streamable HTTP. OAuth is left to a code plugin until a provider needs it.
- **Neutrality.** The list has no default, no order but the name, and no ranking words. A test checks that profiles are sorted and that none is preselected without its key.

### Consequences

- Good, because a user whose provider key is set answers one question, and a provider adds itself with a data file and samples, reviewed like any other change.
- Good, because the core never runs provider-specific code, and every provider gets the same treatment.
- Good, because a provider that never contributes to Casebench still reaches its users in one step, with a file and `--profile`.
- Bad, because fixes to a bundled profile ship with Casebench releases. Until one ships, the provider can hand out a fixed file, or the user edits the options already in `casebench.yaml`.
- Bad, because a profile file is only as trustworthy as where the user got it. Casebench runs no code from it, and the live search and fetch show what it reaches before anything is written.
- Bad, because the maintainers review profiles and their samples, and a broken profile lands in their issue queue until its maintainer fixes it.
- Bad, because a provider that renumbers its documents makes cached citations wrong until the cache is cleared.

## Why not the others

- Code in the core: the maintainers would own each provider's breakages and release schedule, and whichever provider got into the core first would look favoured.
- Package only: the user has to know a package exists and install it before onboarding can offer it, which is the friction this decision removes. It stays available for providers that need code.
- MCP Registry: it adds a network call during onboarding (rule 5), it lists servers rather than field mappings, and it covers MCP providers only.
- Rewording alone: the user still types tool names and JSONPath, which is the step where set-up fails.
- Profiles in a provider's package: installing a package can run code, only to deliver a data file. Anyone can publish `casebench-<name>`, so Casebench could not tell whether the provider published it. The user would add a dependency to the agent's own project ([0030](0030-set-up-here-run-there.md)) for a config file. And the user still has to know the package exists. A file gives a provider the same independence from Casebench releases without any of this.

## Revisit when

- There are more profiles than the maintainers can review. Profiles would then move to their own repository, and releases would bundle a snapshot, as [0032](0032-provider-catalog-and-sdk-providers.md) does with the model catalog.
- Users ask for profiles they received as files to appear in the onboarding list.
- A second provider needs OAuth.
- A provider's terms forbid the local cache of full texts or of resolved citations.

## More information

Checked on 2026-10-12:

- A commercial legal-data MCP server, in the instructions it gives clients: each search draws on the customer's monthly quota; a document can be fetched only by an id a search returned, once per search.
- Casebench's connectors: `HttpCorpusConfig` has `headers`; `McpCorpusConfig` has none; `CachedConnector` passes searches straight through.
- [models.dev](https://github.com/anomalyco/models.dev): one data file per provider, added by pull request and validated by CI.
- [Terraform Registry](https://developer.hashicorp.com/terraform/registry/providers): partner providers are "written, maintained, validated and published by third-party companies against their own APIs".
- [Airbyte](https://docs.airbyte.com/platform/connector-development/config-based/low-code-cdk-overview): REST connectors written as YAML manifests and submitted by pull request; support is split into [Certified and Community](https://airbyte.com/blog/introducing-certified-community-connectors).
- [LangChain](https://python.langchain.com/v0.2/docs/contributing/integrations): partner packages are separate packages co-maintained with the partner. The sunset of `langchain-community` is known only from [its forum](https://forum.langchain.com/t/recommended-migration-path-for-tools-and-integrations-following-the-langchain-community-sunset/3934).
- [dbt](https://docs.getdbt.com/docs/trusted-adapters): the Trusted Adapter Program has ended; adapters maintained by dbt Labs, partners and the community are listed together.
- [MCP Registry](https://github.com/modelcontextprotocol/registry): server owners publish their own entries with `mcp-publisher`, and namespace ownership is verified.

Assumed and not checked: that commercial providers' terms allow a local cache of full texts, and that their hosted MCP servers accept a key header over Streamable HTTP.
