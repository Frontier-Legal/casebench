# Casebench user stories: the lawyer workbench

Tags: `@P0` first public release (R1), `@P1` R2. Design: [workbench.md](workbench.md).

```gherkin
@P0
Feature: Approve golden data built from court decisions
  As a lawyer on a legal AI team
  I want to check each extracted fact against the decision it came from
  So that no wrong answer key reaches a run

  Scenario: Approve with evidence in view
    Given a court draft with an outcome, two statutes and one precedent
    When I open it in the workbench
    Then each fact is shown beside its highlighted passage in the decision
    And I can approve, edit or reject each fact with one key
    And an edited fact asks for a reason before it is saved
    And an unapproved draft can still be run, with its scores in the unreviewed row of the report

@P0
Feature: Golden data changes need a second lawyer
  As the lead lawyer of the eval team
  I want every change to golden data approved by another editor
  So that a single mistake cannot silently change our scores

  Scenario: Four-eye approval
    Given an editor changed a reference answer with the reason "statute amended in 2025"
    When a second editor opens the change
    Then they see the diff, the author, the time and the reason
    And the change takes effect only after they approve it
    And the audit log keeps both the change and the approval

@P0
Feature: Try a question and keep it
  As a lawyer spot-checking our agent
  I want to ask it a question from the workbench
  So that a good check becomes a permanent test case

  Scenario: Spot check to case
    Given the engineer configured the target "firm-assistant" with a daily spend limit
    When I ask a question and read the answer with its citations checked
    And I choose "save as case" and write the reference answer and criteria
    Then the case is added to the suite as a draft awaiting approval

@P0
Feature: Review answers in legal terms
  As a lawyer reviewer
  I want the agent's answer beside the evidence, with citations checked
  So that I judge legal quality without reading traces or JSON

  Scenario: Overrule the judge
    Given a run where the judge passed criterion "relies on İş Kanunu m. 18"
    When I read the answer and see the article is cited for the wrong proposition
    Then I can mark the criterion as failed with a required note
    And my verdict replaces the judge's in the scores
    And the overruled verdict is recorded as calibration data for the judge

@P0
Feature: Compare two versions blind
  As a lawyer asked whether the new agent version is better
  I want to compare answers without knowing which version wrote them
  So that my preference is not biased

  Scenario: Blind A/B
    Given two runs of the same suite
    When I open the comparison
    Then each case shows answers labelled A and B in random order
    And I choose A, B or Equal with a reason, using the keyboard
    And the result shows wins, losses and ties per practice area

@P0
Feature: Report for partners
  As the lead lawyer
  I want a report I can send to partners
  So that the firm decides on evidence it can read

  Scenario: Export
    When I export the report for a suite and run
    Then it shows each metric by task and practice area with its interval
    And it includes worked examples beside their evidence
    And it states who approved the golden data it was scored against

@P0
Feature: Local first, lawyers in minutes
  As an engineer introducing Casebench
  I want to start alone and bring lawyers in with no IT ticket
  So that adoption does not wait for a server

  Scenario: From laptop to the cloud
    Given I ran "casebench run" locally with suites and runs in ./.casebench
    When I run "casebench push" and "casebench invite ayse@firm.com --role reviewer"
    Then the lawyer gets an email naming the number of items and the time they take
    And one login from that email opens the queue with those items
    And my agent, my corpus and my keys were never sent

  Scenario: From laptop to a self-hosted team server
    Given a firm that cannot push data outside its network
    When I deploy the same image with Postgres and set the first admin
    And I run "casebench push" against it
    Then the lawyers log in with their roles and see the same data

  Scenario: Approvals come back to CI
    Given lawyers approved 40 drafts and overruled 3 verdicts in the cloud
    When I run "casebench pull"
    Then the 40 cases are approved in my local suite and the 3 reviews replace the judge's scores
    And "casebench gate" in CI scores against the approved cases only

@P0
Feature: Review in a spreadsheet when there is no server
  As a lawyer at a firm with no Casebench login
  I want the answers to review in a spreadsheet
  So that I take part without a server or a cloud

  Scenario: Review round trip
    Given the engineer ran "casebench export --review run-17"
    When I open the XLSX and fill the verdict and note columns, each row linking to its evidence
    And the engineer runs "casebench import reviews.xlsx"
    Then each row becomes a review with my name and time
    And it replaces the judge's verdict exactly as a workbench review would

@P1
Feature: How far can we trust the judge
  As an engineer choosing whether to rely on the judge
  I want to see its agreement with lawyers per criterion
  So that I know where human review is still needed

  Scenario: Agreement screen
    Given lawyers reviewed 200 judged criteria
    When I open judge agreement
    Then I see agreement and Cohen's κ per criterion and per practice area
    And each disagreement links to the case and the lawyer's note
```
