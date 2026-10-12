# Tagging model comparisons

A running record of the test runs that compare vision models on the
photo metadata job (title, caption, alt text, tags, category). One file
per run, newest last. This serves the AI-showcase goal (ADR 0004): the
evidence behind each model choice stays in the open.

These are records, not specs. The model in use is whatever
`api/services/claude_vision.py` says.

## Runs

| Date | Compared | Outcome | Record |
|---|---|---|---|
| 2026-09-28 | Sonnet 4.6 (in use) vs Sonnet 5 | Stayed on Sonnet 4.6: cost equal, Sonnet 5 faster but made two confident errors. Found the alt-text save bug (fixed in #80). | [2026-09-28.md](2026-09-28.md) |
| 2026-10-12 | Haiku 5.5, Sonnet 5.5, Opus 5.5 | Decision pending. Sonnet 5.5 the steadiest; Opus 5.5 saw the most; Haiku 5.5 cheapest with more unconfirmed claims. | [2026-10-12.md](2026-10-12.md) |

## Model in use over time

| From | Model | Avg cost per photo (production log) |
|---|---|---|
| 2025-11-02 | `claude-3-opus-20240229` | $0.0395 over 144 calls |
| 2026-04-08 | `claude-sonnet-4-6` | $0.0104 over 82 calls |

## How to add a run

1. Pick about ten published photos that cover the categories, and keep
   a few from earlier runs so results can be compared across time.
2. Send each photo once per model with the app's unchanged prompt.
   Write nothing to the database.
3. Record the date, models, settings, measured tokens and cost, what
   was checked by eye, and the decision. Add the raw outputs as JSON
   when they are small.
4. Add a row to the table above.
