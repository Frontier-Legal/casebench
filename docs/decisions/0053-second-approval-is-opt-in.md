---
status: accepted
date: 2026-10-15
decision-makers: Casebench maintainers
---

# Until people log in, a lawyer's change to golden data takes effect at once, and a second editor's approval is opt-in

Changes [0052](0052-golden-data-needs-a-second-editor.md), whose approval by a second editor it makes optional. 0052's "try a question" and its daily limit stand.

## Context and problem statement

[0052](0052-golden-data-needs-a-second-editor.md) held every change to golden data until a second editor approved it. Many teams have one lawyer, who could then change no case at all from the workbench. Until team mode adds logins, the workbench knows a person only by the name they type, so the rule could not tell a second lawyer from the first under another name anyway.

## Considered options

1. A second editor's approval is off by default, and `workbench: second_approval: true` in `casebench.yaml` turns it on. Off, a saved change takes effect at once, with its reason in the event log.
2. Keep 0052's rule for everyone.
3. Drop the second approval until team mode.

## Decision outcome

Chosen option 1, because a team of one keeps working and a team that wants two eyes still has them. Option 2 locks a single lawyer out of their own answer key. Option 3 takes the second look away from teams that have the people for it.

- **Off, the default.**
  - A change to a case is written into its suite when it is saved. The suite is frozen again and gets a new hash ([0039](0039-one-case-by-a-lawyer.md)).
  - A case written in the form, or saved from "try a question", is approved by its author, as a case written with `case new` or in a spreadsheet is ([0039](0039-one-case-by-a-lawyer.md), [0049](0049-lawyers-write-cases-in-a-spreadsheet.md)).
- **On.** Changes and new cases wait for a second editor, as [0052](0052-golden-data-needs-a-second-editor.md) describes.
  - A change proposed while it was on can still be approved or rejected after it is turned off.
- **Either way:**
  - A change needs a reason.
  - The event log keeps who, when, before, after and why.
  - The reviewer role changes nothing.
- **Team mode** decides whether its editors must approve each other's changes, once they log in.

### Consequences

- Good, because a team of one lawyer can keep its answer key in the workbench.
- Good, because every change still carries its author, its reason and what it replaced.
- Bad, because with it off, one lawyer's slip changes the scores at once. The event log shows what changed, and a second editor's approval is one line away.

## Revisit when

- Team mode adds logins and roles.
