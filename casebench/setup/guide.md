# Set up Casebench for this project

You are a coding agent. The user asked you to set up Casebench (version @VERSION@) so it can measure the legal accuracy of the AI agent in this project. Follow these steps in order. When every step is done, `casebench check` passes, or you can say in plain words what cannot pass from here.

## Rules

- **Create only `casebench.yaml` and files under `.casebench/`.** Do not change any other file: not the agent's code, not `pyproject.toml`, not a lockfile, not `.gitignore`. If something seems to need a change elsewhere, stop and tell the user instead.
- **Never read, print or copy a key's value.** Do not open `.env` files. To learn where a key is kept, run `casebench keys NAME`; it prints file names and fingerprints, never values.
- **Run Casebench without installing it into the project.** In a uv project, run every command as:

  ```
  uv run --with "@SPEC@" casebench <command>
  ```

  In a project that uses pip, install it into the project's virtual environment with `pip install "@SPEC@"` and run `casebench <command>`. Below, `casebench` stands for whichever form applies.
- **Commands never prompt.** If a command stops with "nothing here can answer it; give it with …", it names the flag to add. Do not pipe answers into it.

## 1. Find how the agent answers and how it starts

Read the project and answer two questions for yourself:

1. **Which function does production call with a user's legal question?** Find the function behind the API route, the chat handler or the command line, not a helper or a test.
2. **What does production do before that function can run?** Look for the settings it loads, such as `.env` files read by a settings class, `load_dotenv`, `--env-file`, a systemd `EnvironmentFile`, a Docker `env_file`, or a start script that exports variables. Also note what it needs on the import path.

## 2. Write the adapter

Create `.casebench/target.py` with one function:

```python
def answer(question: str, facts: str | None = None) -> str | dict: ...
```

- First, do what production does before it answers. Load the same settings, the same way, for example by calling the project's own settings loader or loading the same `.env` files into `os.environ`. Do not print or log any value.
- Then call the function production calls, and return its final answer. Return a string, or a mapping with `answer` and, if the agent gives them, `citations` (a list of citation strings) and `documents` (a list of document ids).
- `facts`, when given, holds the case's facts as text. Pass it the way the agent takes extra context, or add it to the question.
- Casebench puts the project's folder first on the import path, so `import` the project's packages as code at the project's root does.
- Keep the file short. It is an adapter, not a copy of the agent.

Also create `.casebench/.gitignore` containing exactly:

```
*
!.gitignore
!target.py
```

This keeps runs and caches out of git and keeps the adapter in it.

## 3. Locate the keys Casebench needs

Casebench needs a key for the judge model and, usually, one for the document store. For each key name you find in the agent's code or the project's `.env.example` files, run:

```
casebench keys NAME --json
```

- If `values_agree` is false, the files disagree. Ask the user which file is current, and pass `--key NAME=FILE` to every command below that needs that key.
- If no file has the name and it is not set in the shell, tell the user which variable to set and where.

## 4. Choose the judge

The judge grades the agent's answers, so it costs money on every run.

- Find which models the agent itself uses, from the model names in its code or settings.
- Propose a strong model from a different family than the agent's models, through a provider whose key you found in step 3. A judge from the agent's own family tends to favour its answers.
- **Ask the user once** to confirm the provider and model, and say the provider will be billed for each run. This is the only question you ask the user, apart from keys whose files disagree.

The provider and model ids are the model catalog's (models.dev), such as `--judge-provider openrouter --judge-model anthropic/<model>`.

## 5. Write the setup

```
casebench init --entry .casebench/target.py:answer --corpus none \
  --judge-provider PROVIDER --judge-model MODEL --no-extract --routes --no-live --yes \
  [--key NAME=FILE ...]
```

This writes `casebench.yaml`: the target, the judge, a capture route for each model client the code creates, and under `keys` the name and file of each key, never a value.

## 6. Connect the document store

Casebench checks every citation against the documents the agent's own search uses. Find, in the agent's code, the store it searches: its base URL, search path, query parameter, fetch path, and the variable and header that carry its key.

For an HTTP API:

1. Search once and read the response:

   ```
   casebench corpus probe http --base-url URL --search-path /search --query-param q \
     --fetch-path "/documents/{id}" --key-env KEY_NAME --query "a real legal question topic"
   ```

2. Pick a document id from the response, and fetch it:

   ```
   casebench corpus probe http ...the same flags... --fetch ID
   ```

3. From the two responses, write the mapping. Use JSONPaths taken from the responses you saw, not guessed ones:
   - `--results`: each result in the search response, such as `$.results[*]`.
   - `--result-field id=…`, `citation=…` (how the store cites the document; prefer the fullest form), `type=…` (what kind of document), `passage=…` (the text the search matched). Paths are relative to one result.
   - `--field id=…`, `jurisdiction=…`, `court=…`, `date=…`, `text=…` (the full text), and `level=…` only if the document states the court's level. Paths are relative to the fetched document.
   - `--jurisdiction CODE` for each country or region the store covers, as ISO 3166 codes such as `TR` or `US-CA`.

4. Add it:

   ```
   casebench corpus add http --base-url URL --search-path /search --query-param q \
     --fetch-path "/documents/{id}" --key-env KEY_NAME --probe "the same topic" \
     --results … --result-field … --field … --jurisdiction CODE --yes [--key NAME=FILE]
   ```

For a folder of decisions, use `casebench corpus add folder`; for an MCP server, `casebench corpus add mcp`. Run either with `--help` for its flags.

## 7. Check, and fix what fails

```
casebench check --json
```

Each part has `passed`, a `reason` and the `next` step. Fix the adapter or the flags you gave, and run it again. Stop and tell the user only what you cannot fix from here, such as a service that is not reachable from this machine or a key that is refused.

## 8. Show the user what changed

Run `git status --short`. Only `casebench.yaml` and `.casebench/` may appear. Then tell the user:

- what the adapter calls and which settings it loads;
- the judge you set and that it is billed per run;
- the corpus you connected;
- the result of `casebench check`;
- the next step: a lawyer writes the first case with `casebench case new --suite first`, then `casebench run --suite first` asks the agent and grades it.
