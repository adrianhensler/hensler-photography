# TODO

Single source of truth for open work. Organized by horizon.
GitHub Issues are for bugs (e.g. #36); this file is for planned work.

Source: multi-model site audit 2026-03-07 — see `docs/reviews/photography-site-2026-03-02/`

---

## NOW (this week)

- [ ] **Uptime monitoring** — configure UptimeRobot (free tier) for all 3 domains with
      SMS + email alerts; no cron or external monitor exists; outages discovered by users
- [ ] **Admin 2FA (TOTP)** — add `pyotp`-based TOTP to FastAPI auth middleware

---

## NEXT (2–6 weeks)

- [ ] **SEO metadata fixes** — two concrete gaps in static HTML:
      - Adrian `og:description` still says "View my work on Flickr." (stale since API migration)
      - Neither site has `twitter:card` or `og:image` on Liam
- [ ] **Filter usage instrumentation** — filter clicks (category, tag, intent chips) fire no
      analytics events; `trackEvent` exists but is not called on filter interactions; freeze UI
      for 6 weeks minimum before iterating (Browse/Refine shipped 2026-03-07 in PR #41)
- [ ] **GDPR/CCPA consent banner** — lightweight JS consent gate for analytics tracking
- [ ] **hensler.photography landing page** — directory hub exists; consider adding contact
      info or other content

---

## LATER (next quarter, conditional)

- [ ] **Object storage / CDN migration** — trigger: disk >70% OR measurable perf degradation
- [ ] **Client acquisition analytics** — UTM tracking, contact form events
- [ ] **Cache header audit** — trigger: if "bust browser cache" commits recur
- [ ] **CI/CD via GitHub Actions** — trigger: deployment frequency increases or team grows

---

## Closed / Won't Do

- ~~Backup restore drill~~ — verified 2026-03-07: backup readable, row counts match
  production (46 images).
- ~~Admin rate limiting~~ — `slowapi` already applied at 5/minute per IP (`api/rate_limit.py`)
- ~~Liam API parity~~ — Liam uses same `gallery.js` (userId: 2), WebP variants, analytics,
  and filter system as Adrian. No gap.
- ~~PostgreSQL migration~~ — no evidence of SQLite write-lock problems
- ~~More filter UI iteration~~ — frozen pending 6 weeks of usage data
- ~~Video support, social feeds, user accounts~~ — out of scope

---

## Open Bugs

| Issue | Title | Status |
|-------|-------|--------|
| [#36](https://github.com/adrianhensler/hensler-photography/issues/36) | `applyIntent` reads stale facet maps before scope change | Open — still reproducible after PR #41 |
