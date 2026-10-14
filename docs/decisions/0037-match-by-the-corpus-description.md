---
status: accepted
date: 2026-10-14
decision-makers: Casebench maintainers
---

# The judge matches citations by what the corpus says about each result, one call per answer; scoring runs in parallel and survives a dropped call

Amends [0026](0026-judge-and-citation-checks.md) (what the judge sees to match a citation, and one matching call per citation) and [0029](0029-statute-and-precedent-scores.md) (a statute is searched like a decision).

## Context and problem statement

The first run of a real agent against a real Turkish corpus (8 cases, 2026-10-12) never finished scoring. To match a citation the judge saw each candidate's opening paragraph, the text before the first blank line (0026). In that corpus the opening was a header in most documents (median 45 characters) and the whole decision in 16 of 378 (up to 43,000 characters), because many texts have no blank line. Matching prompts reached 200,000 characters, the judge thought with no output limit, and the provider dropped the connection. Casebench's own HTTP calls had no timeout and no retry, so one dropped call stopped the whole scoring. Matching was one call per citation, one case at a time: the agent cited about 29 authorities per answer, at about 15 s per call. Statute citations were searched among decisions: 3 of 32 resolved, and a citation of a civil code article matched a court decision.

Cutting the opening to a fixed length would be a number with no source (rule 3). The corpus already describes each search result: the provider in that run returns, with every result, a formatted citation (court, chamber, docket numbers, date), a document type (`case_law`, `legislation`) and the passage the search matched. The provider chose those fields for exactly this purpose.

## Considered options

1. Show each candidate by the corpus's own description of the search result (citation, type, matched passage), mapped by JSONPath like every other field, and match all of an answer's citations in one call
2. Keep the opening paragraph, cut to a fixed number of characters
3. Show the whole document of each candidate
4. Rank candidates locally with an embedding model before the judge sees them

## Decision outcome

Chosen option 1, because the provider already knows how to describe its documents, the description is short by construction, and no length limit has to be invented.

- **Search results.** The `http` and `mcp` connectors take `search_results`, a JSONPath to each result in a search response, and `result_fields`, JSONPaths inside one result for its `id` and, where the corpus gives them, its `citation`, `type` and `passage`. `search_ids` still works for a store whose results carry nothing but ids. The connector contract gains an optional `search_results(text, limit, filters)` returning these; a connector without it is searched by id, as before.
- **What the judge sees.** Each candidate is its id and its citation, type and passage as the corpus gave them, and nothing else. When the corpus gives none of the three, Casebench fills them from the stored document: the court, date and metadata stand in for the citation, and the passage is the paragraph of the text that shares the most words with the citation searched for. A text with no paragraph breaks is split into lines. One with no line breaks either gives the shortest stretch of it that holds every word of the citation the text holds at all; splitting it into sentences was considered and left out, because a citation such as "E. 2023/1234" or "9. HD" ends a sentence wherever a full stop does. The `folder` connector gives the file name as the citation and that passage. The judge never sees a whole document to match it.
- **One matching call per answer.** Every citation of an answer is still searched on its own, and the judge then gets all of them, numbered, each with its candidates, and names one document or none for each, in one call. The call is split only when its prompt, estimated at four characters per token ([0028](0028-scores-baselines-and-intervals.md)), would exceed the judge model's context window, which `casebench init` takes from the model catalog's `limit.context` ([0032](0032-provider-catalog-and-sdk-providers.md)) as `context_window`. Without a known window there is one call.
- **Shared by every metric.** Citation integrity, the statute and precedent scores and the authority funnel resolve the same list of citations in the same call, so the judge's memo (0029) answers all but the first. Suite generation resolves the court's citations of one case in one call.
- **Filters per kind.** A corpus block, and a profile ([0033](0033-data-provider-profiles.md)), may set `search_filters` for each kind of citation the judge names, `statute` and `decision`: extra query parameters for `http`, extra tool arguments for `mcp`, fields a document must equal for `folder`. A statute citation is then searched only among what the statute filter returns, so it cannot resolve to a decision. Without filters, the result's type is shown to the judge, which can refuse a decision for a statute.
- **Parallel scoring.** Cases are scored on as many threads as the run's `--max-concurrency`, the number the user already chose for the target. Each judge reply is kept in the run's `judge.jsonl` as it arrives, and the score set keeps the order of the results.
- **Timeouts and retries.** Casebench's HTTP model providers send each call as the vendors' own Python SDKs do by default. The `openai` 3.29.0 and `anthropic` 1.13.0 SDKs, the versions in Casebench's lock file, read on 2026-10-14, both set a 600 s timeout with a 5 s connect timeout, and retry twice on a connection error, a timeout, 408, 409, 429 or any 5xx, unless the server's `x-should-retry` says otherwise. Between tries they wait as the server's `retry-after-ms` or `retry-after` says, otherwise 0.5 s doubled per retry up to 8 s, less up to a quarter at random. They differ in one thing, and each provider follows its own SDK: `openai` honours a `retry-after` of up to 120 s and does not retry past it, `anthropic` honours any. The `bedrock`, `google` and `azure` providers call the SDK itself, which retries on its own terms.
- **A scoring error stays with its case.** A case whose scoring still fails gets no score for that metric. The score set records the error under the case and metric, the other cases keep their scores, and the report counts the errors and says to rerun the run id. Rerunning scores the run again: every reply already kept is read from `judge.jsonl`, so only what failed is asked again. A run whose results are all stored does not start the target, so a stored run is re-scored without calling the agent.

### Consequences

- Good, because a matching prompt grows with the number of citations and candidates, not with the length of any document.
- Good, because an answer citing 29 authorities costs one matching call instead of 29, and eight cases score in about the time of the slowest when `--max-concurrency` is 8.
- Good, because a provider that drops a call costs a retry or one case's score, never the run's.
- Bad, because a corpus that maps no description makes Casebench fetch every candidate to describe it, as before, which costs fetches on a store that charges for them.
- Bad, because one unreadable matching reply leaves every citation of that answer unmatched; it is recorded as that case's scoring error and asked again on the next rerun.
- Bad, because parallel scoring sends several judge calls at once and can meet a rate limit; a 429 is retried as the SDKs retry it.

## Revisit when

- The report's unresolved count shows citations whose document the corpus returned but the judge did not pick from its description.
- A judge model's context window splits matching calls often enough that the split shows in cost.
- A vendor SDK changes its default timeout or retries.

## More information

- First real run, 2026-10-12: 8 cases, 378 documents fetched, 32 statute citations searched.
- OpenAI Python SDK 3.29.0 and Anthropic Python SDK 1.13.0: `_constants.py` (`DEFAULT_TIMEOUT`, `DEFAULT_MAX_RETRIES`, `INITIAL_RETRY_DELAY`, `MAX_RETRY_DELAY`, and OpenAI's `MAX_RETRY_AFTER_DELAY`) and `_base_client.py` (`_parse_retry_after_header`, `_should_retry`, `_should_retry_exception`, `_calculate_retry_timeout`), read 2026-10-14.
- [models.dev](https://models.dev) model entries carry `limit.context` and `limit.output`.
