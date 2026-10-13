# Isolated print shop demonstration

Prepared 2026-10-13 from `main` at `0995d8cd510b1705de04f63b5565ea21de961246`.

Proposed URL: `https://adrian.hensler.photography/shop-preview/`.

This is a public, unlinked design study, not a shop. It has no checkout, payment,
onboarding, customer-data fields, account changes, storage, tracking or financial
API calls. Its conspicuous banner links back to the existing real gallery. It
sets `noindex, nofollow, noarchive`; this is indexing guidance, not privacy or an
access restriction. No private material belongs here.

## Scope and design

Only `sites/adrian/shop-preview/{index.html,preview.css,preview.js,geometry.js}`
adds visitor-facing behavior. No existing site, stylesheet, script, navigation,
sitemap, API route, authentication, database, Caddy or Compose file is changed.
The study uses the existing gallery's dark ground, sand accent, Inter and
Playfair typography. Images remain the strongest visual element.

Photographer records form a registry; the interaction is not conditional on
exactly two people. Adding an independently hosted seller concept requires
adding their public-gallery identity and samples to that registry. Products,
gallery source and proposed payment ownership stay scoped to the selected
photographer. This small mock starts with Adrian and Liam, without inventing a
third person's identity or photographs. A production platform would need a
persistent seller/product model; this registry is not that backend.

Published photographs and their current URLs are read at runtime from the
existing public gallery GET endpoint (`credentials: omit`). No photo files or
metadata snapshots are added to this patch. Curated public IDs are preferred;
if none remain published, up to four current published images are used. Image
paths are restricted to the existing same-origin gallery asset path. Metadata
is inserted as text. Changing photographers aborts any previous gallery request
and clears the previous photograph, collection and demonstration messages.

The full selected photograph and thumbnails keep their intrinsic proportions.
No extra crop, stretch, alteration or generated photographic assets are used.
The frame study uses `object-fit: contain`, preserving even the slight
integer-rounding differences in resized WebP variants.

Physical dimensions derive from integer source `width`/`height`, not the API's
rounded `aspect_ratio`. A selected image long edge of 20/30/40 cm scales the
other image dimension proportionately. The paper adds a 2 cm border on all
sides; a mat adds 5 cm outside the paper; a frame face adds another 2 cm outside
the mat. The diagram and dimension table share this calculation. All physical
sizes, materials and CAD prices are illustrative, not approved products or
offers. Pixel dimensions, image area, paper, mat and frame outer sizes are
labelled separately. Supplier tolerances, mat openings/overlap, print quality,
availability, tax, shipping and fulfilment remain unresolved.

The payment section is a proposed seller-owned state, separate from the actual
management console. It describes Stripe-hosted onboarding, a full seller Stripe
dashboard and direct charges. Both action buttons only reveal explanatory text.
They never open Stripe, request keys or change any state outside this page.
One photographer per conceptual order keeps ownership clear. A cross-seller
cart is unresolved. Financial independence cannot ensure hosting or succession
continuity. Actual implementation should assess current Accounts v2 full
dashboard configurations rather than blindly using legacy `type=standard`.

Stripe references for later design work (no integration in this change):
- https://docs.stripe.com/connect/hosted-onboarding
- https://docs.stripe.com/connect/stripe-dashboard
- https://docs.stripe.com/connect/charges

## Verification

`tests/shop-preview.spec.js` uses only intercepted, synthetic gallery responses
and test image shapes. It checks physical geometry, 10:1 and 1:10 extremes,
square, portrait and landscape; widths 320/390/768/1440; keyboard operation;
selection updates; seller isolation; no write requests or data fields;
unavailable galleries; noindex; text escaping and unsafe asset rejection.

Run in the established dev/CI stack with:

```sh
npx playwright test tests/shop-preview.spec.js
```

For an isolated local static server that serves the directory as `/shop-preview/`,
set `SHOP_PREVIEW_BASE_URL` to its origin. API and image requests in this test
are intercepted. Actual public photographs were independently rendered and
inspected at desktop 1440 px and mobile 390 px, including portrait, square and
both photographer collections. Screenshot evidence is kept outside this patch.

## Proposed additive publication route — review before execution

Read-only VPS inspection confirmed both `/opt/prod/hensler_photography` and
`/opt/dev/hensler_photography` clean on `main` at the base commit above.
Origin is `https://github.com/adrianhensler/hensler-photography.git`.
`AGENTS.md` resolves to `CLAUDE.md`; no `.agents/skills` exists in this checkout.

Production Caddy serves Adrian's site from `/srv/sites/adrian` using
`try_files {path} {path}.html {path}/index.html`. Compose bind-mounts `./sites`
read-only into the web container. Thus the new directory is served by the
existing static handler: **no Caddy changes, API rebuild or service restart**.

1. Review the additive file list and screenshots with the parent coordinator.
2. Push the isolated feature branch and open a PR. Do not push directly to main.
3. Require passing CI and review the exact merged diff. Recheck production is
   clean and confirm no unrelated merged changes would hitchhike in a pull.
4. After approval/merge, fast-forward the production checkout only when the
   pending diff contains this reviewed additive patch. No container action.
5. Verify `/shop-preview/`, its three scripts/styles, real image loads, CSP,
   banner, noindex, both photographer switches and demo controls. Check existing
   hub/portfolio pages and health endpoints still behave as before.

Do not edit live bind-mounted files to prepare or stage the change. No remote
push, PR, merge or deployment occurred during local preparation. Removing only
this preview directory through the same PR workflow can retire the study.
