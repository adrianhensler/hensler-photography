# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

**Key Documentation:**
- **DATABASE.md** - Complete database schema, creation instructions, and common queries
- **ARCHITECTURE.md** - System design and technical architecture
- **DEVELOPMENT.md** - Development workflow and best practices
- **INTEGRATION_BREAKPOINT.md** - Current integration status (static → API)

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
- Test on port 8080 before production (see "Test Before Production" section)

**Summarize** (after completion):
- What changed and why (bullet list)
- How verified (commands run + results)
- Any follow-ups or known limitations

### Backend Quality Attributes
- **Idempotency**: Re-running same operation should not duplicate/corrupt state
- **Reproducibility**: Pin dependencies, avoid time-dependent behavior in core logic
- **Traceability**: Log inputs, key decisions, outputs; include run_id for async operations
- **Auditability**: Prefer append-only history for important records

## Project Overview

Multi-site static photography portfolio deployment using a **single Caddy container** serving three domains:
- `hensler.photography` → sites/main/ (Coming Soon landing page)
- `liam.hensler.photography` → sites/liam/ (Instagram portfolio)
- `adrian.hensler.photography` → sites/adrian/ (Flickr portfolio)

The architecture supports future expansion where the main site will showcase both photographers with links to their individual portfolios.

## Backend API System (NEW - November 2025)

**IMPORTANT**: The project now includes a Python/FastAPI backend for image management, in addition to the static portfolio sites.

### Architecture Overview

**Single-Port Architecture**:
- All routes (public + admin) served on same port
- Production: Port 443 (standard HTTPS)
- Development: Port 8080 (with HTTPS)
- JWT authentication secures `/admin` and `/manage` routes

```
┌─────────────────────────────────────────────────────────────┐
│  Port 443 (Production) / 8080 (Development)                 │
│                                                              │
│  Public Routes:                                              │
│  - adrian.hensler.photography/                              │
│  - liam.hensler.photography/                                │
│  - Dynamic loading via /api/gallery/published               │
│  - Responsive WebP variants (400px/800px/1200px)            │
│  - 10-20x faster with optimized images                      │
│                                                              │
│  Management Routes (JWT auth required):                      │
│  - /admin/login (authentication)                            │
│  - /manage (dashboard)                                       │
│  - /manage/upload (image upload with AI metadata)           │
│  - /manage/gallery (publish workflow, EXIF editing)          │
│  - /manage/analytics (engagement metrics)                    │
│                                                              │
│  Backend: Python/FastAPI + SQLite                            │
│  - JWT authentication with httpOnly cookies                 │
│  - AI-powered metadata (Claude Vision API)                  │
│  - WebP variant generation (400px/800px/1200px)             │
│  - Analytics tracking (privacy-preserving)                   │
└─────────────────────────────────────────────────────────────┘
```

### Port Architecture

- **Production**: Port 443 only (standard HTTPS)
  - Public routes: Open to all
  - Management routes: JWT authentication required
- **Development**: Port 8080 only (with HTTPS)
  - Same structure as production
  - Test with: `https://adrian.hensler.photography:8080/manage`

### Backend Stack

**Language/Framework**:
- Python 3.11+ with FastAPI
- Async/await throughout (aiosqlite, asyncio)
- Uvicorn ASGI server

**Database**:
- SQLite at `/data/gallery.db`
- Multi-tenant: users, images, image_variants, analytics, ai_costs
- Full EXIF metadata storage
- Audit logging for security

**AI Integration**:
- Claude Vision API (Anthropic) for metadata generation
- Cost: ~$0.015-0.03 per image
- Tracks token usage in database
- Features: title, caption, tags, category generation

**Authentication**:
- JWT tokens in httpOnly cookies
- bcrypt password hashing (12 rounds)
- Role-based access (admin, photographer)
- Session management

**Image Processing**:
- PIL/Pillow for EXIF extraction and WebP conversion
- Format detection (JPEG, PNG, GIF, WebP)
- Automatic WebP variant generation on upload:
  - Thumbnail: 400px width (for grid display, ~10-30KB)
  - Medium: 800px width (for tablets, ~30-80KB)
  - Large: 1200px width (for lightbox, ~40-150KB)
- 90-99% file size reduction vs originals
- Variants stored in `image_variants` table

### Admin Interface Features

**Upload System** (`/manage/upload`):
- Drag-and-drop or file picker
- Real-time progress tracking (XMLHttpRequest)
- Batch upload (max 3 concurrent)
- Automatic AI metadata generation
- Full EXIF extraction with photographer-focused display
- Exposure triangle (aperture, shutter, ISO)
- Print size recommendations based on resolution
- Editable technical fields with validation

**Gallery Management** (`/manage/gallery`):
- View all uploaded images
- Filter by status (published/draft)
- Filter by featured
- Search by title/caption/tags
- Edit metadata (all fields)
- Re-extract EXIF from original file (free)
- Regenerate AI metadata (~$0.02 per image)
- Publish/unpublish images
- Mark as featured
- Delete images

