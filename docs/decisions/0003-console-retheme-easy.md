# 0003 — Console retheme "easy.": cotton-rag and darkroom for the management console

- **Date:** 2026-07-10
- **Status:** accepted
- **PR:** (feature/console-retheme-phase1)

## Context

The management console (`/manage/*` and the shared `admin-common.css` /
`variables.css` foundation it shares with `/admin/*`) still runs the
original blue accent palette (`#0066cc` light, `#0a84ff` dark) and a pill
based nav that reads as a generic SaaS admin panel. The public portfolio
sites moved to a warm, paper and darkroom palette during the visitor
first gallery redesign (0002); the console never followed.

The 2026-03-02 design review recorded a guardrail: "admin UI overhaul:
do not do yet." That freeze predates the public redesign and the sand
accent it introduced. Adrian reviewed a working design brief, published
publicly at `hensler.photography/design.html` under the title "easy.",
and approved it on 2026-07-10, superseding the March freeze for this
specific direction.

## Decision

Retheme the console to the same warm neutral family as the public
sites: cotton rag paper (`#f6f3ec`) in light mode, darkroom (`#171512`)
in dark mode, both built around the brand sand `#e8d5b5` already used
for category links and focus rings on adrian. and liam. Bronze
(`#8a6f47`) carries the accent role on the light theme so it can sit
under white or paper text; sand is used straight on the dark theme.
Playfair Display, lowercase, stays reserved for page titles and the
console wordmark; body copy stays system sans; mono stays reserved for
EXIF and other machine data. The AI stays invisible in console copy: no
"AI" badges or cost language in visitor or photographer facing text.
Every console page gets one primary action per view, with everything
else stepping back into a quiet or overflow control.

`sites/main/design.html` is the living spec, not a frozen mock: it
updates as the console catches up to it, page by page. Rollout is
phased. Phase 1 (this PR) covers `api/static/css/variables.css` token
values, the Google Fonts include for Playfair Display, and the shared
header in `api/static/css/manage-shell.css`. Per page templates
(upload, gallery manager, dashboard, analytics, settings) are later
phases; the admin console (`/admin/*`) inherits the new token values
because it shares `variables.css`, but its own markup is out of scope
here.

## Consequences

- Token names in `variables.css` are unchanged, so no other template
  needed edits to keep working; only the color values moved.
- Several page templates hardcode `color: white` (or similar) on top of
  `var(--accent)` buttons. On the dark theme, `--accent` is now sand,
  a light color, so white text on those buttons is close to illegible.
  Because dark is the console default, phase 1 includes a mechanical
  sweep (19 call sites across the five photographer templates) changing
  those to `color: var(--bg-primary)`, which resolves to dark ink on
  the light backgrounds and paper on the deep ones. Remaining
  `color: white` hits sit on fixed dark or unchanged backgrounds and
  are listed in the PR for phase 2.
- `api/templates/admin/dashboard.html` hardcodes its own
  `--accent`/`--accent-hover` overrides (`#06c` / `#0a84ff`) inside a
  `<style>` block, so the admin dashboard keeps the old blue regardless
  of this change. Flagged for a later phase, not fixed here.
- The active-nav underline uses a fixed sand hex (`#e8d5b5`) directly in
  `manage-shell.css` rather than a new token, matching how
  `design.html` treats `--sand` as constant across both themes while
  `--accent` shifts. A dedicated `--sand` token can be introduced later
  if more surfaces need the same fixed value.
