# Decision Brief: Adrian Hensler Photography Portfolio
### Multi-Model Review Synthesis — Solo Owner Action Plan

---

# Executive Summary

Your stack is solid. Docker + Caddy + FastAPI + SQLite is the right tool for this scale, your documentation is genuinely exceptional, and WebP variant generation gives you a real performance edge. The AI metadata pipeline is a meaningful differentiator.

**The problem isn't the architecture — it's three unresolved risks sitting underneath a functional system:**

1. Your backup has never been tested. It may not work.
2. Your admin routes are publicly exposed with password-only auth.
3. You're building features (filters, Liam's shell site) without closing the gaps that actually cost you business (no landing page, no SEO, no uptime alerts).

Three independent models agreed on all of the above. The path forward is clear: stop adding, start hardening.

---

# Now (This Week)

**Two non-negotiable actions before anything else.**

### 1. Test Your Backup — Today
Your `BACKUP.md` is well-written. That means nothing until you've actually restored from it.

- Spin up a fresh VM (DigitalOcean $6/mo droplet is fine)
- Execute a full restore from your `restic` backup
- Confirm the database, images, and config all come back clean
- Document what broke, what was missing, and update `BACKUP.md` with the actual results

**Why this is #1:** An untested backup is not a backup. If your single host goes down tonight, you find out whether this works under pressure. Do it on your terms instead.

---

### 2. Harden Admin Authentication
Your `/admin` and `/manage` routes are on a public domain with password-only auth. That's one credential leak away from a serious problem.

**Two-layer fix, both low effort:**

- **Caddy level:** Add rate limiting to `/admin` routes in your `Caddyfile` (~30 minutes)
- **Application level:** Implement TOTP 2FA via `pyotp` in your FastAPI auth middleware (~2 hours)

These are complementary controls, not alternatives. Do both. This is the minimum acceptable posture for a business handling client data.

---

# Next (2–6 Weeks)

**Close the business gaps. These are all high-impact, low-to-medium effort.**

### 3. Add SEO Metadata to Gallery Pages
Every gallery page is currently invisible to search engines and renders poorly on social sharing. This is leaving organic traffic on the table every day it's unfixed.

