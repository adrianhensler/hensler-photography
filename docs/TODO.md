# TODO

Single source of truth for open work. Organized by horizon.
GitHub Issues are for bugs; this file is for planned work.

Sources: multi-model site audit 2026-03-07 (`docs/reviews/photography-site-2026-03-02/`);
management console UI/UX review 2026-08-01 (artifact; findings summarized in the
retheme item below). Refreshed 2026-08-01: dropped items made moot by the July
gallery redesign (PRs #43, #50–#56).

---

## NOW (this week)

- [ ] **Uptime monitoring** — configure UptimeRobot (free tier) for all 3 domains with
      SMS + email alerts; nothing in the repo suggests this was ever set up — Adrian to
      confirm whether an external monitor exists, else it is still open
- [ ] **Admin 2FA (TOTP)** — add `pyotp`-based TOTP to FastAPI auth middleware
      (verified 2026-08-01: still not implemented)

---

## NEXT (2–6 weeks)

- [ ] **Console retheme phase 2** (per ADR 0003 + UI/UX review 2026-08-01) — adopt the
      `admin-common.css` button system on every `/manage` page and delete local overrides;
      restructure upload batch bar and gallery card action rows ("one primary action per
      view"); retire off-palette colors (`#667eea/#764ba2` purple, `#34c759` green,
      `#06c` blue); remove AI/cost language from photographer-facing copy; replace
      div-as-button patterns with real elements. Upload workflow first (confirmed).
      Separate decision needed: fold `/admin` pages into the manage shell or retire them.
- [ ] **SEO metadata fixes** — remaining gaps (Adrian `og:description`/`og:image` fixed):
      - Liam has no `og:image`
      - Neither site has `twitter:card`
- [ ] **Filter usage instrumentation** — category-row clicks fire no analytics events;
      `trackEvent` exists in `gallery.js` but is not called on filter interactions
      (re-verified 2026-08-01 against the redesigned gallery)
- [ ] **GDPR/CCPA consent banner** — lightweight JS consent gate for analytics tracking
- [ ] **hensler.photography landing page** — directory hub exists; consider adding contact
      info or other content

---

## LATER (next quarter, conditional)

- [ ] **Object storage / CDN migration** — trigger: disk >70% OR measurable perf degradation
- [ ] **Client acquisition analytics** — UTM tracking, contact form events
- [ ] **Cache header audit** — trigger: if "bust browser cache" commits recur
- [ ] **CI/CD via GitHub Actions** — trigger: deployment frequency increases or team grows
- [ ] **User-account management UI** — no admin CRUD exists (API is self-service
      `/api/users/me` only); adding a photographer requires direct DB access. Fine at two
      users; revisit if the roster grows.

---

## Closed / Won't Do

- ~~Issue #36 (applyIntent stale facets)~~ — closed 2026-08-01 as obsolete: the intent-chip
  code path was removed entirely by the July gallery redesign
- ~~Backup restore drill~~ — verified 2026-03-07: backup readable, row counts match
  production (46 images).
- ~~Admin rate limiting~~ — `slowapi` already applied at 5/minute per IP (`api/rate_limit.py`)
- ~~Liam API parity~~ — Liam uses same `gallery.js` (userId: 2), WebP variants, analytics,
  and filter system as Adrian. No gap.
- ~~PostgreSQL migration~~ — no evidence of SQLite write-lock problems
- ~~More filter UI iteration~~ — the 2026-03 freeze applied to the Browse/Refine UI, which
  the July redesign replaced wholesale; superseded
- ~~Video support, social feeds, user accounts~~ — out of scope

---

## Open Bugs

None tracked. File new bugs as GitHub Issues and list them here.