**Dashboard** (`/manage`):
- Overview of images, stats
- Quick actions

**Analytics Dashboard** (`/manage/analytics`):
- Real-time engagement metrics (views, visitors, clicks, CTR)
- Timeline chart showing traffic over 7/30/90 days
- Top performing images ranked by:
  - Impressions (viewport visibility)
  - Clicks (thumbnail interactions)
  - Views (lightbox opens)
- Category performance breakdown
- Scroll depth analysis (25%, 50%, 75%, 100% milestones)
- Average viewing duration tracking
- Privacy-preserving (no PII collected)
- Expandable "About Analytics" section with metric explanations

**Settings** (`/manage/settings`):
- Account profile management
- Theme preferences
- Password management
- Public portfolio settings

### Photographer Management Interface Architecture

**Template System**:
All `/manage/*` pages use a shared template inheritance system for consistency and maintainability.

**Core Components**:
- **Base Template**: `api/templates/photographer/base.html`
  - Provides HTML structure, `<head>` setup, CSS/JS includes
  - Includes inline theme initialization script (prevents FOUC)
  - Default dark theme with localStorage persistence
  - Jinja blocks: `page_title`, `head_scripts`, `styles`, `content`, `scripts`

- **Shared Header**: `api/templates/photographer/_header.html`
  - Navigation bar with active page detection
  - Theme toggle (dark/light mode with icon visibility logic)
  - User dropdown menu (profile, settings, logout)
  - Admin console link (visible only to admin role)
  - Requires `request` object for active nav detection

- **Shared Styles**: `api/static/css/manage-shell.css`
  - Header, navigation, theme toggle, user dropdown styles
  - Responsive mobile navigation with horizontal scroll
  - Note: "manage" refers to photographer management area (not admin)

- **Shared JavaScript**: `api/static/js/manage-header.js`
  - Theme toggle functionality
  - User dropdown open/close logic
  - Logout with error handling (alerts user on failure)
  - Keyboard support (Escape to close dropdown)

**Design System**:
- **CSS Variables**: Defined in `api/static/css/variables.css`
  - `--avatar-gradient`: User avatar background (reuses brand gradient)
  - `--accent`, `--success`, `--warning`, `--error`: UI states
  - Light/dark theme variants for all colors

**Navigation Order**:
1. Dashboard (`/manage`)
2. Gallery (`/manage/gallery`)
3. Upload (`/manage/upload`)
4. Analytics (`/manage/analytics`)

**Adding New Management Pages**:
1. Create template extending `photographer/base.html`:
   ```html
   {% extends 'photographer/base.html' %}
   {% block content %}
     <div class="container">
       <!-- Your page content -->
     </div>
   {% endblock %}
   ```

2. Add route to `api/main.py`:
   ```python
   @app.get("/manage/your-page")
   async def photographer_your_page(
       request: Request,
       current_user: User = Depends(get_current_user_for_subdomain)
   ):
       context = {
           "request": request,  # Required for header nav detection
           "title": "Your Page Title",
           "current_user": current_user
       }
       return templates.TemplateResponse(
           "photographer/your-page.html",
           context
       )
   ```

3. Add navigation link to `api/templates/photographer/_header.html` (lines 10-13):
   ```html
   <a href="/manage/your-page" class="{{ 'active' if '/manage/your-page' in path else '' }}">Your Page</a>
   ```

**Theme System**:
- Default: Dark theme (`data-theme="dark"`)
- Persists via localStorage (`theme` key)
- Inline script in base.html prevents FOUC (Flash of Unstyled Content)
- Theme toggle icons show/hide based on current theme (CSS visibility rules)

**Mobile Responsiveness**:
- Navigation uses horizontal scroll on narrow viewports
- Header collapses to column layout at 768px breakpoint
- User dropdown menu positioned correctly on all screen sizes

### Database Schema

