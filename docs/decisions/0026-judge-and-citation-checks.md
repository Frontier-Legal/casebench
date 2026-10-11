---
status: accepted
date: 2026-10-11
decision-makers: Casebench maintainers
---

# The judge lists, matches and weighs citations; the corpus finds them

## Context and problem statement

A citation can exist and still not say what the answer claims, and citation formats differ by country ([0024](0024-no-jurisdiction-adapters.md)). Checking a citation therefore takes three things only a model or a lawyer can do (reading the citations in free text, deciding which document a citation means, judging whether a passage supports a claim) and one thing only the corpus can do: finding candidate documents. The judge runs on the user's own model and key ([0007](0007-no-telemetry.md)), never on the system under test.

## Considered options

- The judge lists each citation with the claim it supports; the corpus search returns candidates; the judge picks the cited document or none; the judge reads that document and decides whether it supports the claim
- One prompt that does everything with the documents attached
- Exact string matching of citations against document metadata

## Decision outcome

Chosen option: "list, search, match, weigh", because each model step sees only what it needs and the corpus decides what exists.

- **Providers.** Casebench calls its judge through a model-provider plugin ([0016](0016-plugin-contract.md)). Two ship built in: `anthropic` (Messages API) and `openai` (Chat Completions, which also reaches any OpenAI-compatible endpoint through `base_url`). Each reads its key from an environment variable; the core sends the request with httpx2.
- **Config.** `judge: {provider, model, options}` in casebench.yaml. There is no default model: the user picks one.
- **Listing.** The judge returns every citation in the answer exactly as written, with the claim the answer makes about it, as JSON.
- **Finding.** The corpus searches for each citation and returns its first `candidates` results (default 5). This is a provisional choice, not a measurement: five keeps the matching prompt short, and a cited document the provider ranks lower is reported as unresolved, so the report's unresolved count is what to measure before changing it.
- **Matching.** The judge sees the citation and each candidate's court, date, metadata and opening paragraph, and names the candidate the citation refers to, or none. None means `fabricated`.
- **Weighing.** For a matched document the judge reads its full text and decides whether it supports the claim, quoting the passage. Supported is `verified`; not supported is `misgrounded`.
- **Score.** The `citation_integrity` metric scores an answer as the share of its citations that are verified, keeps every citation's label and quote on the score, and the report counts verified, misgrounded and fabricated citations across a run.
- **Ungrounded** (cited from memory, never retrieved) needs the captured steps and belongs to the authority funnel.

### Consequences

- Good, because every label rests on a document the corpus returned or on its absence.
- Bad, because one answer with several citations costs several judge calls; the dry run counts them.
- Bad, because the judge can be wrong; its agreement with exact scoring is measured and reported, and a lawyer's verdict outranks it.

## Revisit when

The unresolved count shows cited documents ranked below the fifth candidate, or the judge's measured agreement is too low to trust a label.

## More information

- [Anthropic Messages API](https://docs.anthropic.com/en/api/messages)
- [OpenAI Chat Completions](https://platform.openai.com/docs/api-reference/chat)
- Stanford RegLab's grounded, misgrounded and ungrounded labels: [Magesh et al.](https://arxiv.org/abs/2405.20362)
