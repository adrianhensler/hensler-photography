# 0004 — Two co-equal goals: AI showcase and photographers' showcase

- **Date:** 2026-09-28
- **Status:** accepted
- **PR:** (docs/goals-charter)

## Context

The site has been built from two frames of mind. When the work was about
AI skills and tooling, AI capability was enhanced. When it was about
photography, the visitor experience and the console were refined, and
AI was pushed out of sight. With no written statement of goals and no
decision log, the two frames produced rules that contradict each other:

- `sites/main/design.html` (ADR 0003, July) says "No 'AI' in visitor or
  photographer copy" and marks suggestions "until you touch or publish
  them". The first line is not achievable for a site that is openly an
  AI-built project, and the public lightbox already shows an
  "AI-generated description" note. The second quietly made publishing
  count as human approval.
- The original intent was that AI-generated metadata stays labelled
  until a human reviews it. The mechanism survives (per-field
  `ai_generated_*` flags, `ai_disclosure` in the public API, the
  lightbox note), but `PATCH /api/images/{id}` clears a field's flag
  whenever the field is *sent*, changed or not. The gallery manager's
  Save always sends every text field, and upload's Publish saves first,
  so unread text loses its label. Upload never shows alt text, so it is
  never reviewed before a photo goes public.

## Decision

The project has two co-equal goals, recorded in CLAUDE.md "Project
Direction":

1. **AI showcase:** the site is openly an AI-built project.
2. **Photographers' showcase:** a marketable home for the
   photographers' work, eventually selling prints.

Principles that reconcile them, superseding design.html's "the
intelligence is invisible":

- **AI is honest, never hidden.** Visitors can tell AI-drafted text from
  human-reviewed text.
- **The photograph is the loudest thing.** Provenance is a quiet note,
  not a badge. Console chrome has no robot badges and no cost talk.
- **Humans review AI output.** AI-drafted fields stay marked (the sand
  dot in the console, a quiet lightbox note for visitors) until a person
  edits them or explicitly approves them. **Publishing is allowed while
  fields are unreviewed, and does not count as approval.**
- **Decisions are recorded.** Goal-affecting changes get an ADR, and
  console changes update design.html's change log.

Copy ruling: the setting that picks the metadata voice is called
**Writing style** everywhere (settings and gallery manager).

## Consequences

- Follow-up code PR: PATCH clears a flag only when the value actually
  changes; a new explicit Approve action clears flags without edits;
  upload shows alt text and server-driven dots; the gallery manager gets
  a "Needs review" filter; the lightbox note is restyled and kept.
- Photos already published had their flags cleared by the old
  publish-equals-approval behaviour. Which ones a human actually read
  cannot be recovered. They are left as they are; a one-time "mark for
  re-review" reset is available on request, with a DB backup first.
- Review bots and future sessions should check visitor-facing and
  AI-related changes against both goals, not just one.