```sql
-- Users (photographers)
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,
    display_name TEXT,
    role TEXT DEFAULT 'photographer',
    subdomain TEXT,
    bio TEXT
);

-- Images with full metadata
CREATE TABLE images (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    filename TEXT NOT NULL,                -- YYYYMMDD_HHMMSS_hash.jpg
    slug TEXT NOT NULL,

    -- AI-generated metadata
    title TEXT,
    caption TEXT,
    description TEXT,
    tags TEXT,                             -- Comma-separated
    category TEXT,

    -- EXIF technical data
    camera_make TEXT,
    camera_model TEXT,
    camera TEXT,                           -- Combined make + model
    lens TEXT,
    focal_length TEXT,
    aperture TEXT,
    shutter_speed TEXT,
    iso TEXT,
    date_taken DATETIME,
    location TEXT,

    -- Image properties
    width INTEGER,
    height INTEGER,
    aspect_ratio REAL,
    file_size INTEGER,

    -- Publishing control
    published BOOLEAN DEFAULT 0,          -- Visible on public site
    featured BOOLEAN DEFAULT 0,           -- Hero/featured image
    available_for_sale BOOLEAN DEFAULT 0,
    sort_order INTEGER DEFAULT 0,

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- WebP image variants (optimized versions)
CREATE TABLE image_variants (
    id INTEGER PRIMARY KEY,
    image_id INTEGER NOT NULL,
    format TEXT NOT NULL,              -- 'webp', 'avif' (future)
    size TEXT NOT NULL,                -- 'thumbnail', 'medium', 'large'
    filename TEXT NOT NULL,            -- e.g., '20251111_183319_hash_thumbnail.webp'
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    file_size INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
);

-- Analytics event tracking
CREATE TABLE image_events (
    id INTEGER PRIMARY KEY,
    image_id INTEGER,                  -- NULL for site-level events (page_view, scroll_depth)
    event_type TEXT NOT NULL,          -- 'page_view', 'image_impression', 'gallery_click',
                                       -- 'lightbox_open', 'lightbox_close', 'scroll_depth'
    user_agent TEXT,
    referrer TEXT,
    ip_hash TEXT,                      -- SHA256 hashed for privacy
    session_id TEXT,                   -- Client-generated random string
    metadata TEXT,                     -- JSON: {duration: 5} or {depth: 75}
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- AI cost tracking
CREATE TABLE ai_costs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    operation TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    image_path TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### API Endpoints

**Authentication**:
- `POST /api/auth/login` - Login (returns JWT cookie)
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Get current user

**Image Management**:
- `POST /api/images/upload` - Upload image(s) with AI analysis
- `GET /api/images/list?user_id=1&limit=1000` - List images
- `GET /api/images/{image_id}` - Get image details with EXIF
- `PATCH /api/images/{image_id}` - Update metadata (validated)
- `DELETE /api/images/{image_id}` - Delete image
- `POST /api/images/{image_id}/publish` - Toggle publish status
- `POST /api/images/{image_id}/featured?featured=true` - Toggle featured
- `POST /api/images/{image_id}/reextract-exif` - Re-extract EXIF
- `POST /api/images/{image_id}/regenerate-ai` - Regenerate AI metadata (~$0.02)

**Public Gallery** (✓ Implemented):
- `GET /api/gallery/published?user_id=1` - Get published images with WebP variants
  - Returns: image_url, thumbnail_url, medium_url, large_url
  - Includes EXIF data if share_exif=true
  - Used by adrian.hensler.photography and liam.hensler.photography

**Analytics Tracking**:
- `POST /api/track` - Record visitor events (no auth required)
  - Event types: page_view, image_impression, gallery_click, lightbox_open, lightbox_close, scroll_depth
  - Privacy-preserving: IP hashed, no cookies, anonymous session IDs
- `GET /api/analytics/overview?days=30` - Overall stats (auth required)
- `GET /api/analytics/timeline?days=30&metric=views` - Time series data
- `GET /api/analytics/top-images?days=30&limit=10&metric=impressions` - Top performing images
- `GET /api/analytics/category-performance?days=30` - Category breakdown
- `GET /api/analytics/scroll-depth?days=30` - Scroll milestone analysis
- `GET /api/analytics/referrers?days=30` - Traffic sources

### Validation Rules

**Technical Metadata** (Pydantic models with regex validation):
- **ISO**: Must be numeric, range 25-10,000,000
- **Aperture**: Format `f/2.8` or `f/1.4`
- **Shutter Speed**: Formats `1/250s`, `1/1000`, `1"`, `2.5s`
- **Focal Length**: Format `50mm` or `24-70mm`
- **Date Taken**: Format `YYYY-MM-DD HH:MM:SS` or `YYYY-MM-DD`

### File Storage

**Image Storage** (API container `/app/assets/gallery/`):
- **Originals**: `YYYYMMDD_HHMMSS_hash.jpg` (full resolution)
- **Thumbnail**: `YYYYMMDD_HHMMSS_hash_thumbnail.webp` (400px, ~10-30KB)
- **Medium**: `YYYYMMDD_HHMMSS_hash_medium.webp` (800px, ~30-80KB)
- **Large**: `YYYYMMDD_HHMMSS_hash_large.webp` (1200px, ~40-150KB)
- All files served via: `https://adrian.hensler.photography/assets/gallery/filename`
- Metadata stored in database (images + image_variants tables)

**Public Gallery Loading**:
- Frontend fetches from `/api/gallery/published?user_id=1`
- API returns URLs for all variants (thumbnail, medium, large, original)
- Browser uses responsive srcset to load appropriate size:
  - Mobile: 400px thumbnails
  - Tablet: 800px medium
  - Desktop grid: 400px or 800px based on column width
  - Lightbox: 1200px large (not full-res for performance)
- Native lazy loading (loading="lazy" attribute)
- 10-20x faster page loads vs full-resolution images

**Gallery Filtering & URL Synchronization** (✅ Implemented January 2026):
- **Featured/All Toggle**: Default view shows only featured images, users can toggle to "all"
  - UI: Two-button toggle above filters: "featured" | "all"
  - Default: Featured only (shows curated selection)
  - State persists in URL: `?featured=false` for "all" view
