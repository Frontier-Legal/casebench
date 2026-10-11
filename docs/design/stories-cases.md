# Casebench user stories: cases, tasks and harness diagnostics

Tags: `@P0` first public release (R1), `@P1` R2. Model: [architecture.md](architecture.md); diagnostics: [harness-eval.md](harness-eval.md).

```gherkin
@P0
Feature: First result with no key and no data
  As an engineer who has never heard of Casebench
  I want one command to show me a real report
  So that I understand what it does before configuring anything

  Scenario: Demo
    When I run "uvx casebench demo"
    Then a bundled suite runs against an echo target with cached judge verdicts
    And the viewer opens on failures shown beside their evidence
    And no network call leaves my machine

@P0
Feature: Lawyers author cases in a spreadsheet
  As a firm's knowledge lawyer
  I want to write reference answers in a spreadsheet
  So that our own anonymised matters become test cases without YAML

  Scenario: Template round trip
    Given I ran "casebench template lawyer --task qa"
    And I filled facts, question, reference answer, key points with weights and authorities
    When an engineer runs "casebench import cases.xlsx"
    Then each row becomes a case whose reference source is "lawyer"
    And each key point becomes a criterion tied to the row it came from
    And a row with no key points is imported as "unevidenced" and flagged in the report

@P0
Feature: Drafting graded by evidenced criteria
  As a firm builder
  I want a drafted document graded against the points my lawyer listed
  So that drafting quality is measured without a free-form LLM opinion

  Scenario: Weighted criteria
    Given a drafting case with criteria weighted +5, +3 and -4
    When the target's draft meets the +5 criterion and triggers the -4 criterion
    Then each criterion is shown as pass or fail with the judge's quoted evidence
    And the case score is the weighted sum over the positive weights, clipped to 0 to 1
    And every citation in the draft is still checked against the corpus

@P0
Feature: Editing keeps what it should not touch
  As a vendor shipping contract review
  I want edits checked for the issues found and for unintended changes
  So that a helpful edit that breaks another clause is caught

  Scenario: Unrequested change
    Given an editing case whose reference lists clause 9.2 as the issue
    When the target flags 9.2 and also rewrites clause 4
    Then "issues found" passes for 9.2
    And "meaning preserved outside the edit" fails for clause 4 with the diff shown

@P0
Feature: No blended score
  As a buyer reading a report
  I want every number tied to one task, one metric and one reference source
  So that court-derived and lawyer-authored results are never averaged together

  Scenario: Mixed suite
    Given a suite with court-derived qa cases and lawyer-authored drafting cases
    When the report is built
    Then it shows one table per task and metric, split by reference source
    And court-derived rows are split into lawyer-approved and unreviewed
    And it shows no overall accuracy figure

@P0
Feature: Where the right authority was lost
  As a harness engineer
  I want to follow each gold authority through my pipeline
  So that I know whether retrieval, reranking, context or the model failed

  Scenario: Rerank drop
    Given my target returns a JSON trace with retrieval, rerank and llm steps
    And the case's gold authorities include decision D
    When D appears in the retrieval step but not in the rerank output
    Then the case shows the label "rerank_drop" for D
    And the suite funnel shows how many gold authorities survive each step

  Scenario: Citation from memory
    When the answer cites a decision that no retrieval or tool step returned
    Then the citation is labelled "ungrounded"

@P0
Feature: Every model call measured with no change to my code
  As an engineer whose agent loop has many model calls, tool calls and branches
  I want each call's model, latency and tokens, and each tool call's duration
  So that I see what a run does without adding decorators

  Scenario: Process wrapper
    Given a Python agent that uses the Anthropic or OpenAI SDK and has no tracing
    When I run "casebench run --python agent.py"
    Then every model call shows provider, model, latency, input and output tokens
    And every tool call shows its name, arguments, result size and duration, paired from the model stream
    And time no span accounts for is shown as a gap between the two calls around it

  Scenario: Any language through the proxy
    Given a TypeScript agent with "ANTHROPIC_BASE_URL" pointed at "casebench proxy"
    When a case runs
    Then the same per-call record is shown, read from the requests and responses

  Scenario: A backend through the proxy
    Given an agent that calls Qdrant and a rerank API over HTTP, with their base URL variables pointed at "casebench proxy"
    When a case runs
    Then the retrieval step shows the document ids returned and the rerank step shows the ids in and out
    And an unknown backend is read with the JSONPath the config names

  Scenario: A function named in the config
    Given a Python agent whose rerank is a function in its own process
    When the config names that function and maps its arguments and return value to document ids
    Then the step appears with its duration and ids, and the agent's code is unchanged

@P0
Feature: Traces from the tools I already use
  As a team already tracing with OpenTelemetry, Langfuse or LangSmith
  I want Casebench to read those traces
  So that I get stage diagnostics without changing my harness

  Scenario: OTLP intake
    Given my harness exports OTLP spans using OTel GenAI or OpenInference attributes
    When I point "casebench run" at the collector
    Then retrieval, rerank, tool and llm spans are mapped to Casebench steps
    And a span without document ids is reported as "no diagnostic possible"

@P1
Feature: What fixing one stage would buy
  As a harness engineer choosing where to invest
  I want to rerun a suite with one stage changed
  So that I measure the outcome gain instead of guessing

  Scenario: Oracle context
    Given a Python target that exposes a named "retrieve" stage
    When I run "casebench experiment oracle-context"
    Then the generator receives the gold authorities instead of retrieved ones
    And the report shows the paired per-case outcome change with a confidence interval
```
