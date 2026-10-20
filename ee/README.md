# casebench-ee

Casebench's team server: the workbench with sign-in, five roles, an audit log and admin pages ([decision 0058](https://github.com/Frontier-Legal/casebench/blob/main/docs/decisions/0058-the-team-server.md)).

Licensed under the [Elastic License 2.0](https://github.com/Frontier-Legal/casebench/blob/main/ee/LICENSE). Everything outside `ee/` is Apache-2.0.

## Run it

Install it from PyPI, with the `casebench` release of the same version, and start it in a folder holding your runs, suites and `casebench.yaml`:

```bash
pip install casebench-ee
CASEBENCH_DATABASE_URL=postgresql://casebench:secret@db.internal/casebench \
CASEBENCH_PUBLIC_URL=https://casebench.firm.example \
casebench-team serve --host 0.0.0.0
```

Without `CASEBENCH_DATABASE_URL` it keeps the team in `.casebench/team.db`, SQLite, which is enough for a trial.

Or build the container image from the repository's root, and run it with Postgres and a folder holding your runs, suites and `casebench.yaml`:

```bash
docker build -f ee/Dockerfile -t casebench-team .
docker run -p 8080:8080 \
  -e CASEBENCH_DATABASE_URL=postgresql://casebench:secret@db.internal/casebench \
  -e CASEBENCH_PUBLIC_URL=https://casebench.firm.example \
  -v /srv/casebench:/data \
  casebench-team
```

The first start prints a one-time setup code to the log. Open the public URL, enter the code, and create the first admin with a password of 12 characters or more that is no default.

## Settings

| Variable | What it sets |
|---|---|
| `CASEBENCH_DATABASE_URL` | Postgres for a team; SQLite works for a trial |
| `CASEBENCH_PUBLIC_URL` | where people open the app; sign-in links point here |
| `CASEBENCH_SMTP_HOST`, `_PORT`, `_USERNAME`, `_PASSWORD`, `_FROM`, `_SECURITY` | the SMTP server that sends sign-in links; `_SECURITY` is `starttls` (default), `tls` or `none`. Without it, the admin copies each link from the Team page |
| `CASEBENCH_GOOGLE_CLIENT_ID`, `_SECRET` | sign-in with Google, for invited emails Google has verified |
| `CASEBENCH_MICROSOFT_CLIENT_ID`, `_SECRET` | sign-in with Microsoft, for invited emails Microsoft vouches for: personal accounts, or work accounts whose domain is verified |
| `CASEBENCH_RUNS`, `CASEBENCH_SUITES`, `CASEBENCH_CONFIG` | where runs, suites and `casebench.yaml` are; `/data/...` in the image |

Register the Google or Microsoft client with `<public URL>/auth/google/callback` or `<public URL>/auth/microsoft/callback` as its redirect address.

## Erasing a team

`casebench-team erase --database URL --runs-dir DIR --suites DIR --confirm NAME` removes every table in the team's database, with the audit log, and everything in its run and suite folders. `NAME` is the database's name, typed back. What is erased cannot be restored.

## Organisations

A server keeps each organisation's rows apart in Postgres itself, with row-level security, and each organisation's runs and suites in folders of its own ([decision 0066](../docs/decisions/0066-one-shared-cloud.md)). A self-hosted server has one organisation and needs nothing set. A service serving several adds them with `Team.add_organisation`, and must connect as a Postgres role that is no superuser and has no `BYPASSRLS`; otherwise the server refuses a second organisation. `casebench_ee.hosting.erase_organisation` removes one organisation's rows and folders and leaves the others.

## From an engineer's machine

Create an API key with the engineer role on the Team page, set it as `CASEBENCH_CLOUD_KEY` on the engineer's machine, and name the server in `casebench.yaml` under `cloud: url:`. Then `casebench push`, `casebench invite` and `casebench pull` work against it ([decision 0059](https://github.com/Frontier-Legal/casebench/blob/main/docs/decisions/0059-push-invite-pull.md)).

## Develop

`uv sync` installs `casebench-ee` with the core. `npm run build:team` in `workbench/` builds the team's web app into `ee/casebench_ee/static/`. `uv run pytest ee/team_tests` runs its tests; set `CASEBENCH_TEST_POSTGRES` to a Postgres server's URL to run the Postgres ones too.