- **Category Filters**: Click category pills to filter by category
  - URL format: `?category=portrait` or `?category=wildlife`
  - Categories dynamically generated from image metadata
- **Tag Filters**: Click tag pills to filter by tags (supports multiple)
  - Single tag: `?tag=nature`
  - Multiple tags: `?tags=nature,landscape,wildlife`
  - Tags dynamically aggregated from all images
- **URL Synchronization**:
  - All filter state synced to URL query parameters
  - Browser history support: back/forward buttons restore filter state (popstate)
  - Shareable links: Copy URL preserves exact filter configuration
  - Clean URLs: Default state (featured only, no filters) = `/` with no query params
- **Copy Link Button**: Appears when filters are active
  - One-click copy shareable link to clipboard
  - Visual feedback: "Copied!" for 1.5 seconds
  - Fallback to `window.prompt()` if Clipboard API unavailable
- **Filter Combinations**: All filters work together
  - Example: `/?featured=false&category=wildlife&tag=nature`
  - Active filters display shows current state
  - Clear all button resets to default (featured only)

**Hero Slideshow Behavior**:
- Slideshow always uses full published dataset (independent of gallery filters)
- 70% weighted toward featured images, 30% any published
- Gallery grid respects user-selected filters
- This separation ensures slideshow variety while allowing focused gallery browsing

### Current Status & Next Steps

**✅ Complete** (Production-ready features):
- ✅ Full admin upload system with AI metadata
- ✅ Gallery management with publish/unpublish
- ✅ Authentication and authorization (JWT cookies)
- ✅ Database schema (images, image_variants, image_events, ai_costs)
- ✅ EXIF extraction and editing
- ✅ Technical field validation
- ✅ AI cost tracking
- ✅ **WebP variant generation** (400px/800px/1200px)
- ✅ **Public gallery API integration** (`/api/gallery/published`)
- ✅ **Responsive image loading** (srcset, lazy loading)
- ✅ **Analytics system** (impression tracking, engagement metrics)
- ✅ **Analytics dashboard** (top images, categories, scroll depth)
- ✅ **Image optimization** (10-20x faster page loads)
- ✅ **Gallery filtering system** (featured/all, category, tags)
- ✅ **URL-based filters** (shareable links, browser history support)

**🚀 Performance Achievements**:
- Gallery grid: 90-99% smaller images (thumbnails vs originals)
- Lightbox: 88-98% smaller images (1200px vs full-res)
- Page load time: 5-10 seconds → 0.5-1 second on 4G
- Total bandwidth: ~100MB → ~5-10MB for 21 images

**📊 Analytics Features**:
- 6 event types tracked (page_view, impression, click, open, close, scroll)
- Privacy-preserving (IP hashed, no PII, anonymous sessions)
- Real-time metrics and time-series charts
- Category performance breakdown
- Scroll depth analysis
- Average viewing duration

**⏳ Future Enhancements** (Optional):
- AVIF format support (even smaller than WebP)
- Blur-up placeholder technique
- Service worker caching (offline support)
- Image CDN (if scaling beyond single server)
- E-commerce integration (print sales)
- Text search on public site (search across titles, captions, tags)

### Testing URLs

**Production** (requires authentication):
- Login: `https://adrian.hensler.photography/admin/login`
- Dashboard: `https://adrian.hensler.photography/manage`
- Gallery: `https://adrian.hensler.photography/manage/gallery`
- Upload: `https://adrian.hensler.photography/manage/upload`
- Analytics: `https://adrian.hensler.photography/manage/analytics`
- Settings: `https://adrian.hensler.photography/manage/settings`

**Development** (requires authentication):
- Login: `https://adrian.hensler.photography:8080/admin/login`
- Dashboard: `https://adrian.hensler.photography:8080/manage`
- Gallery: `https://adrian.hensler.photography:8080/manage/gallery`
- Upload: `https://adrian.hensler.photography:8080/manage/upload`
- Analytics: `https://adrian.hensler.photography:8080/manage/analytics`
- Settings: `https://adrian.hensler.photography:8080/manage/settings`

**Credentials** (development):
- Username: `adrian`
- Password: Set via CLI tool (see DATABASE.md)

**Public Sites** (open, no auth):
- Adrian: `https://adrian.hensler.photography/`
- Liam: `https://liam.hensler.photography/`
- Loads images dynamically from `/api/gallery/published?user_id=1` (or 2 for Liam)
- Uses responsive WebP variants for optimal performance
- Analytics tracking active (impression, click, scroll events)

### Backend Commands

```bash
# Initialize database (creates schema + seed data)
cd /opt/dev/hensler_photography
docker compose -p hensler_test exec api python -m api.database

# Check database contents
docker compose -p hensler_test exec api python -c "
from api.database import get_db
conn = get_db().__enter__()
cursor = conn.execute('SELECT * FROM images WHERE user_id = 1')
for row in cursor.fetchall(): print(dict(row))
"

# View uploaded images
ls api/assets/gallery/

# Check API logs
docker compose -p hensler_test logs api --tail 50

# Restart API only
docker compose -p hensler_test restart api
```

