# 0001 — Gallery default scope is data-driven, not hardcoded featured-only

- **Date:** 2026-07-05
- **Status:** accepted
- **PR:** (fix/gallery-featured-empty-default)

## Context

The public gallery defaulted to a hardcoded `featuredOnly = true` scope. In
production, 35 images are published but zero are marked featured, so every
first-time visitor saw a "No images found" empty state directly beneath a
working hero slideshow (which has its own fallback to all published images).
Category and tag filter pills also rendered empty, because facets are
aggregated from the featured-scoped dataset.

A gallery must be structurally incapable of opening empty.

## Decision

The default scope is derived from the data: featured-only when at least one
published image is featured, otherwise all images. This applies to the
initial load, URL-state reset, `clearFilters()`, the "start here" intent, and
URL serialization (only a non-default scope appears as a `?featured=` param).
An explicit `?featured=true` URL is still honored even when it yields zero
results.

## Consequences

- The gallery always opens populated; marking/unmarking featured images in
  `/manage/gallery` changes the default scope without a deploy.
- `?featured=false` links copied before this change still work; they now
  resolve to the same view as the default when nothing is featured.
- The `tests/url-filters.spec.js` featured-toggle test was updated to assert
  the new data-driven contract.
- The 2026-03 review's brand guardrail froze filter UI pending analytics; the
  owner explicitly overrode that freeze on 2026-07-05 by requesting a gallery
  redesign. This fix is the minimal correctness patch ahead of that redesign,
  which is expected to remove the public featured/all toggle entirely.
