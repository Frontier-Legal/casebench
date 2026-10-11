# Security policy

## Reporting a vulnerability

Report a vulnerability through GitHub's private vulnerability reporting: open the repository's **Security** tab and choose **Report a vulnerability**. Never report it in a public issue, discussion or pull request.

A maintainer sends a first response within 14 days. The response says whether the report is accepted, what happens next and when to expect the next update.

## Supported versions

Casebench is in 0.x. Only the latest release receives security fixes.

## What Casebench promises

- Nothing leaves your machines except calls to the system under test and the judge or extraction models you configured. There is no telemetry.
- API keys are read from the environment or the system keyring. They are never written to config files, logs or run logs.
- Model output is data. Casebench never evaluates, executes or unpickles it, and loads YAML with a safe loader only.
- Releases on PyPI carry attestations produced by Trusted Publishing from this repository's release workflow.

A gap in any of these is a vulnerability. Please report it.