### Environment Variables

Required in `docker-compose.local.yml`:
```yaml
environment:
  DATABASE_PATH: /data/gallery.db
  ANTHROPIC_API_KEY: sk-ant-...     # For AI features
  JWT_SECRET_KEY: dev-secret-...    # Auto-generated
```

### Cost Tracking

All Claude Vision API calls are logged:
- Model: claude-3-opus-20240229
- Pricing: $15/1M input tokens, $75/1M output tokens
- Typical cost: ~$0.015-0.03 per image
- Query costs: `SELECT * FROM ai_costs WHERE user_id = 1`

## Critical Architecture Decisions

### Single Container, Multiple Domains
All three sites run in one Caddy container on ports 80/443. Caddy automatically obtains and manages separate TLS certificates for each domain. This design choice:
- Simplifies deployment and resource usage
- Allows adding new sites without port conflicts
- Maintains standard HTTPS URLs for all domains

### Dual Configuration System
Two parallel configurations enable identical code for local testing and production:

**Production**: `Caddyfile` + `docker-compose.yml`
- Three separate domain blocks (hensler.photography, liam.hensler.photography, adrian.hensler.photography)
- Each domain serves its own /srv/sites/{main,liam,adrian} directory
- Auto-HTTPS via Let's Encrypt

**Local Testing**: `Caddyfile.local` + `docker-compose.local.yml`
- Single localhost:8080 server with path-based routing (/, /liam, /adrian)
- Uses `uri strip_prefix` to remove path prefixes before serving files
- Same sites/ directory structure, identical HTML/assets

This dual-config ensures changes can be tested locally with exact production behavior before deployment.

## Common Commands

### Directory Structure (Post-Migration)
Development and production are now properly isolated:

```
/opt/
├── prod/hensler_photography/    # Production (ports 80/443)
└── dev/hensler_photography/     # Development (port 8080)
```

**See docs/setup/MIGRATION_GUIDE.md for setup instructions.**

### Testing on VPS (Port 8080)
The testing environment runs in `/opt/dev/hensler_photography` and is fully isolated from production.

```bash
# Start test container
cd /opt/dev/hensler_photography
docker compose -p hensler_test -f docker-compose.local.yml up -d

# Access from VPS or remotely:
# http://localhost:8080/          (main site)
# http://localhost:8080/liam      (Liam's site)
# http://localhost:8080/adrian    (Adrian's site)
# http://localhost:8080/healthz   (health check)
# Or: http://VPS-IP:8080/liam, etc.

# Stop test container
docker compose -p hensler_test -f docker-compose.local.yml down
```

### Testing
```bash
# Install test dependencies (first time)
npm install
npx playwright install --with-deps

# Run all Playwright tests (requires local server running)
npm test

# Interactive test UI
npm run test:ui

# Generate screenshots only
npm run screenshot

# Debug specific test
npx playwright test --debug tests/sites.spec.js
```

### Production Deployment

> **⚠️ IMPORTANT**: Direct pushes to main are blocked by branch protection (enabled Nov 2025).
> All changes must go through Pull Requests with passing CI tests.

```bash
# All work happens on VPS in /opt/dev/
cd /opt/dev/hensler_photography

# Make changes, test on port 8080
docker compose -p hensler_test up -d

# Create feature branch (required - direct push to main blocked)
git checkout -b feature/my-improvement
git add .
git commit -m "Description"
git push origin feature/my-improvement

# Create Pull Request on GitHub
gh pr create --title "..." --body "..."

# After PR approved and merged (or use --admin to bypass):
# gh pr merge <number> --squash --admin

# Deploy to production: Pull merged changes
cd /opt/prod/hensler_photography
git pull origin main
docker compose restart

# Check production health
curl -I https://hensler.photography/healthz
curl -I https://liam.hensler.photography/healthz
curl -I https://adrian.hensler.photography/healthz

# View logs
docker compose logs web

# Start production (first time only)
cd /opt/prod/hensler_photography
docker compose up -d
```

## File Locations for Content Updates

### Hero Images
- Liam: `sites/liam/assets/liam-hero.jpg`
- Adrian: `sites/adrian/assets/adrian-hero.jpg` (currently placeholder)

### External Links
- Liam's Instagram: `sites/liam/index.html` line 27
- Adrian's Flickr: `sites/adrian/index.html` line 27

### Main Landing Page
- `sites/main/index.html` (currently "Coming Soon" placeholder)

## Testing Architecture

Playwright tests in `tests/sites.spec.js` verify:
- All pages load with correct titles/headings
- External links point to correct URLs (Instagram/Flickr)
- Hero images display properly
- Health check endpoints return 200
- Responsive design across mobile/tablet/desktop viewports
- Multi-browser compatibility (Chromium, Firefox, WebKit)

Tests run against local server (localhost:8080) and generate screenshots to `screenshots/` directory.

## Security Headers (Applied to All Sites)