- Add FastAPI middleware to inject Open Graph, Twitter Card, and canonical `<meta>` tags dynamically per gallery and image page
- Verify your AI-generated alt text is actually populating `<img>` tags (audit, don't assume)
- One implementation pass covers both SEO and social sharing simultaneously

### 4. Launch the `hensler.photography` Landing Page
"Coming Soon" is a business decision, not a technical one. You have two live portfolios and no front door.

- Build a conversion-focused static page served by Caddy
- Clear CTAs to Adrian's and Liam's portfolios, contact info, and brand positioning
- Static HTML/CSS — this does not need to be complex

### 5. Bring Liam's Site to API Parity with Adrian's
Two codepaths for the same feature doubles every future maintenance task. Every improvement you make to Adrian's gallery now requires a separate decision about Liam's.

- Bring `liam.hensler.photography` to full API-driven gallery parity
- Eliminate the maintenance split before it compounds further

### 6. Set Up External Uptime Monitoring
Caddy logs tell you what happened. They don't tell you when your site goes down. Right now, your clients discover downtime before you do.

- Configure UptimeRobot (free tier) for all three domains
- Set SMS + email alerts
- This is a 15-minute setup with zero ongoing cost

### 7. Add a GDPR/CCPA Consent Banner
If any EU or California visitors hit your site while you're running analytics tracking, you have legal exposure. Two of three models missed this — that doesn't make it wrong.

- Implement a lightweight cookie consent banner (e.g., `cookieconsent` JS library)
- Gate analytics tracking on user consent
- Low effort, asymmetric risk profile: cheap to fix, non-trivial if ignored

---

# Later

**Valid improvements — but not until the above is done.**

| Item | Trigger to act |
|---|---|
| Object storage migration (S3/R2) | Disk utilization hits 70% OR CDN becomes necessary for performance |
| Client acquisition + funnel analytics | Landing page is live and generating traffic to measure |
| Cache header audit + content-hash versioning | The `fix: bust browser cache` commit pattern recurs |
| Filter UI revisit | Analytics confirm >5% usage of advanced filter features (6-week gate) |
| CI/CD via GitHub Actions | Deployment frequency increases or a second person joins the project |
| PostgreSQL migration | Concurrent write errors appear in logs — not before |

**Explicitly do not do yet:** PostgreSQL migration, object storage migration, video support, social media feeds, admin UI overhaul, additional AI features, more filter iteration.

---

# Risks to Monitor

| Risk | Current Status | Watch Signal |
|---|---|---|
| **Untested backup** | 🔴 Critical — unvalidated | Resolve this week; re-test quarterly |
| **Single host failure** | 🟠 Accepted risk at current scale | Monitor disk, CPU, memory via UptimeRobot |
| **Admin route exposure** | 🔴 Unacceptable with password-only auth | Resolve this week |
| **SQLite concurrency** | 🟡 Fine now | Watch for write lock errors in logs under concurrent uploads + analytics |
| **Claude API cost/availability** | 🟡 Low now | Set daily spend cap; have EXIF-only fallback ready |
| **Liam's site maintenance split** | 🟠 Compounding with every Adrian improvement | Resolve within 6 weeks |
| **GDPR/CCPA compliance** | 🟠 Legal exposure if EU/CA visitors tracked | Resolve within 4 weeks |
| **Cache instability** | 🟡 One commit suggests underlying issue | Watch for recurrence; audit headers in "Later" phase |

---

# Brand Guardrails

These are constraints, not suggestions. Don't ship anything that violates them.

**Visual**
- Hero images dominate every page. UI chrome (filters, nav, banners) is always secondary
- Maximum 3 fonts, 2 accent colors (black/white + 1 brand color)
- Never upscale images. Always serve WebP variants
- No auto-playing video, no heavy animations — static image quality is the product

**Performance**
- LCP stays under 2.5 seconds. Lazy-load everything below the fold
- Skeleton screens for loading states, never spinners
- Touch targets minimum 44px height — mobile is your majority traffic

**UX Consistency**
- `liam` and `adrian` sites share global CSS tokens (fonts, spacing, color) despite different content
- Filters: collapsed "Advanced" options by default, zero-count filters preserved for discovery
- Contact access within 2 clicks from any page
- Brand voice: professional and understated ("Explore" not "Click here")

**Development**
- No filter UI changes until analytics data justifies them — the current state is the frozen baseline
- No new AI features until the existing metadata pipeline is stable
- No local disk expansion — if storage is a problem, that's the trigger for object storage migration

---

# 7-Day Execution Checklist

Concrete deliverables, one owner (you), seven days.

**Day 1 — Monday**
- [ ] Provision a fresh VM (DigitalOcean, Linode, or equivalent)
- [ ] Execute full restore from `restic` backup per `BACKUP.md`
- [ ] Document results: what worked, what failed, what was missing

**Day 2 — Tuesday**
- [ ] Update `BACKUP.md` with actual restore results and any gaps found
- [ ] Add rate limiting rules to `Caddyfile` for `/admin` and `/manage` routes
- [ ] Test that rate limiting is active (verify with repeated requests)

**Day 3 — Wednesday**
- [ ] Install `pyotp` and implement TOTP 2FA in FastAPI auth middleware
- [ ] Test 2FA end-to-end: enrollment, login, recovery
- [ ] Set up UptimeRobot monitoring for all three domains with SMS + email alerts

**Day 4 — Thursday**
- [ ] Write FastAPI middleware for dynamic Open Graph + Twitter Card + canonical `<meta>` tag injection
- [ ] Audit 5 gallery pages to confirm AI-generated alt text is populating `<img>` tags correctly

**Day 5 — Friday**
- [ ] Deploy SEO metadata middleware to production
- [ ] Verify with a social share test (paste a gallery URL into Twitter/LinkedIn preview tool)
- [ ] Implement cookie consent banner; gate analytics on consent

**Day 6 — Saturday**
- [ ] Draft `hensler.photography` landing page content and layout (wireframe or rough HTML)
- [ ] Identify the specific API gaps between Liam's site and Adrian's — create a written task list

**Day 7 — Sunday**
- [ ] Review the week: what shipped, what slipped, what blocked you
- [ ] Prioritize the Liam parity task list for the following week
- [ ] Schedule your next backup restore test (calendar invite, 4 weeks out)

---

**End state after 7 days:** Backup validated, admin hardened, SEO live, monitoring active, compliance addressed, landing page in progress, Liam's gap documented. The foundation is real — now it's protected.