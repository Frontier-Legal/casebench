---
name: casebench-setup
description: Set up Casebench for the legal AI agent in this repository and run its first evaluation. Use when the user asks to set up, connect or evaluate their legal agent with Casebench, or to measure how accurately it cites the law.
---

# Set up Casebench and run the first evaluation

Casebench measures the legal accuracy of the agent in this repository: whether each authority it cites exists in the team's corpus and says what the answer claims. This skill sets it up, runs a first evaluation and opens the results.

## 1. Follow the guide

Run:

```
uvx casebench guide
```

It prints the setup steps for the installed version, and the exact command to run Casebench with in this project. Follow them in order. They hold the rules that matter most:

- create only `casebench.yaml` and files under `.casebench/`;
- never read, print or copy a value from a `.env` file;
- spend little: each command that calls out says what it spends.

Answer every question you can from the repository: which function answers a legal question, how production loads its settings, which document store the agent searches, and which models it calls. Ask the user only two things:

1. **Where the court decisions are**, when the code does not show which store the agent searches.
2. **Which models to pay for.** Propose a judge from a different model family than the agent's, and two extraction models from two different families, as the guide says. Say the judge is billed for each run, and the extraction models when the first run builds its suite.

The guide ends when `casebench check` passes, or when you can say in plain words what cannot pass from here. Below, `casebench` stands for the command the guide told you to run it with.

## 2. Run the first evaluation

Setup is done; the guide's rule against running `casebench run` covered setup only. A first evaluation needs a suite of cases. Without one, `casebench run` builds it from the corpus: the two extraction models the guide's setup named read a sample of decisions, and their agreed findings become cases.

1. Run `casebench run` with no `--suite`. It prints what extraction will cost and how many cases it will send, then stops, because nothing answers its question.
2. Show the user that estimate and ask whether to go on. Apart from the team server question in step 4, this is the only other question you ask.
3. When the user agrees, run `casebench run --yes`. It extracts, generates the suite, sends each case to the agent and scores the answers. If it stops partway, run `casebench run` again: it resumes.

When the user would rather start from lawyer-written cases, use `casebench case new --suite first` or the spreadsheet `casebench template lawyer` writes, and then `casebench run --suite first`.

## 3. Open the results

Run `casebench ui`. The workbench opens on this machine with the failed answers first, each beside the passage it cited.

Then tell the user:

- what the adapter calls and which settings it loads;
- the corpus and the judge that are set;
- what the run found: its error rates, and the first failed answer;
- that `git status --short` shows only `casebench.yaml` and `.casebench/` as changed.

## 4. Ask about a team server

Lawyers who review on another machine need a team server: the workbench with sign-in, on a machine they can reach. Ask the user once: **will lawyers review on a team server?** Then follow "A team server" at the end of the guide:

- **Not now:** change nothing; lawyers review here with `casebench ui`.
- **They have one:** ask its address and run `casebench init --team-server URL --no-routes --yes`. Ask the user to set `CASEBENCH_CLOUD_KEY` themselves, to an engineer key an admin makes on the server's Team page; never ask for it or handle it. Run `casebench check`, then `casebench push`, and offer `casebench invite` for each lawyer they name.
- **They want one:** give them the commands the guide lists for the machine lawyers reach. Install it only if the user asks you to and you have access to that machine.

## Without a project of its own

`uvx casebench demo` runs a bundled suite with no key and asks no model, and opens the workbench on it. Like every run, it reads two public price lists. Use it when the user wants to see Casebench before connecting their agent.