Configured in both Caddyfiles:
- `Strict-Transport-Security`: Force HTTPS
- `X-Frame-Options: DENY`: Prevent clickjacking
- `X-Content-Type-Options: nosniff`: Prevent MIME sniffing
- `Referrer-Policy: strict-origin-when-cross-origin`: Privacy protection

## Adding a New Site

To add a fourth domain (e.g., foo.hensler.photography):

1. Create directory: `sites/foo/` with `index.html` and `assets/`
2. Add block to `Caddyfile`:
   ```
   foo.hensler.photography {
     encode zstd gzip
     root * /srv/sites/foo
     file_server
     # ... (copy security headers from existing blocks)
   }
   ```
3. Add path handler to `Caddyfile.local`:
   ```
   @foo path /foo /foo/*
   handle @foo {
     root * /srv/sites/foo
     uri strip_prefix /foo
     file_server
   }
   ```
4. Test locally at `http://localhost:8080/foo` before deploying

## Using Claude CLI Subagents

### What Are Subagents?

Subagents are specialized AI assistants with their own context windows, custom system prompts, and specific tool access. They enable focused, expert-level work on specialized tasks without polluting the main conversation context.

### When to Use Subagents

**Use subagents for:**
- Complex, specialized tasks requiring domain expertise
- Tasks that benefit from isolated context (design review, code audit)
- Reusable workflows (same agent for same task type)
- Preserving main conversation context for coordination

**Work directly in main agent for:**
- Simple, quick changes
- Continuing work already in progress
- Tasks requiring full project context
- Coordination across multiple tasks

### Best Practices

1. **Early Delegation**: Use subagents early in conversations to verify details or investigate questions without consuming main context
2. **Single-Purpose Agents**: Create focused agents for specific tasks, not general-purpose helpers
3. **Detailed System Prompts**: Write comprehensive instructions in agent configuration
4. **Tool Limitation**: Only grant necessary tools to each agent type
5. **Version Control**: Keep project agents in `.claude/agents/` and commit to git

### Custom Agents in This Project

This project includes specialized agents for web development:

**web-design-critic** (`.claude/agents/web-design-critic.md`)
- Expert in photography portfolio design
- Analyzes UX, visual hierarchy, modern design trends
- Provides actionable improvement suggestions
- Use for: Design reviews, layout critique, inspiration gathering

**modern-css-developer** (`.claude/agents/modern-css-developer.md`)
- Expert in vanilla HTML/CSS/JavaScript
- No frameworks, performance-focused approach
- Accessibility and responsive design specialist
- Use for: Implementing designs, CSS architecture, animations

**expert-code-reviewer** (`.claude/agents/expert-code-reviewer.md`)
- Expert software engineer with 15+ years experience
- Reviews code quality, security, architecture, and product strategy
- Evaluates backend (FastAPI, Python), frontend (HTML/CSS/JS), and DevOps (Docker)
- Use for: Code quality audits, security reviews, architecture feedback

**product-marketing-critic** (`.claude/agents/product-marketing-critic.md`)
- Product marketing strategist and business analyst
- Specializes in SaaS products and creative tools
- Analyzes product-market fit, competitive positioning, value proposition
- Use for: Product strategy, feature prioritization, go-to-market planning

### How to Invoke Subagents

**Explicit invocation:**
```
Use the web-design-critic subagent to analyze adrian.hensler.photography
```

**Automatic delegation** (Claude decides):
```
Please review the design of adrian.hensler.photography
```

### Subagent Workflow Example

```
Main Agent: "I need to improve adrian.hensler.photography"
  ↓
Subagent (web-design-critic): Analyzes site, provides critique
  ↓
Main Agent: Reviews critique, plans implementation
  ↓
Subagent (modern-css-developer): Implements design improvements
  ↓
Main Agent: Tests changes, coordinates deployment
```

## Working with Claude CLI

### What is Claude CLI?

Claude CLI (claude.ai/code) is an interactive terminal-based interface for working with Claude AI. It provides:
- Direct filesystem access for reading/editing files
- Git integration for version control
- Command execution capabilities
- Persistent conversation context across sessions
- Specialized subagents for focused tasks

### Why Use Claude CLI for This Project?

**Benefits for web development**:
- **Direct file manipulation**: Edit HTML/CSS/JavaScript without copy-pasting
- **Testing integration**: Run Docker commands, check site status, view logs
- **Git workflow**: Commit, push, pull within the conversation
- **Context awareness**: Claude understands project structure from CLAUDE.md
- **Iterative development**: Make changes → test → refine in tight loop
- **Documentation**: Generate comprehensive docs (like this file)

### Typical Claude CLI Workflow for This Project

**Session Start**:
1. SSH into VPS or work locally
2. Navigate to dev directory: `cd /opt/dev/hensler_photography`
3. Launch Claude CLI: `claude` (or `claude chat`)
4. Claude reads CLAUDE.md automatically and understands project context

