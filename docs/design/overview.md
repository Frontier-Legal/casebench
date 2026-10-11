# Casebench overview

## Summary

- Casebench is an open-source framework that helps legal AI builders and legal teams test and prove the accuracy of their AI, using their own jurisdiction's court decisions as the answer key.
- Its unit is an evaluation case: a task (Q&A, research, drafting, editing, extraction), a reference to grade against, and the metrics to apply. A reference comes from a court decision, a lawyer, expected fields, or a mix ([architecture.md](architecture.md)).
- From court decisions the user already holds, Casebench builds references automatically: what the court ruled, which statutes it applied, which precedents it relied on. Lawyer-authored cases come in through a spreadsheet.
- It reaches the AI under test through its API, its MCP server, a Python function or an exported file, and checks every citation in every answer against the corpus. If the target sends a trace, it also shows where in the harness the right authority was lost ([harness-eval.md](harness-eval.md)).
- The report shows each metric per task and per reference source, never one blended score, with every failure next to its evidence.

## Problem

Legal AI vendors and the firms that buy or build legal AI cannot say how often it gets the law wrong.

- Leading tools still do. Stanford RegLab measured Lexis+ AI hallucinating on 17% of queries and Westlaw AI-Assisted Research on 33% ([RegLab](https://reglab.stanford.edu/publications/hallucination-free-assessing-the-reliability-of-leading-ai-legal-research-tools/)). HAQQ graded 3,000 answers and found 24% cited law that does not say what the model claimed ([HAQQ](https://www.haqq.ai/blog/best-ai-for-legal-work-benchmark)).
- Generic eval tools (Langfuse, LangSmith, Braintrust) store traces and run LLM judges. Their answer keys come from an LLM or from the user, and in legal work "from the user" means lawyer hours.
- Public legal benchmarks are fixed sets, mostly English and US-centred (LegalBench, Harvey LAB). Models may have trained on them, and they say nothing about Turkish, French or Brazilian law. We found no Turkish legal QA benchmark ([HukukBERT paper](https://arxiv.org/html/2604.04790v1)).
- The rigorous legal evaluations are closed: Vals AI, Thomson Reuters' use of Scorecard, Legora BAR. A small vendor, or a firm building on GPT or Claude, cannot run them on its own corpus.
- Buyers now ask for evidence, and vendors answer with self-run benchmarks that nobody else can reproduce.

## The insight

A court decision is already a labelled example. Its operative part is the correct outcome. Its citations are the correct statutes and precedents. Its date fixes which statute version applied. A judge wrote all of it.

Casebench reads those labels out of decisions the user already holds, so an answer key costs extraction compute instead of lawyer hours. Decisions keep arriving every day, so a user with a current corpus can always build tests from decisions published after a model's training cutoff.

## Goals

1. A vendor engineer gets a first report on their own corpus in one working session, with no help from the maintainers.
2. Every score links to the evidence behind it: the court record or the lawyer's reference.
3. A new jurisdiction costs no code: models read its decisions and the corpus resolves its citations.
4. A third party with the suite id and the same corpus snapshot reproduces a published result.
5. The agent, the corpus and the API keys never leave the user's machines. Full decision text goes only to the AI under test and the judge the user picked. The shared place receives cases, outputs, scores, evidence excerpts and reviews, and never computes a score ([decision 0005](../decisions/0005-cloud-never-computes-a-score.md)).

## Non-goals

- A tracing or observability platform for production. Casebench keeps only the traces that explain eval results, shown per model call and tool call in the harness view. It needs no Langfuse, LangSmith or Inspect, and can export to them.
- Grading drafting, editing or advice without an evidenced reference. Court records do not label those; a lawyer-authored reference can.
- Shipping any corpus. Users bring their own data, Türkiye included.
- A leaderboard. The project publishes no rankings of products.
- A runtime guardrail in the first releases. A citation-check API called before an answer reaches a lawyer is a later product ([releases.md](releases.md), R3).
- Replacing lawyer review. The report states what court records can prove and names what they cannot.

## Users

| Persona | Their job | What they need from Casebench |
|---|---|---|
| Vendor AI engineer | ships a legal AI product in one or more countries | a regression gate in CI, an error breakdown, a number buyers can verify |
| Firm builder | runs an in-house assistant on GPT or Claude | test it on the firm's practice areas without touching its code |
| Buyer (general counsel, innovation lead, procurement) | chooses between vendors | the same suite run against each vendor, on their own corpus, in a report a partner can read |
| Security officer | approves tools near client data | proof that nothing leaves the perimeter |
| Plugin contributor | engineer at a data provider or in another country | a documented plugin interface and a conformance test |
| AI lab evaluator | tests models on non-English law | suites limited to decisions after the model's cutoff, in a standard result format |

## Principles

- Evidence writes the answer key: the court where a decision exists, a lawyer where it does not. An LLM judge grades only what exact scoring cannot, always against that evidence.
- The grader never asks the system it grades. Citation checks read raw decisions, never the AI under test.
- Show the failing example next to every rate.
- No score is reported without its baseline and its confidence interval.
- There is no country-specific code: models read, the corpus resolves.
- Court-derived, never "synthetic". No LLM invents a question or an answer. The question is what the court was asked, the answer is what it ruled, and every fact points at a passage in the decision.
- Lawyers are first-class users. The workbench ([workbench.md](workbench.md)) ships with the library, and every review is done in legal terms, never in spans or JSON. Their first session is a queue of answers to review, reached from an email invite with nothing to install. Authoring golden data comes after.
