---
title: Roles
description: The five roles on a team server, what each one can do in the workbench, and who can invite whom.
sidebar:
  order: 2
---

On a team server each person has one role. Each role includes everything the one before it can do.

| Role | Can |
| --- | --- |
| **Viewer** | Read the queue, results, reports, history and comparisons |
| **Reviewer** | Also give verdicts, compare versions blind and try questions |
| **Editor** | Also write and change cases, approve colleagues' changes, and approve court drafts |
| **Engineer** | Also open the engineering view of an answer, with the AI's internal steps, and run suites from CI |
| **Admin** | Also invite people, change roles, create keys for CI and set spending limits |

There is always at least one admin. An engineer can invite viewers, reviewers and editors; only an admin invites an engineer or another admin.

Most lawyers are reviewers or editors. A partner who only reads results is a viewer.

## On a colleague's machine

When the workbench runs on an engineer's own computer, there are no accounts. Everyone who opens it can do everything except administer, unless the engineer opened it in review-only mode. That gives everyone the reviewer role: the review view only, with no changes to cases and no approving court drafts.

## Who sees the audit log

Editors, engineers and admins read the audit log: every verdict, every change to the answer key and every team event, with who, when, before, after and why.