**Development Cycle**:
1. **User**: "I want to add new images to Adrian's gallery"
2. **Claude**: Reads sites/adrian/README.md, explains process
3. **User**: Uploads images or provides URLs
4. **Claude**: Downloads images to assets/gallery/, updates galleryImages array in index.html
5. **Claude**: Suggests testing: "Let's start the test server and verify"
6. **User**: Approves
7. **Claude**: Runs `docker compose up` command, provides test URL
8. **User**: Views site at http://localhost:8080/adrian, confirms it works
9. **Claude**: Commits changes with descriptive message
10. **User**: "Deploy to production"
11. **Claude**: Switches to /opt/prod/, pulls changes, restarts container, verifies health

**Complex Tasks (Design Changes)**:
1. **User**: "I want to redesign the header"
2. **Claude**: Invokes `web-design-critic` subagent to analyze current design
3. **Subagent**: Provides critique and 3-4 design options
4. **User**: Selects option 4 (ghost typography)
5. **Claude**: Invokes `modern-css-developer` subagent to implement
6. **Subagent**: Updates CSS, tests responsiveness
7. **Main Claude**: Coordinates testing and deployment

### Commands Claude Can Run

**File Operations**:
- `cat sites/adrian/index.html` - Read files
- `ls sites/adrian/assets/gallery/` - List directory contents
- `nano` / `vim` - Edit files (Claude uses its own editing tools)

**Docker Commands**:
```bash
# Start test container
docker compose -p hensler_test -f docker-compose.local.yml up -d

# Check running containers
docker ps

# View logs
docker compose logs web

# Restart production
cd /opt/prod/hensler_photography && docker compose restart
```

**Git Commands**:
```bash
# Check status
git status

# Create feature branch
git checkout -b feature/gallery-updates

# Add and commit
git add sites/adrian/
git commit -m "Add new gallery images"

# Push feature branch
git push origin feature/gallery-updates

# Create PR
gh pr create --title "Add new gallery images" --body "Description"

# After PR merged, pull in production
cd /opt/prod/hensler_photography && git pull origin main
```

**Testing Commands**:
```bash
# Run Playwright tests
npm test

# Check site health
curl -I https://adrian.hensler.photography/healthz

# Check site is running
curl https://adrian.hensler.photography/ | head -20
```

### Critical Workflow: Test Before Production

**Established Protocol** (after learning experience):

1. ✅ **Make changes** in `/opt/dev/hensler_photography`
2. ✅ **Deploy to test server** (port 8080)
3. ✅ **Show user the test URL**: "Please review at http://localhost:8080/adrian"
4. ✅ **Wait for explicit approval**: User says "looks good" or "deploy"
5. ✅ **Only then commit and push**: Never skip straight to production
6. ✅ **Deploy to production**: Pull in /opt/prod/ and restart
7. ✅ **Verify production**: Check health endpoints and user confirms

**Why This Matters**:
- User values correctness and security above speed
- User wants to see results before they go live
- Mistakes in production affect real visitors
- Testing catches issues early (broken images, CSS bugs, etc.)

### Context Management

**CLAUDE.md as Source of Truth**:
- Claude reads this file at session start
- Provides project overview, architecture, common commands
- Explains dual dev/prod environment
- Documents security headers, testing procedures

**Site-Specific Documentation**:
- `sites/adrian/README.md` - Comprehensive maintenance guide for Adrian's site
- `sites/liam/README.md` - (Future) Liam's site documentation
- `DEVELOPMENT.md` - Development best practices
- `BACKUP.md` - Backup and recovery procedures

