# Decision Records

Lightweight Architecture Decision Records (ADRs) for choices that shape the
site's behavior, architecture, or process. One file per decision, numbered
sequentially, never edited after acceptance — superseding decisions get a new
record that links back.

**When to write one:** any change where "why did we do it this way?" won't be
obvious from the code or the PR diff six months from now. Bug fixes that
change intended behavior, UX direction changes, dependency choices,
infrastructure shifts.

**When not to:** routine fixes, refactors, content updates. The PR
description is enough.

## Format

```markdown
# NNNN — Short title

- **Date:** YYYY-MM-DD
- **Status:** accepted | superseded by NNNN
- **PR:** #NN

## Context
What situation forced a decision.

## Decision
What we chose, in one or two sentences.

## Consequences
What this makes easier, what it makes harder, what to revisit.
```

## Index

- [0001](0001-gallery-default-scope-data-driven.md) — Gallery default scope is data-driven, not hardcoded featured-only
- [0002](0002-visitor-first-gallery-redesign.md) — Visitor-first gallery redesign: delete the public filter system
