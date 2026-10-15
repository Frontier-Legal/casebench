# SPDX-License-Identifier: Elastic-2.0
# The team server in one image: casebench and casebench-ee, with the team build of the web app
# (decision 0058). Build from the repository's root: docker build -f ee/Dockerfile .
#
# Configured through the environment:
#   CASEBENCH_DATABASE_URL   postgresql://user:password@host/database
#   CASEBENCH_PUBLIC_URL     where people open the app, such as https://casebench.firm.example
#   CASEBENCH_SMTP_HOST, _PORT, _USERNAME, _PASSWORD, _FROM, _SECURITY   sign-in links by email
#   CASEBENCH_GOOGLE_CLIENT_ID, _SECRET; CASEBENCH_MICROSOFT_CLIENT_ID, _SECRET   optional sign-in
# Runs, suites and casebench.yaml are read from /data, a volume.

FROM node:22-slim@sha256:c3de60bf2f9dd0ac6370e6117950ff62d6e339527e7472301c9c78a017978392 AS web
WORKDIR /src
COPY workbench/package.json workbench/package-lock.json workbench/
RUN cd workbench && npm ci --ignore-scripts
COPY workbench workbench
COPY ee/web ee/web
RUN cd workbench && npm run build && npm run build:team

FROM python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f AS wheels
COPY --from=ghcr.io/astral-sh/uv:0.12.7@sha256:95f2aa1fe59274951cfe9b0cbc7972e879ff1004bc8945d130a32eb0dbd85945 /uv /bin/uv
WORKDIR /src
COPY . .
COPY --from=web /src/casebench/workbench/static casebench/workbench/static
COPY --from=web /src/ee/casebench_ee/static ee/casebench_ee/static
RUN uv build --package casebench --wheel --out-dir /wheels \
    && uv build --package casebench-ee --wheel --out-dir /wheels

FROM python:3.13-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f
COPY --from=wheels /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels \
    && useradd --create-home --uid 10001 casebench && mkdir /data && chown casebench /data
USER casebench
WORKDIR /data
ENV CASEBENCH_HOST=0.0.0.0 \
    CASEBENCH_PORT=8080 \
    CASEBENCH_RUNS=/data/runs \
    CASEBENCH_SUITES=/data/suites \
    CASEBENCH_CONFIG=/data/casebench.yaml
VOLUME ["/data"]
EXPOSE 8080
CMD ["casebench-team", "serve"]
