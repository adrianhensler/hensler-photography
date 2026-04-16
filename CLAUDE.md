# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

**Key Documentation:**
- **DATABASE.md** - Complete database schema, creation instructions, and common queries
- **ARCHITECTURE.md** - System design and technical architecture
- **DEVELOPMENT.md** - Development workflow and best practices

## Public Repository Notice

**This code is publicly visible on GitHub**: https://github.com/adrianhensler/hensler-photography

### Guidelines for Public Code
- **Security first**: Never commit secrets, API keys, or credentials
- **XSS prevention**: Always escape user input before DOM insertion (use `escapeHtml()`)
- **Test before push**: Run `npm test` and manual verification on dev server (port 8080)

## AI Coding Working Agreement

### Non-Negotiables
1. **Make it work first.** Only refactor after tests pass and behavior is correct.
2. **Small, reviewable diffs.** Prefer multiple small commits over one big change.
3. **Do not change tests** unless explicitly instructed (or adding coverage for new behavior).
4. **No new dependencies** without approval. If needed, explain why and list alternatives.
5. **Ask before destructive actions** (deletes, migrations, data resets, force pushes, wide refactors).

### Workflow: Plan → Build → Verify → Summarize

**Plan** (before edits):
- Restate goal in 1-2 lines
- List files to touch
- Define acceptance criteria (what proves this is done)

**Build** (implementation):
- Follow existing patterns unless told otherwise
- Prefer straightforward code over clever code
- Keep functions small; isolate side effects at edges

**Verify** (always run):
- Run targeted tests for changed areas, then full suite
- Check lint/format, typecheck if present
- Test on port 8080 before production

**Summarize** (after completion):
- What changed and why (bullet list)
- How verified (commands run + results)
- Any follow-ups or known limitations

### Backend Quality Attributes
- **Idempotency**: Re-running same operation should not duplicate/corrupt state
- **Reproducibility**: Pin dependencies, avoid time-dependent behavior in core logic
- **Traceability**: Log inputs, key decisions, outputs; include run_id for async operations
- **Auditability**: Prefer append-only history for important records

## Code Quality Standards

### JavaScript Style
- **Pure vanilla JS**: No frameworks (React, Vue, etc.) for frontend
- **ES6+ syntax**: Use arrow functions, destructuring, template literals
- **No jQuery**: Use native DOM APIs
- **Function size**: Keep functions under 50 lines; extract if larger
- **Single responsibility**: Each function does one thing well
- **DRY principle**: Extract duplicate code into reusable functions

### Security Checklist
- ✅ Escape all user input with `escapeHtml()` before inserting into DOM
- ✅ Use event listeners (addEventListener) instead of inline onclick handlers
- ✅ Validate URL parameters against known database values
- ✅ Never use `eval()` or `innerHTML` with unescaped user data
- ✅ Review all string interpolation in template literals for XSS risks

### Performance Targets
- **Gallery load time**: < 1 second on 4G connection
- **First Contentful Paint**: < 1.5 seconds
- **Lazy loading**: Images load progressively as user scrolls
- **WebP optimization**: Use responsive srcset with 400px/800px/1200px variants

### Accessibility
- **Alt text**: All images must have descriptive alt attributes
- **Keyboard navigation**: Lightbox navigable via keyboard
- **Reduced motion**: Respect `prefers-reduced-motion` setting
- **Semantic HTML**: Use proper heading hierarchy (h1, h2, h3)

## Project Overview

Multi-site photography portfolio using a **single Caddy container** serving three domains:
- `hensler.photography` → sites/main/ (directory hub linking to Adrian and Liam portfolios)
- `liam.hensler.photography` → sites/liam/ (Instagram portfolio)
- `adrian.hensler.photography` → sites/adrian/ (Flickr portfolio)

## Backend API System

