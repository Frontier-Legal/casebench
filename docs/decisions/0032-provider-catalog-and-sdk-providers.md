---
status: accepted
date: 2026-10-12
decision-makers: Casebench maintainers
---

# Models are picked from a public catalog; cloud providers are called through the project's own SDK

## Context and problem statement

Casebench calls models of its own: the judge ([0026](0026-judge-and-citation-checks.md)) and the two extraction models ([0027](0027-answer-keys-from-decisions.md)). A team may reach models through any of hundreds of providers, and typing a base URL, a key variable and a model id by hand is where set-up goes wrong. Some clouds authenticate with their own signing or OAuth, which Casebench should not re-implement. Casebench runs inside the team's project ([0030](0030-set-up-here-run-there.md)), where those SDKs and credentials are already set up.

## Considered options

- Pick provider and model from a public catalog in `casebench init`; call providers over HTTP where they offer an OpenAI-compatible or Anthropic-compatible API, and through the SDK already installed in the project where they authenticate their own way
- Ask for a base URL, a key variable and a model id by hand
- Depend on a multi-provider gateway library for every call

## Decision outcome

Chosen option: "a public catalog, HTTP where it suffices, the project's SDK where it does not", because the user picks from names they recognise, and Casebench never signs a request or stores a credential.

- **Catalog.** `casebench init` reads [models.dev](https://models.dev) (MIT licence): each provider's name, the environment variables its key lives in, its base URL and docs, and each model's id, family and limits. It is fetched over HTTPS each time `init` asks for a model (about 0.5 MB compressed) and kept in memory only; nothing is written to the project. `--catalog FILE` reads a saved copy instead.
- **Picker.** The provider list and the model list are a type-to-filter menu ([questionary](https://github.com/tmbo/questionary), MIT, `use_search_filter`), because the catalog lists hundreds of providers. The same picker serves the judge and both extraction models. Every choice also has a flag, so `init` runs with no terminal.
- **Which plugin serves a catalog entry.** Each model-provider plugin may say which catalog entries it serves and with what options (`from_catalog`). Where more than one does, the one that needs nothing more from the user wins. An entry no plugin fully serves gets the base URL asked once, with the provider's docs link shown.
- **HTTP providers.** The built-in OpenAI-compatible and Anthropic-compatible providers reach every catalog entry that offers such an API; Casebench sends the request and reads the key from the variable the catalog names.
- **SDK providers.** For Amazon Bedrock, Google (Gemini API and Vertex AI) and Azure OpenAI, a built-in provider calls the vendor's own Python SDK (`boto3`, `google-genai`, `openai`), which reads the environment's credentials itself. Casebench does not depend on those SDKs; `init` checks the chosen one imports in the project and says what it found. These providers are the exception to providers being pure ([0016](0016-plugin-contract.md)): they send their own call.
- **Family.** The model's family comes from the catalog and is stored with the judge, ready for comparing the judge with the target's models.
- `casebench check` asks each configured model one short question, so a wrong credential shows before a run.

### Consequences

- Good, because choosing a judge is two filtered lists, and a cloud the team already uses works with the credentials it already has.
- Bad, because the catalog is a third party's data; when it is wrong or unreachable, the user types the base URL, as before.
- Bad, because an SDK provider's call does not pass through Casebench's sender; its traffic is the SDK's.

## Revisit when

The catalog stops being maintained, or users need a provider whose API is neither OpenAI- nor Anthropic-compatible and has no SDK provider.