**When Context Grows Large**:
- Claude CLI has token limits (~200k tokens per conversation)
- Use `/compact` command to summarize and continue
- Start new session for unrelated tasks
- Use subagents for focused work (doesn't consume main context)

### Best Practices for Working with Claude CLI

**Be Explicit About Expectations**:
- "Show me the test site before deploying" - Clear instruction
- "I want to see the result BEFORE production" - Sets expectation
- "Correctness is priority, doing things the right way" - Establishes standards

**Provide Feedback**:
- "That worked great" - Positive reinforcement
- "This isn't what I wanted" - Course correction
- "Let's try a different approach" - Alternative path

**Ask Questions**:
- "What are the options here?" - Claude provides multiple approaches
- "What would a designer do?" - Leverage Claude's knowledge
- "Explain how this works" - Understanding before changes

**Verify and Approve**:
- Always check test site before approving deployment
- Open browser DevTools (F12) to check console for errors
- Test on mobile viewport if changes affect responsive design

**Document Learnings**:
- Request documentation updates after complex work
- "Update CLAUDE.md with what we just learned"
- "Create a guide for this in sites/adrian/README.md"

### Error Handling and Debugging with Claude

**When something breaks**:
1. **Claude**: Checks Docker logs: `docker compose logs web`
2. **Claude**: Checks git status for unexpected changes
3. **Claude**: Reads browser console errors (if you share them)
4. **Claude**: Reviews recent file changes
5. **Claude**: Proposes fix and tests before deploying

**Common Issues Claude Can Solve**:
- **Image not loading**: Check filename spelling in galleryImages array
- **CSS not applying**: Check for syntax errors, missing semicolons
- **Docker container won't start**: Check Caddyfile syntax, port conflicts
- **Git conflicts**: Resolve merge conflicts, explain what happened
- **JavaScript errors**: Debug console errors, fix syntax issues

**When Claude Gets Stuck**:
- Provide more context: Share error messages, screenshots
- Break down the problem: "Let's focus on just the slideshow first"
- Try a different approach: "Let's roll back and try option 2"
- Restart conversation: `/compact` to summarize and continue fresh

### Adrian Site Current Architecture (Claude Reference)

**Key Facts for Claude to Remember**:
- **Single file design**: All HTML/CSS/JS in `sites/adrian/index.html`
- **API-driven gallery**: Loads from `/api/gallery/published?user_id=1` on page load
- **Responsive images**: Uses srcset with WebP variants (400px/800px/1200px)
- **Ghost typography**: Playfair Display, 300 weight, 0.45 opacity, lowercase
- **Slideshow**: Uses large variants (1200px), auto-cycles 5s, pauses on hover
- **Gallery grid**: Uses thumbnail variants (400px), responsive 3→2→1 columns
- **GLightbox**: Uses large variants (1200px), not full-res
- **Analytics**: Tracks impressions, clicks, views, scroll depth, duration
- **No frameworks**: Pure vanilla HTML/CSS/JS, no build process
- **Performance**: 10-20x faster than loading full originals

**Image Loading Strategy**:
- Grid thumbnails: 400px WebP (~10-30KB each)
- Hero slideshow: 800-1200px WebP responsive
- Lightbox: 1200px WebP (~40-150KB vs 2-5MB originals)
- Lazy loading: Native browser lazy loading
- srcset/sizes: Browser chooses appropriate variant

**Analytics Events Tracked**:
- `page_view` - Page load (site-level)
- `image_impression` - Image 50% visible in viewport
- `gallery_click` - Thumbnail clicked
- `lightbox_open` - Full-screen view opened
- `lightbox_close` - Full-screen closed (includes duration)
- `scroll_depth` - 25%, 50%, 75%, 100% milestones

**When making changes**:
- Preserve aspect ratios in gallery (user requirement: "not negotiable")
- Don't change image URLs - they come from API
- Check browser console for errors (remind user to do this)
- Test slideshow cycling and manual navigation
- Verify responsive breakpoints (mobile, tablet, desktop)
- Ensure WebP variants are loading (check Network tab)
- Verify analytics events fire (check Network tab for /api/track)

### Session Continuity

**Starting a New Session**:
- Claude reads CLAUDE.md automatically
- Previous conversation context is NOT retained (unless using /compact)
- User should provide context: "I'm continuing work on Adrian's gallery"
- Claude will read relevant files to catch up

**Resuming After Compaction**:
- `/compact` creates a summary of conversation
- New session starts with that summary
- Most technical details preserved
- Some conversational nuance lost

**Long-Term Project Memory**:
- Documentation (CLAUDE.md, README.md) serves as project memory
- Git commit messages document what changed and why
- Site-specific READMEs capture architecture decisions
- This allows Claude to help even without conversation history

### Recovery Without Claude CLI

**If you lose access to Claude CLI**, the documentation in this repo should be sufficient to continue:

**Essential Files**:
1. **sites/adrian/README.md** - Complete maintenance guide
2. **CLAUDE.md** - This file, project overview
3. **DEVELOPMENT.md** - Development workflow
4. **BACKUP.md** - Recovery procedures

**Alternative Tools**:
- Any text editor (nano, vim, VSCode) to edit index.html
- Standard git commands for version control
- Docker Compose commands for deployment
- Browser DevTools for debugging

**The documentation is designed to be Claude-independent**: All procedures are documented step-by-step with actual commands. You can follow them manually without AI assistance.

## Development Workflow

For detailed development best practices, see **DEVELOPMENT.md**.

Key workflow:
1. Make changes in `/opt/dev/hensler_photography`
2. Test locally on port 8080
3. Run Playwright tests: `npm test`
4. Commit and push to git
5. Deploy: `cd /opt/prod/hensler_photography && git pull && docker compose restart`
6. Verify production health checks
7. Create git tag for version (see **CHANGELOG.md**)

**Critical**: Production (`/opt/prod/`) and development (`/opt/dev/`) are now fully isolated. Changes in dev do NOT affect production until explicitly deployed.

## Backup and Recovery

For backup procedures, see **BACKUP.md**.

Automated daily backups via restic:
- Docker volumes (caddy-data, caddy-config)
- TLS certificates preserved
- 7-day retention policy
- Restore procedures documented

## Production Marker

Production code lives in `/opt/prod/hensler_photography/`. Development work happens in `/opt/dev/hensler_photography/`. These are fully isolated directories with separate git working trees.

**Never edit files in `/opt/prod/` directly.** Always make changes in `/opt/dev/`, test, commit, and deploy via git pull.
