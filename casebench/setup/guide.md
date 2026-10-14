# Set up Casebench for this project

You are a coding agent. The user asked you to set up Casebench (version @VERSION@) so it can measure the legal accuracy of the AI agent in this project. Follow these steps in order. When every step is done, `casebench check` passes, or you can say in plain words what cannot pass from here.

## Rules

- **Create only `casebench.yaml` and files under `.casebench/`.** Do not change any other file: not the agent's code, not `pyproject.toml`, not a lockfile, not `.gitignore`. If something seems to need a change elsewhere, stop and tell the user instead.
- **Never read, print or copy a value from a `.env` file**, a key or anything else. Do not open `.env` files; their `.env.example` files show the names. To learn where a variable is kept, run `casebench keys NAME`; it prints file names and fingerprints, never values. Where Casebench needs a value from such a file, such as a URL, give the variable by name, as `${NAME}`.
- **Run Casebench without installing it into the project.** In a uv project, run every command as:

  ```
  uv run --with "@SPEC@" casebench <command>
  ```

  Run it from the project's folder, or add `--directory <project>` after `uv run`. This runs Casebench with the project's own dependencies, as the agent needs them; in a uv project that has no `.venv` yet, uv creates one, which uv projects ignore. In a project that uses pip, install it into the project's virtual environment with `pip install "@SPEC@"` and run `casebench <command>`. Below, `casebench` stands for whichever form applies.
- **`casebench.yaml` is yours to edit.** To redo a corpus, delete its block under `corpora:` and add it again. `--key NAME=FILE` takes a path relative to the project's folder.
- **Spend little, and only once.** Many document stores and every model charge per call. These are the only commands here that call out, and what each spends:
  - `casebench corpus probe http`: 1 search for 1 result with `--query`, 1 document with `--fetch`.
  - `casebench corpus add http`: 1 search for 1 result, and 1 document.
  - `casebench check`: 1 search for 1 result and 1 document, 1 message to the agent ("Hi. How are you?"), and 1 short call to each judge.

  Run each when a step calls for it and not again to look around; after a failure, fix what it said and run it once more. Never run `casebench corpus check` or `casebench run` during setup.
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
- Then call the function production calls, and return its final answer. Return a string, or a mapping with `answer` and, if the agent gives them, `citations` (a list of citation strings) and `documents` (a list of document ids). Leave out what the agent does not give; Casebench reads the recorded calls too.
- `facts`, when given, holds the case's facts as text. Pass it the way the agent takes extra context, or add it to the question.
- Casebench puts the project's folder first on the import path, so `import` the project's packages as code at the project's root does.
- Leave the agent's base URLs and keys as its settings set them. Casebench records each model and search call where it goes, without changing where it goes.
- Keep the file short. It is an adapter, not a copy of the agent.

Also create `.casebench/.gitignore` containing exactly:

```
*
!.gitignore
!target.py
```

This keeps runs and caches out of git and keeps the adapter in it.

## 3. Locate what Casebench reads itself

Casebench reads a few variables for its own calls: the judge's key, the document store's key, and the store's URL when the project keeps it in a variable. The agent's own settings are the adapter's business, not Casebench's; do not list them. For each variable Casebench will read, from the agent's code or the project's `.env.example` files, run:

```
casebench keys NAME --json
```

- If `values_agree` is false, the files disagree. Ask the user which file is current, and pass `--key NAME=FILE` to every command below that needs that key.
- If no file has the name and it is not set in the shell, tell the user which variable to set and where.

## 4. Choose the judge

The judge grades the agent's answers, so it costs money on every run.

- Find which models the agent itself uses, from the model names in its code or settings.
- `casebench models --json` lists the catalog's providers, with the variable each one's key is read from; `casebench models PROVIDER --json` lists that provider's models, with their family, price per million tokens and context. Take both ids from there.
- Propose a strong model from a different family than the agent's models, through a provider whose key you found in step 3. A judge from the agent's own family tends to favour its answers.
- **Ask the user once** to confirm the provider and model, and say the provider will be billed for each run. This is the only question you ask the user, apart from keys whose files disagree.

Both ids are the model catalog's (models.dev), as `casebench models` lists them.

## 5. Write the setup

```
casebench init --entry .casebench/target.py:answer --corpus none \
  --judge-provider PROVIDER --judge-model MODEL --no-extract --no-routes --no-live --yes \
  [--key NAME=FILE ...]
```

This writes `casebench.yaml`: the target, the judge, and under `keys` the name and file of each key, never a value. Model calls need no route for a Python target: Casebench records each call where the agent sends it.

## 6. Connect the document store

Casebench checks every citation against the documents the agent's own search uses. Find, in the agent's code, the store it searches: its base URL, search path, query parameter, fetch path, and the variable and header that carry its key. When the code reads the base URL from a variable, such as `DOCS_URL`, give `--base-url '${DOCS_URL}'` in single quotes; Casebench reads it from the same file as a key, and `casebench.yaml` names it rather than holding it.

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
   - `--field id=…`, `jurisdiction=…`, `court=…`, `date=…`, `text=…` (the full text), and `level=…` only if the document states where the court sits in the hierarchy, such as first instance, appeal or supreme court; a field such as `national`, which says how far a jurisdiction reaches, is not it. Paths are relative to the fetched document. A filter such as `$.dates[?(@.type=='decided')].date` picks one of several entries.
   - `--jurisdiction CODE` for each country or region the store covers, as ISO 3166 codes such as `TR` or `US-CA`.

4. Add it:

   ```
   casebench corpus add http --base-url URL --search-path /search --query-param q \
     --fetch-path "/documents/{id}" --key-env KEY_NAME --probe "the same topic" \
     --results … --result-field … --field … --jurisdiction CODE --name NAME --yes [--key NAME=FILE]
   ```

   `--name` is how reports name the store, such as the provider's name, in lowercase letters, digits and hyphens, such as `frontier-legal`; without it, a name is made from its host.

For a folder of decisions, use `casebench corpus add folder`; for an MCP server, `casebench corpus add mcp`. Run either with `--help` for its flags.

## 7. Check, and fix what fails

```
casebench check --json
```

Each part has `passed`, a `reason` and the `next` step. The agent is sent "Hi. How are you?": an answer without an error shows it starts and answers. Setup needs nothing more from it. Fix the adapter or the flags you gave, and run it again. Stop and tell the user only what you cannot fix from here, such as a service that is not reachable from this machine or a key that is refused.

## 8. Show the user what changed

Run `git status --short`. Only `casebench.yaml` and `.casebench/` may appear. Then tell the user:

- what the adapter calls and which settings it loads;
- the judge you set and that it is billed per run;
- the corpus you connected;
- the result of `casebench check`;
- the next step: a lawyer writes a first case with `casebench case new --suite first`, then `casebench run --suite first` asks the agent and grades it.
