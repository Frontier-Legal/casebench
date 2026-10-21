---
status: accepted
date: 2026-10-20
decision-makers: Casebench maintainers
---

# The workbench is built from shadcn's own components, and charts with shadcn's chart

Adds to [0050](0050-the-review-queue.md) (the web app is built with shadcn/ui), [0065](0065-setting-up-in-the-workbench.md) and [0067](0067-run-history.md).

## Context and problem statement

The setup guide and the History page shipped with pieces made by hand where shadcn/ui has one: a country list, native selects, radio cards, result boxes, list rows and an SVG chart, with decorative blurs around them. People setting Casebench up found the guide slow and inconsistent with the rest of the app, while the stock components elsewhere were not.

## Considered options

1. Use shadcn's component wherever one exists: Command for a searchable list, Select for a choice, RadioGroup with field labels for choice cards, Alert for a result, Item for list rows, Card, Collapsible, and Chart for charts. Add each with the shadcn CLI, at the version the project pins.
2. Keep the hand-made pieces and tune them.

## Decision outcome

Chosen option 1, because the stock components are maintained, accessible and consistent with every other screen, and a hand-made copy is one more thing to keep working. No decoration is added beyond what the components ship.

- **Two dependencies come with them**, at exact versions: `cmdk` 1.1.1, which shadcn's Command is built on, and `recharts` 3.8.0, which shadcn's Chart is built on.

### Consequences

- Good, because every list, choice and chart behaves like the rest of the app, by keyboard and screen reader too.
- Bad, because Recharts adds to the bundle.

## Revisit when

- shadcn ships a component the workbench still builds by hand: then the hand-made one is replaced.
