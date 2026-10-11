# Casebench user stories: score, report, compare, extend

Tags: `@P0` first release (R1), `@P1` R2, `@P2` later. Connecting and running stories are in [stories-run.md](stories-run.md).

```gherkin
@P0
Feature: Exact scoring for objective tests
  As an AI engineer
  I want outcome and statute answers checked against the answer key without an LLM
  So that the core scores are deterministic and cheap

  Scenario: Wrong outcome
    Given a test whose answer key is "reversed"
    When the target answers "upheld"
    Then the test fails with the label "wrong outcome"

@P0
Feature: Citation integrity
  As a vendor whose largest risk is invented case law
  I want every citation in an answer checked against the corpus
  So that I know how often my tool fabricates or misstates sources

  Scenario: Fabricated and misstated citations
    Given an answer that cites three decisions
    When the answer is scored
    Then each citation is found in the corpus or labelled "fabricated citation"
    And each found citation's passage is compared with the claim made about it
    And the report shows fabricated, misstated and correct citation rates

@P1
Feature: Statute in force on the date
  As a lawyer relying on the tool
  I want answers checked against the statute version in force on the relevant date
  So that repealed or amended law is caught

  Scenario: Amended article
    Given a question about events in 2019
    When the target quotes an article as amended in 2023
    Then the test fails with the label "wrong statute version"

@P0
Feature: Judge anchored to the court's reasoning
  As an AI engineer
  I want open-ended answers graded against the court's own reasoning
  So that the judge compares against a reference instead of guessing

  Scenario: Same-family warning and calibration
    Given research tests with the court's reasoning as the reference
    When the judge comes from the same model family as the target
    Then the report warns that same-family judges may favour the target
    And the report shows the judge's agreement with exact scoring on a sample of objective tests

@P0
Feature: A report a lawyer can read
  As a head of legal innovation
  I want results broken down by legal error type with real examples
  So that I can explain the risk to partners without metrics jargon

  Scenario: Error breakdown
    Given a finished run
    When I open report.html
    Then I see rates for fabricated citation, wrong outcome, wrong statute, wrong version and unsupported claim
    And each rate opens its failing examples with question, answer and court record side by side

@P0
Feature: Honest baselines
  As a buyer reading a score
  I want a no-model baseline beside every score
  So that I can see how much the question text alone gives away

  Scenario: Baselines shown
    Given an outcome suite
    When the run finishes
    Then the report shows majority-class and text-only baselines next to the target's score

@P1
Feature: Regression gate in CI
  As an AI engineer changing prompts or models
  I want a gate in my pipeline
  So that a drop in legal accuracy blocks the release

  Scenario: Significant drop
    Given a saved baseline run on a frozen suite
    When a new run's citation accuracy falls outside the confidence interval
    Then "casebench gate" exits non-zero and names the failing error types
    And a drop inside the interval is reported without failing the build

@P1
Feature: Reproducible results
  As a buyer
  I want to rerun a vendor's exact suite
  So that I can verify the score they claim

  Scenario: Frozen suite
    Given a vendor publishes a suite id, its hash and the Casebench version
    When I run that suite against the same corpus snapshot
    Then I get the same tests in the same order
    And any mismatch in corpus snapshot or version is reported before the run starts

@P1
Feature: Compare vendors
  As a firm choosing between legal AI products
  I want several targets run on one suite
  So that I compare them on my own practice area

  Scenario: Three-way comparison
    Given three connected or imported targets
    When I run "casebench compare"
    Then I see each target's score per test type and error type with confidence intervals
    And differences that are not significant are marked as such

@P1
Feature: Export to tools already in use
  As a team on Langfuse or LangSmith
  I want Casebench scores written into my existing tool
  So that I do not need another dashboard

  Scenario: Langfuse export
    Given Langfuse credentials in the config
    When a run finishes
    Then each test becomes a dataset item and each score is attached to its trace

@P0
Feature: Data stays inside the perimeter
  As a firm's security officer
  I want Casebench to call only my target and my chosen judge
  So that client-adjacent data never reaches a third party

  Scenario: Allowlist enforced
    Given a network allowlist with my target's host and my judge provider
    When a run attempts a request to any other host
    Then the request is blocked and the run stops with an error
    And nothing is sent as telemetry unless I opted in

@P1
Feature: Add a jurisdiction
  As an open-source contributor in another country
  I want to write an adapter for my country's decisions and citation formats
  So that Casebench works for my legal system

  Scenario: Adapter conformance
    Given a new adapter with sample decisions and hand-checked expected extractions
    When I run "casebench plugin test ./casebench-fr"
    Then citation parsing, operative-part extraction and statute-version lookup are checked against the samples
    And a passing adapter is listed with its measured extraction accuracy
```
