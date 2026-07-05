# 0002 — Visitor-first gallery redesign: delete the public filter system

- **Date:** 2026-07-05
- **Status:** accepted
- **PR:** (feature/visitor-first-gallery)

## Context

The public gallery exposed ~165 interactive controls to visitors of a
35-photo portfolio: browse/refine discovery modes, intent pills, a
featured/all scope toggle (a CMS curation flag), all ~147 AI-generated
tags as filter pills, conjunctive tag logic, and an empty-state
suggestion engine built to recover from dead-ends the UI itself
created. An expert design review (2026-07-05) found the page built
like an image database admin tool pointed at consumers, and Adrian
requested a complete redesign toward a public, marketable site.

The 2026-03 review's guardrail froze filter UI changes pending
analytics; Adrian explicitly overrode that freeze with this request.

## Decision

Delete the public filter system rather than iterate on it. The visitor
surface is: full-bleed hero slideshow (ghost title overlaid), one
category row ("all" + categories having ≥ 3 published images, no
counts), a justified grid driven by API `aspect_ratio`, and a
metadata-rich lightbox. `?category=` is the only public filter state.
Featured becomes hero curation only. Tags become lightbox metadata
only. Both portfolio sites share the identical structure.

## Consequences

- gallery.js drops from 1727 to ~670 lines; the empty-state engine,
  discovery modes, intent heuristics, and tag logic are unreachable
  by construction rather than defended by fallbacks.
- Old deep links with `?featured=`, `?tag(s)=`, `?tagMatch=`, `?mode=`
  degrade gracefully (unknown params are ignored; the page renders all
  published images).
- Liam's site reaches API parity with Adrian's, closing the
  maintenance split flagged in the 2026-03 review.
- Categories need curation in the gallery manager: buckets with < 3
  images don't appear in public navigation.
- The per-image analytics events (impression/click/lightbox/scroll)
  are preserved, so the 6-week "did anyone use filters" question the
  old guardrail asked can still be answered for the category row.