Python/FastAPI backend for image management on the same port as the static sites.

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Port 443 (Production) / 8080 (Development)                 │
│                                                              │
│  Public Routes:                                              │
│  - adrian.hensler.photography/                              │
│  - liam.hensler.photography/                                │
│  - Dynamic loading via /api/gallery/published               │
│  - Responsive WebP variants (400px/800px/1200px)            │
│                                                              │
│  Management Routes (JWT auth required):                      │
│  - /admin/login (authentication)                            │
│  - /manage (dashboard)                                       │
│  - /manage/upload (image upload with AI metadata)           │
│  - /manage/gallery (publish workflow, EXIF editing)          │
│  - /manage/analytics (engagement metrics)                    │
│  - /manage/settings (account + portfolio settings)          │
│                                                              │
│  Backend: Python/FastAPI + SQLite                            │
│  - JWT authentication with httpOnly cookies                 │
│  - AI-powered metadata (Claude Vision API)                  │
│  - WebP variant generation (400px/800px/1200px)             │
│  - Analytics tracking (privacy-preserving)                   │
└─────────────────────────────────────────────────────────────┘
```

### Backend Stack

- **Framework**: Python 3.11+ / FastAPI / Uvicorn ASGI
- **Database**: SQLite at `/data/gallery.db` (see DATABASE.md for full schema)
- **Auth**: JWT tokens in httpOnly cookies, bcrypt (12 rounds), role-based (admin/photographer)
- **Image Processing**: PIL/Pillow — EXIF extraction, WebP conversion, 3 variant sizes
- **AI**: Claude Vision API — title, caption, tags, category generation (~$0.02/image)

### Admin Interface Features

**Upload** (`/manage/upload`): Drag-and-drop, batch upload (max 3 concurrent), auto AI metadata, EXIF extraction, editable technical fields.

**Gallery Management** (`/manage/gallery`): View/filter/search images, edit all metadata, re-extract EXIF (free), regenerate AI metadata (~$0.02), publish/unpublish, mark featured, delete.

**Analytics Dashboard** (`/manage/analytics`): Engagement metrics (views, visitors, clicks, CTR), 7/30/90-day timeline chart, top images by impressions/clicks/views, category breakdown, scroll depth analysis (25/50/75/100%), average viewing duration.

**Settings** (`/manage/settings`): Account profile, theme, password, public portfolio settings.

### Management Interface Architecture

All `/manage/*` pages use shared template inheritance.

**Core Components**:
- **Base Template**: `api/templates/photographer/base.html`
  - Dark theme default with localStorage persistence, FOUC-prevention inline script
  - Jinja blocks: `page_title`, `head_scripts`, `styles`, `content`, `scripts`
- **Shared Header**: `api/templates/photographer/_header.html`
  - Nav with active page detection, theme toggle, user dropdown, admin console link
  - Requires `request` object in template context
- **Shared Styles**: `api/static/css/manage-shell.css`
- **Shared JS**: `api/static/js/manage-header.js`
- **CSS Variables**: `api/static/css/variables.css` (theme colors, `--avatar-gradient`, state colors)

**Navigation Order**: Dashboard → Gallery → Upload → Analytics

**Adding New Management Pages**:
1. Create template extending `photographer/base.html`
2. Add route to `api/main.py` (pass `request` in context for nav detection)
3. Add nav link to `api/templates/photographer/_header.html`

### API Endpoints

**Authentication**:
- `POST /api/auth/login` — Login (returns JWT cookie)
- `POST /api/auth/logout` — Logout
- `GET /api/auth/me` — Get current user

**Image Management**:
- `POST /api/images/upload` — Upload image(s) with AI analysis
- `GET /api/images/list?user_id=1&limit=1000` — List images
- `GET /api/images/{id}` — Get image details with EXIF
- `PATCH /api/images/{id}` — Update metadata (validated)
- `DELETE /api/images/{id}` — Delete image
- `POST /api/images/{id}/publish` — Toggle publish status
- `POST /api/images/{id}/featured?featured=true` — Toggle featured
- `POST /api/images/{id}/reextract-exif` — Re-extract EXIF (free)
- `POST /api/images/{id}/regenerate-ai` — Regenerate AI metadata (~$0.02)

**Public Gallery**:
- `GET /api/gallery/published?user_id=1` — Published images with WebP variant URLs (used by public sites)

**Analytics**:
- `POST /api/track` — Record events (no auth; privacy-preserving)
- `GET /api/analytics/overview?days=30` — Overall stats
- `GET /api/analytics/timeline?days=30&metric=views` — Time series
- `GET /api/analytics/top-images?days=30&limit=10&metric=impressions` — Top images
- `GET /api/analytics/category-performance?days=30` — Category breakdown
- `GET /api/analytics/scroll-depth?days=30` — Scroll milestones
- `GET /api/analytics/referrers?days=30` — Traffic sources

### Validation Rules

Pydantic models enforce these formats:
- **ISO**: Numeric, range 25–10,000,000
- **Aperture**: `f/2.8` or `f/1.4`
- **Shutter Speed**: `1/250s`, `1/1000`, `1"`, `2.5s`
- **Focal Length**: `50mm` or `24-70mm`
- **Date Taken**: `YYYY-MM-DD HH:MM:SS` or `YYYY-MM-DD`

### File Storage

**Image Storage** (API container `/app/assets/gallery/`):
- **Originals**: `YYYYMMDD_HHMMSS_hash.jpg`
- **Thumbnail**: `YYYYMMDD_HHMMSS_hash_thumbnail.webp` (400px, ~10-30KB)
- **Medium**: `YYYYMMDD_HHMMSS_hash_medium.webp` (800px, ~30-80KB)
- **Large**: `YYYYMMDD_HHMMSS_hash_large.webp` (1200px, ~40-150KB)
- Served via: `https://adrian.hensler.photography/assets/gallery/filename`

**Public Gallery Loading**:
- Frontend fetches `/api/gallery/published?user_id=1` on page load
- Browser uses responsive srcset: thumbnails for grid, large for lightbox
- Native lazy loading; 10-20x faster than loading originals

### Gallery Filtering & URL Synchronization

- **Featured/All Toggle**: Default = featured only; `?featured=false` for all
- **Category Filters**: `?category=portrait`
- **Tag Filters**: `?tag=nature` or `?tags=nature,landscape,wildlife`
- All filter state synced to URL; browser history (back/forward) supported
- Copy Link button appears when filters are active
- Hero slideshow always uses full published dataset (independent of gallery filters); 70% weighted toward featured images

### Environment Variables

Required in `docker-compose.local.yml`:
```yaml
environment:
  DATABASE_PATH: /data/gallery.db
  ANTHROPIC_API_KEY: sk-ant-...
  JWT_SECRET_KEY: dev-secret-...
```

### Backend Commands

```bash
# Initialize database
cd /opt/dev/hensler_photography
docker compose -p hensler_test exec api python -m api.database

# Check API logs
docker compose -p hensler_test logs api --tail 50

# Restart API only
docker compose -p hensler_test restart api

# Query database
docker compose -p hensler_test exec api python -c "
from api.database import get_db
conn = get_db().__enter__()
for row in conn.execute('SELECT id, title, published FROM images WHERE user_id = 1').fetchall():
    print(dict(row))
"
```

## Frontend: Adrian Site Architecture

- **Entry point**: `sites/adrian/index.html`
- **Gallery logic**: `sites/shared/gallery.js` (IIFE module, 1692 lines)
- **API-driven**: Gallery loads from `/api/gallery/published?user_id=1` on page load
- **Responsive images**: srcset with WebP variants (400px/800px/1200px)
- **Ghost typography**: Playfair Display, 300 weight, 0.45 opacity, lowercase
- **Slideshow**: Auto-cycles 5s with large (1200px) variants, pauses on hover
- **Gallery grid**: Thumbnail variants (400px), 3→2→1 responsive columns
- **Lightbox**: GLightbox using large (1200px) variants
- **Analytics**: Tracks impressions, clicks, views, scroll depth, duration
- **No frameworks**: Pure vanilla HTML/CSS/JS, no build process

**When making changes**:
- Preserve aspect ratios in gallery (hard requirement)
- Image URLs come from the API — do not hardcode them
- Test slideshow cycling and manual navigation
- Verify responsive breakpoints (mobile, tablet, desktop)
- Check Network tab: WebP variants loading, `/api/track` events firing

### Gallery.js Architecture

**File**: `sites/shared/gallery.js` — IIFE module, used by both adrian and liam sites.

**Module Structure**:
1. **Configuration & State**: Global variables, filter state
2. **Security Helpers**: `escapeHtml()` XSS prevention
3. **Utility Functions**: `applyFilterCriteria()`, `buildLightboxDescription()`, `createGalleryItem()`
4. **Slideshow Logic**: Hero carousel, auto-advance
5. **Gallery Grid Logic**: Thumbnail grid, lazy loading
6. **Analytics Tracking**: Event tracking (impression, click, scroll)
7. **Gallery Filtering**: Featured/category/tag filters, URL sync
8. **Main Initialization + Public API**: `window.GalleryApp`

**Key Functions**:
- `escapeHtml(unsafe)` — XSS prevention for all user input
- `applyFilterCriteria(dataset, criteria)` — Filter by featured/category/tags
- `buildLightboxDescription(imageData, options)` — Builds EXIF/caption HTML
- `createGalleryItem(imageData, index, options)` — Creates thumbnail element
- `applyFilters()` / `rerenderGallery(filteredData)` — Filter + re-render
- `initSlideshow()` / `initGallery()` — Initialize components

**Modifying gallery.js**: Changes affect both sites. Use DocumentFragment for batch DOM inserts. All user input (URL params, DB values) must be escaped.

**Analytics Events**:
- `page_view` — Page load
- `image_impression` — Image 50% visible in viewport
- `gallery_click` — Thumbnail clicked
- `lightbox_open` — Full-screen opened
- `lightbox_close` — Full-screen closed (includes duration)
- `scroll_depth` — 25%, 50%, 75%, 100% milestones

## Critical Architecture Decisions

### Single Container, Multiple Domains
All sites run in one Caddy container on ports 80/443. Caddy manages TLS certificates per domain. Keeps deployment simple; no port conflicts when adding new sites.

### Dual Configuration System

**Production**: `Caddyfile` + `docker-compose.yml`
- Three separate domain blocks, auto-HTTPS via Let's Encrypt

**Development**: `Caddyfile.local` + `docker-compose.local.yml`
- Single `localhost:8080` with path-based routing (`/liam`, `/adrian`)
- Uses `uri strip_prefix` before serving files

Same sites/ directory structure in both; test locally with identical production behavior.

## Common Commands

### Directory Structure

```
/opt/
├── prod/hensler_photography/    # Production (ports 80/443)
└── dev/hensler_photography/     # Development (port 8080)
```

**Never edit files in `/opt/prod/` directly.** Make changes in `/opt/dev/`, test, commit, deploy via git pull.

### Development (Port 8080)

```bash
cd /opt/dev/hensler_photography

# Start dev stack
docker compose -p hensler_test -f docker-compose.local.yml up -d

# Stop dev stack
docker compose -p hensler_test -f docker-compose.local.yml down

# URLs:
# http://localhost:8080/         (main site)
# http://localhost:8080/liam     (Liam's site)
# http://localhost:8080/adrian   (Adrian's site)
# https://adrian.hensler.photography:8080/manage  (management)
```

### Production Deployment

> **Direct pushes to main are blocked.** All changes require a Pull Request with passing CI.

```bash
# 1. Work in dev, test on port 8080
cd /opt/dev/hensler_photography

# 2. Create feature branch
git checkout -b feature/my-improvement
git add <files>
git commit -m "Description"
git push origin feature/my-improvement

# 3. Create PR
gh pr create --title "..." --body "..."

# 4. After PR merged, deploy
cd /opt/prod/hensler_photography
git pull origin main
docker compose restart

# 5. Verify health
curl -I https://hensler.photography/healthz
curl -I https://liam.hensler.photography/healthz
curl -I https://adrian.hensler.photography/healthz
```

### Testing

```bash
# Install deps (first time)
npm install && npx playwright install --with-deps

# Run all tests (requires dev server on port 8080)
npm test

# Interactive UI
npm run test:ui

# Debug specific test
npx playwright test --debug tests/sites.spec.js
```

**Test credentials** (development):
- Login: `https://adrian.hensler.photography:8080/admin/login`
- Username: `adrian` / Password: see DATABASE.md

## Testing Architecture

Playwright tests in `tests/sites.spec.js` verify page loads, external links, hero images, health endpoints, responsive viewports, and multi-browser compatibility (Chromium, Firefox, WebKit). Generates screenshots to `screenshots/`.

## Security Headers (Applied to All Sites)

Configured in both Caddyfiles:
- `Strict-Transport-Security`: Force HTTPS
- `X-Frame-Options: DENY`: Prevent clickjacking
- `X-Content-Type-Options: nosniff`: Prevent MIME sniffing
- `Referrer-Policy: strict-origin-when-cross-origin`: Privacy

## Adding a New Site

1. Create `sites/foo/` with `index.html` and `assets/`
2. Add domain block to `Caddyfile` (copy security headers from existing block)
3. Add path handler to `Caddyfile.local`:
   ```
   @foo path /foo /foo/*
   handle @foo {
     root * /srv/sites/foo
     uri strip_prefix /foo
     file_server
   }
   ```
4. Test at `http://localhost:8080/foo` before deploying

## Custom Agents

Project-specific agents in `.claude/agents/`:

- **web-design-critic** — Photography portfolio design review (UX, visual hierarchy, modern trends)
- **modern-css-developer** — Vanilla HTML/CSS/JS implementation, accessibility, responsive design
- **expert-code-reviewer** — Code quality, security, architecture (FastAPI, Python, HTML/CSS/JS, Docker)
- **product-marketing-critic** — Product strategy, feature prioritization, go-to-market

## Backup

Daily backups via `scripts/backup.sh` (sqlite3 `.backup` + `cp -a` for images). Runs Mon/Thu at 2 AM. Keeps 2 most recent backups in `/opt/backups/hensler_photography`.
