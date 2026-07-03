# Hensler Photography - System Architecture

**Version**: 2.2.0
**Last Updated**: 2026-07-03

## Executive Summary

Multi-photographer portfolio management system with JWT-based authentication,
role-based (admin/photographer) access control, AI-powered image analysis, a
multi-tenant SQLite database, and WebP responsive image optimization.

**Current State**: Authenticated photographer management interface
(`/manage/*`) is live in production and has been since roughly late 2025.
Both Adrian (admin) and Liam (photographer) authenticate with username +
password, get httpOnly JWT session cookies, and manage their own galleries
through `/manage/dashboard`, `/manage/upload`, `/manage/gallery`,
`/manage/analytics`, and `/manage/settings`. A separate admin-only surface
remains at `/admin` and `/admin/upload` for Adrian.

**Roadmap Visibility**: High-level milestones are published in
`docs/ROADMAP_PUBLIC.md`. Detailed sprint notes, task breakdowns, and
retrospectives live in private storage; see `docs/planning/README.md` for
access guidance.

---

## Technology Stack

### Backend
- **Framework**: FastAPI 0.115.6 (Python 3.11+)
- **Database**: SQLite with multi-tenant schema (`aiosqlite` for async access)
- **Image Processing**: Pillow (PIL) 11.1.0 for WebP variant generation
- **EXIF Extraction**: piexif library
- **AI Analysis**: Anthropic Claude (Claude Vision API)
- **Authentication**: JWT tokens (PyJWT) in httpOnly cookies — **live in production**
- **Password Hashing**: bcrypt (direct, cost factor 12) — **live in production**
- **CSRF Protection**: token-based, via `itsdangerous` — **live in production**
- **Rate Limiting**: `slowapi` (per-IP limits on login, register, uploads, etc.) — **live in production**
- **Server**: Uvicorn ASGI server, behind Caddy which sets `X-Forwarded-For`
- **Logging**: JSON structured logging for AI-assisted debugging

### Frontend
- **Static Sites**: Vanilla HTML/CSS/JavaScript (no framework)
  - **Adrian's Portfolio**: Ghost typography design, GLightbox, pure CSS animations
  - **Liam's Portfolio**: Instagram-style portfolio
  - **Main Landing**: Directory hub linking to both portfolios
- **Management Interface**: Jinja2 server-side templates (autoescape on) under
  `api/templates/photographer/` (and a smaller `api/templates/admin/` set)
- **Styling**: Shared management shell (`api/static/css/manage-shell.css`,
  `api/static/css/variables.css`) plus per-site CSS for the public portfolios
- **Lightbox**: GLightbox for full-screen image viewing

### Infrastructure
- **Web Server**: Caddy 2 (automatic HTTPS, reverse proxy)
- **Container Orchestration**: Docker Compose
- **Deployment**: Dual environment (dev: port 8080, prod: ports 80/443)
- **Storage**: Docker volumes for persistent data (database + gallery images)
- **Backup**: Shell script (`scripts/backup.sh`) — `sqlite3 .backup` of the
  database plus `cp -a` of the gallery images volume, run via cron Mon/Thu
  2 AM, retaining only the **2 most recent backups** on the same host. See
  **BACKUP.md** for full detail (retention, restore steps, RTO). This is
  *not* Restic and there is no offsite/incremental history beyond those two
  snapshots — disaster recovery for full host loss relies on the hosting
  provider's periodic VPS snapshot.

---

## Directory Structure

```
/opt/dev/hensler_photography/          # Development environment
├── api/                               # FastAPI backend
│   ├── main.py                        # App entry point, routes for /admin, /manage, CORS, error handlers
│   ├── database.py                    # SQLite schema, connection helpers, inline migrations
│   ├── security.py                    # JWT_SECRET_KEY / CSRF_SECRET_KEY loading (fail-fast)
│   ├── csrf.py                        # CSRF token generation/verification
│   ├── rate_limit.py                  # slowapi limiter + per-endpoint rate limit presets
│   ├── errors.py                      # Structured ErrorResponse class
│   ├── logging_config.py              # JSON structured logging
│   ├── models.py                      # Pydantic request/response models
│   ├── audit.py                       # Audit log helpers (login, logout, password change, user create)
│   ├── routes/
│   │   ├── ingestion.py               # Image upload, listing, metadata, publish, delete (admin/self)
│   │   ├── auth.py                    # Login/logout/me/register/change-password, JWT dependency
│   │   ├── gallery.py                 # Public, unauthenticated gallery read endpoints
│   │   ├── photographer.py            # Photographer-scoped image CRUD (/api/photographer/*)
│   │   ├── analytics.py               # Analytics dashboards (overview, timeline, top images, etc.)
│   │   └── users.py                   # Current-user profile endpoints (/api/users/me)
│   ├── services/
│   │   ├── claude_vision.py           # Claude Vision API integration, AI metadata sanitization
│   │   ├── image_processor.py         # WebP variant generation
│   │   └── exif.py                    # EXIF metadata extraction
│   ├── templates/
│   │   ├── admin/                     # Admin-only templates (dashboard, upload, login)
│   │   └── photographer/              # Photographer management templates (live)
│   │       ├── base.html              # Shared layout, dark theme, FOUC prevention
│   │       ├── _header.html           # Shared nav (Dashboard/Gallery/Upload/Analytics/Settings)
│   │       ├── dashboard.html
│   │       ├── upload.html
│   │       ├── gallery.html
│   │       ├── analytics.html
│   │       └── settings.html
│   ├── static/                        # CSS, JavaScript assets (manage-shell.css, manage-header.js, ...)
│   ├── migrations/                    # Standalone, idempotent migration scripts (001, 002, 003, ...)
│   └── tests/                         # pytest suite (auth, security, gallery isolation, etc.)
├── sites/                             # Static portfolio sites
│   ├── main/                          # hensler.photography (directory hub)
│   │   └── index.html
│   ├── adrian/                        # adrian.hensler.photography
│   │   ├── index.html
│   │   └── assets/gallery/            # Served via Caddy reverse proxy to the API container
│   ├── liam/                          # liam.hensler.photography
│   │   └── index.html
│   └── shared/
│       └── gallery.js                 # Shared gallery/lightbox/analytics module (both sites)
├── tests/                             # Playwright end-to-end tests
│   ├── sites.spec.js
│   └── screenshots/
├── Caddyfile.local                    # Local development routing (port 8080)
├── docker-compose.local.yml           # Local development containers
├── Caddyfile                          # Production routing (ports 80/443)
├── docker-compose.yml                 # Production containers
├── ARCHITECTURE.md                    # This file
├── CLAUDE.md                          # Claude Code project instructions
├── DEVELOPMENT.md                     # Development best practices
├── BACKUP.md                          # Backup and recovery procedures (source of truth for backups)
├── CHANGELOG.md                       # Version history
└── docs/                              # Organized documentation
    ├── planning/                      # Public pointer to private planning docs
    ├── reviews/                       # Historical code/design reviews
    ├── setup/                         # One-time setup guides
    └── guides/                        # Implementation guides and operational runbooks

/opt/prod/hensler_photography/         # Production environment (mirrors dev)
```

---

## Multi-Tenant Database Schema

**Database File**: SQLite, path from `DATABASE_PATH` env var (`/data/gallery.db`
in containers). Schema lives in `api/database.py`; incremental changes are
applied two ways:
1. `run_migrations()` in `api/database.py` — inline, idempotent
   `ALTER TABLE ... ADD COLUMN` checks run automatically against the schema
   defined at the top of that file.
2. Standalone numbered scripts in `api/migrations/` (`001_add_password_hash.py`,
   `002_add_google_oauth.py`, `003_add_photographer_tracking.py`, ...) for
   larger, one-off changes that need custom seeding/verification logic and are
   run manually (`python -m api.migrations.00N_...`).

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT,             -- bcrypt hash; live in production
    display_name TEXT,
    role TEXT DEFAULT 'photographer',  -- 'admin' or 'photographer'
    subdomain TEXT,                 -- e.g. 'adrian', 'liam' — used for /manage access control
    bio TEXT,
    ai_style TEXT DEFAULT 'balanced',       -- Claude Vision prompt style preference
    track_own_activity BOOLEAN DEFAULT 1,   -- whether photographer's own visits count in analytics
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Seed data
INSERT INTO users (id, username, email, display_name, role, subdomain, bio) VALUES
(1, 'adrian', 'adrianhensler@gmail.com', 'Adrian Hensler', 'admin', 'adrian', '...'),
(2, 'liam', 'liam@hensler.photography', 'Liam Hensler', 'photographer', 'liam', '...');
```

Authentication is fully implemented (`api/routes/auth.py`): bcrypt-verified
login, JWT session cookie, role + subdomain-scoped authorization on every
`/manage/*` and `/api/photographer/*` route.

### Images Table
```sql
CREATE TABLE images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,               -- Foreign key to users.id
    filename TEXT NOT NULL,                 -- Generated filename: YYYYMMDD_HHMMSS_hash.jpg
    slug TEXT NOT NULL,                     -- URL-friendly slug for detail pages
    original_filename TEXT,                 -- User's original filename

    -- AI-generated metadata (Claude Vision; sanitized server-side before storage)
    title TEXT,
    caption TEXT,
    description TEXT,
    alt_text TEXT,                          -- required accessibility field
    tags TEXT,                              -- comma-separated keywords
    category TEXT,

    -- Per-field AI-vs-human-reviewed tracking
    ai_generated_title BOOLEAN DEFAULT 1,
    ai_generated_caption BOOLEAN DEFAULT 1,
    ai_generated_description BOOLEAN DEFAULT 1,
    ai_generated_alt_text BOOLEAN DEFAULT 1,
    ai_generated_tags BOOLEAN DEFAULT 1,
    ai_generated_category BOOLEAN DEFAULT 1,

    -- EXIF metadata
    camera_make TEXT,
    camera_model TEXT,
    lens TEXT,
    focal_length TEXT,
    aperture TEXT,
    shutter_speed TEXT,
    iso INTEGER,
    date_taken DATETIME,
    location TEXT,
    share_exif BOOLEAN DEFAULT 0,           -- whether EXIF is exposed on the public API

    -- Image properties
    width INTEGER,
    height INTEGER,
    aspect_ratio REAL,
    file_size INTEGER,

    -- Publishing controls
    published BOOLEAN DEFAULT 0,
    featured BOOLEAN DEFAULT 0,
    available_for_sale BOOLEAN DEFAULT 0,
    sort_order INTEGER DEFAULT 0,

    -- Soft delete (grace-period trash; see "Image Deletion" below)
    deleted_at DATETIME DEFAULT NULL,

    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(user_id, slug)
);

CREATE INDEX idx_images_user ON images(user_id);
CREATE INDEX idx_images_published ON images(published);
CREATE INDEX idx_images_slug ON images(user_id, slug);
```

### Image Variants Table
WebP responsive variants at different sizes for optimal performance.

```sql
CREATE TABLE image_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER NOT NULL,
    format TEXT,                           -- 'webp'
    size TEXT,                             -- 'large' (1200w), 'medium' (800w), 'thumbnail' (400w)
    filename TEXT,
    width INTEGER,
    height INTEGER,
    file_size INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
);

CREATE INDEX idx_variants_image ON image_variants(image_id);
```

### Image Events Table (Analytics — live)
Tracks impressions, clicks, lightbox opens/closes, scroll depth, and page
views for the public sites and powers `/manage/analytics`.

```sql
CREATE TABLE image_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER,
    event_type TEXT,               -- 'image_impression', 'gallery_click', 'lightbox_open', ...
    user_agent TEXT,
    referrer TEXT,
    ip_hash TEXT,                  -- SHA256(ip + JWT secret salt) — never stores raw IP
    session_id TEXT,               -- client-generated, ephemeral
    metadata TEXT,
    is_photographer BOOLEAN DEFAULT 0,  -- distinguishes owner's own visits from public traffic
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_events_image ON image_events(image_id);
CREATE INDEX idx_events_timestamp ON image_events(timestamp);
CREATE INDEX idx_is_photographer ON image_events(is_photographer);
```

### Audit Log Table (live)
```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action TEXT NOT NULL,          -- 'login', 'logout', 'password_change', 'user_create', ...
    resource_type TEXT,
    resource_id INTEGER,
    old_value TEXT,
    new_value TEXT,
    ip_address TEXT,
    user_agent TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### AI Cost Tracking Table (live)
```sql
CREATE TABLE ai_costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    operation TEXT NOT NULL,       -- 'analyze_image'
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    image_path TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Future / Not Yet Built
`products`, `orders`, and `sessions` tables exist in the schema as forward
scaffolding for a possible future print-sales feature; nothing in the
application currently reads or writes them.

---

## URL Structure

**Public Sites** (port 8080 locally, ports 80/443 in production):
- `hensler.photography` → `sites/main/` (directory hub linking to both portfolios)
- `liam.hensler.photography` → `sites/liam/` (Liam's portfolio)
- `adrian.hensler.photography` → `sites/adrian/` (Adrian's portfolio)
- Both portfolios load images dynamically via `GET /api/gallery/published?user_id=...`

**Photographer Management Interface** (JWT-authenticated, subdomain-scoped):
- `/manage` → Dashboard
- `/manage/upload` → Upload interface
- `/manage/gallery` → Gallery management (publish, feature, edit, delete)
- `/manage/analytics` → Engagement analytics
- `/manage/settings` → Account/profile/theme settings
- `/manage/login` → Login page (same template as `/admin/login`)
- Enforced by `get_current_user_for_subdomain()`: a photographer can only
  reach `/manage/*` on their own subdomain (e.g. Liam cannot access
  `adrian.hensler.photography/manage`); the admin role can access any
  subdomain's `/manage`.

**Admin-Only Interface** (JWT-authenticated, `role == 'admin'`):
- `/admin` → Admin dashboard
- `/admin/upload` → Upload interface (can target any user via `target_user_id`)
- `/admin/login` → Login page

**Backend API** (mounted on the same origin as the pages that call it):
- `/api/auth/*`, `/api/images/*`, `/api/photographer/*`, `/api/gallery/*`,
  `/api/analytics/*`, `/api/users/*`, `/api/track`
- `/assets/gallery/*` → Static file serving of originals + WebP variants

**Gallery Assets** (served via Caddy reverse proxy to the API container in
production; same path structure in dev):
- `adrian.hensler.photography/assets/gallery/*`
- `liam.hensler.photography/assets/gallery/*`

---

## Authentication Flow (Live)

**Technology**:
- **Password Hashing**: bcrypt (cost factor 12), called directly — no `passlib`
- **Tokens**: JWT via `PyJWT` (`jwt.encode`/`jwt.decode`, `HS256`)
- **Storage**: httpOnly cookies (`session_token`) — mitigates XSS token theft
- **Session Duration**: 24 hours
- **Security**: `secure=True` when `ENVIRONMENT=production`, `SameSite=Lax`
- **Password policy**: minimum 12 characters, upper/lower/digit/special
  character required, common-password blocklist (`validate_password()` in
  `api/routes/auth.py`)
- **Rate limiting**: login attempts limited to 5/minute per IP
  (`RATE_LIMITS["auth_login"]` in `api/rate_limit.py`)
- **CSRF**: state-changing routes (`logout`, uploads, edits, deletes,
  publish/feature toggles, etc.) require a verified CSRF token
  (`api/csrf.py`, `verify_csrf_token` dependency)

**Login Flow** (`POST /api/auth/login`, `api/routes/auth.py`):
```
1. User submits username + password (form-encoded) to /api/auth/login
2. Backend fetches user by username, verifies bcrypt hash
3. On success: generate JWT {user_id, username, role, exp: now+24h}
4. Set httpOnly cookie: session_token=<JWT>
5. Audit log entry written (api/audit.py: audit_login)
6. Client redirects to /manage or /admin
```

**Authorization** (`api/routes/auth.py`):
- `get_current_user(request)` — FastAPI dependency; reads `session_token`
  cookie, validates JWT, loads the user row, raises `HTTPException(401)` if
  missing/invalid/expired.
- `get_current_user_optional(request)` — same, but returns `None` instead of
  raising (used where anonymous access is also valid).
- `get_current_user_for_subdomain(request)` — wraps `get_current_user` and
  additionally checks that the authenticated user's `subdomain` matches the
  hostname being accessed, unless they are `admin`.
- Route-level ownership checks: `verify_image_ownership()` is implemented
  independently in both `api/routes/ingestion.py` and
  `api/routes/photographer.py` (image belongs to `current_user.id`, or the
  caller is `admin`); returns 404 rather than 403 to avoid confirming that a
  given image ID exists for another user.
- 401 responses to browser (HTML) requests for protected pages are redirected
  to `/manage/login` (see the `HTTPException` handler in `api/main.py`).

**Logout Flow**:
```
1. POST /api/auth/logout (requires valid session + CSRF token)
2. response.delete_cookie("session_token")
3. Audit log entry written (audit_logout)
```

---

## Permission Model (Live)

### Roles

**Admin** (Adrian):
- Access `/admin` and `/manage` on any subdomain
- View/upload/edit/delete/publish images for any user
- Create new users (`POST /api/auth/register`)
- View all analytics

**Photographer** (Liam, and any future non-admin users):
- Access `/manage` only on their own subdomain
- View only their own images (`/api/photographer/*` filters by `user_id`)
- Upload/edit/publish/delete only their own images
- View only their own analytics
- Cannot access `/admin` or another photographer's `/manage`

### Enforcement Strategy

**Database Level**: every photographer-facing query filters by
`user_id = ?`; admin-facing queries in `api/routes/ingestion.py` accept an
optional `user_id` filter but are not forced to it.

**API Level** (as implemented, `api/routes/ingestion.py` /
`api/routes/photographer.py`):
```python
async def verify_image_ownership(image_id: int, current_user: User) -> None:
    # SELECT user_id FROM images WHERE id = ?
    # 404 if missing, or if current_user.role != "admin" and row.user_id != current_user.id
    ...

@router.delete("/{image_id}")
async def delete_image(
    image_id: int,
    current_user: User = Depends(get_current_user),
    _csrf: str = Depends(verify_csrf_token),
):
    await verify_image_ownership(image_id, current_user)
    ...
```

**Frontend Level**: the shared header (`_header.html`) shows/hides the admin
console link based on `current_user.role`; each management page is still
independently protected server-side regardless of what the UI renders.

---

## API Architecture

### FastAPI Application Structure

**Main Application** (`api/main.py`):
- FastAPI instance with CORS middleware (restricted to the three production
  origins), `ProxyHeadersMiddleware` (trusts `X-Forwarded-For` from Caddy —
  safe because port 8000 is only reachable on the internal Docker network)
- Global exception handlers: structured JSON error responses, browser-aware
  401 → `/manage/login` redirect, catch-all handler that never leaks stack
  traces to the client
- Health check endpoints (`/healthz`, authenticated `/api/health`)
- HTML routes for `/admin`, `/admin/upload`, `/manage`, `/manage/upload`,
  `/manage/gallery`, `/manage/analytics`, `/manage/settings`, `/admin/login`,
  `/manage/login`
- Static file mounts: `/static` (CSS/JS), `/assets/gallery` (images)
- Includes all routers from `api/routes/`

**Routers** (`app.include_router(...)` in `api/main.py`):
- `api/routes/ingestion.py` — `/api/images/*` (upload, list, get, patch,
  publish, featured, exif-sharing, reextract-exif, regenerate-ai, delete)
- `api/routes/auth.py` — `/api/auth/*`
- `api/routes/gallery.py` — `/api/gallery/*` (public, unauthenticated)
- `api/routes/photographer.py` — `/api/photographer/*`
- `api/routes/analytics.py` — `/api/analytics/*`
- `api/routes/users.py` — `/api/users/*`

**Services** (business logic):
- `api/services/claude_vision.py` — AI image analysis; sanitizes AI-returned
  text fields before they are handed back to the caller for persistence
- `api/services/image_processor.py` — WebP variant generation
- `api/services/exif.py` — EXIF metadata extraction

**Utilities**:
- `api/errors.py` — Structured `ErrorResponse` class, error codes
- `api/logging_config.py` — JSON structured logging
- `api/database.py` — SQLite schema, connection helpers, inline migrations
- `api/security.py` — fail-fast loading of `JWT_SECRET_KEY` / `CSRF_SECRET_KEY`
- `api/csrf.py` — CSRF token generation/verification
- `api/rate_limit.py` — `slowapi` limiter + per-endpoint presets
- `api/audit.py` — audit log writers

### Core API Endpoints

**Image Management** (`/api/images`, `api/routes/ingestion.py`):
```
POST   /api/images/ingest                  # Upload and process image (rate limited)
GET    /api/images/list                    # List images (filtered by user/published/featured/category/search)
GET    /api/images/{id}                    # Get image details
PATCH  /api/images/{id}                    # Update metadata (validated)
POST   /api/images/{id}/publish            # Toggle published status
POST   /api/images/{id}/featured           # Toggle featured status
POST   /api/images/{id}/exif-sharing       # Toggle public EXIF exposure
POST   /api/images/{id}/reextract-exif     # Re-extract EXIF (free)
POST   /api/images/{id}/regenerate-ai      # Regenerate AI metadata (~$0.02)
DELETE /api/images/{id}                    # Soft-delete image (marks deleted_at; see below)
```

**Photographer-Scoped Image Management** (`/api/photographer`,
`api/routes/photographer.py`) — same underlying delete semantics as above,
scoped strictly to the caller's own images:
```
GET    /api/photographer/images            # List own images
GET    /api/photographer/images/{id}       # Get own image
PUT    /api/photographer/images/{id}       # Update own image metadata
PATCH  /api/photographer/images/{id}/publish
DELETE /api/photographer/images/{id}       # Soft-delete own image
```

**Authentication** (`/api/auth`, `api/routes/auth.py`):
```
POST   /api/auth/login                     # Username + password → JWT cookie (5/min rate limit)
POST   /api/auth/logout                    # Clear session (CSRF-protected)
GET    /api/auth/me                        # Get current user info
POST   /api/auth/register                  # Create user (admin only)
POST   /api/auth/change-password           # Update password
```

**Public Gallery** (`/api/gallery`, `api/routes/gallery.py`, no auth):
```
GET    /api/gallery/published?user_id=1    # Published images with WebP variant URLs
GET    /api/gallery/published/{slug}       # Single published image by slug
```

**Analytics** (`/api/analytics`, `api/routes/analytics.py`, authenticated):
```
GET    /api/analytics/overview
GET    /api/analytics/highlights
GET    /api/analytics/timeline
GET    /api/analytics/recent-engagement
GET    /api/analytics/top-images
GET    /api/analytics/referrers
GET    /api/analytics/category-performance
GET    /api/analytics/scroll-depth
GET    /api/analytics/image/{image_id}
```

**Tracking** (public, no auth):
```
POST   /api/track                          # Record engagement events (100/min rate limit)
```

**Health & Status**:
```
GET    /healthz                            # Simple health check (Docker)
GET    /api/health                         # Detailed diagnostics (authenticated)
```

### Image Ingest Flow

```
1. User uploads image via drag-and-drop or file picker (/manage/upload or /admin/upload)
2. JavaScript validates file type and size client-side
3. POST /api/images/ingest (multipart/form-data), CSRF-protected, rate-limited
4. FastAPI validates file type (MIME allowlist via python-magic) and size server-side
5. Generate unique filename: YYYYMMDD_HHMMSS_<hash>.jpg
6. Save original to /app/assets/gallery/{filename}
7. Extract EXIF metadata — failure is non-fatal, returns a warning
8. Analyze with Claude Vision API (title, caption, description, alt_text, tags, category)
   using the photographer's preferred style — failure falls back to filename-derived metadata
9. Sanitize AI-returned text fields server-side (strip HTML/script content) before persisting
10. Generate WebP variants at 3 sizes (1200px/800px/400px) — failure is non-fatal
11. Insert image row + variant rows
12. Return success response with image_id, metadata, and any warnings
```

**Structured Error Response** (`api/errors.py`):
```python
class ErrorResponse:
    success: bool = False
    error_code: str          # e.g. "VALIDATION_FILE_TOO_LARGE"
    user_message: str        # Human-readable explanation
    technical_details: str   # For developers/AI diagnosis
    context: dict            # Additional context (user_id, filename, etc.)
```

### AI Metadata Sanitization

`api/services/claude_vision.py` calls the Claude Vision API and parses its
JSON response. Before that metadata is returned to callers (and subsequently
written to the `images` table), text fields (`title`, `caption`,
`description`, `alt_text`, `tags`, `category`) are run through a server-side
sanitizer that strips HTML tags and neutralizes obviously dangerous content
(`<script>`, inline event-handler attributes, `javascript:` URIs) before
persistence. This is defense in depth: the public sites also
HTML-escape every field at render time via `escapeHtml()` in
`sites/shared/gallery.js`, and Jinja2 templates auto-escape by default — but
neither of those previously protected data stored via the `PATCH
/api/images/{id}` / `PUT /api/photographer/images/{id}` metadata-edit paths
or any future consumer that renders these fields without escaping.

### Image Deletion (Soft Delete)

Both delete endpoints (`DELETE /api/images/{id}` and
`DELETE /api/photographer/images/{id}`) share the same behavior: they set
`images.deleted_at = CURRENT_TIMESTAMP` rather than removing the row or
unlinking files immediately. Soft-deleted images are excluded from
`/api/gallery/published`, `/api/images/list`, `/api/photographer/images`, and
all ownership/ID lookups (`verify_image_ownership()` treats a soft-deleted
image as not found). Physical files (original + WebP variants) are removed
by a separate cleanup step after a grace period, rather than synchronously
in the request path — this avoids the previous behavior where a delete
request could unrecoverably destroy image files with no undo.

---

## Caddy Reverse Proxy Configuration

**Development** (`Caddyfile.local`): single `localhost:8080` block per
domain name, using path-based routing (`/liam`, `/adrian`) with
`uri strip_prefix` before serving static files; `/manage`, `/admin`, `/api`,
and `/assets/gallery` are reverse-proxied to `api:8000`.

**Production** (`Caddyfile`): three separate domain blocks
(`hensler.photography`, `liam.hensler.photography`,
`adrian.hensler.photography`), automatic HTTPS via Let's Encrypt, separate
TLS certificates per domain. Each domain proxies `/manage`, `/admin` (where
applicable), `/api`, and `/assets/gallery` to `api:8000` and serves its own
static site for everything else. Access logging is enabled on all three
domain blocks to support fail2ban-style abuse detection.

**Security Headers** (applied to all routes in both Caddyfiles):
```caddy
header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    X-Frame-Options "DENY"
    X-Content-Type-Options "nosniff"
    Referrer-Policy "strict-origin-when-cross-origin"
    Content-Security-Policy "..."
}
```

---

## Structured Logging for AI Diagnosis

**Configuration**: `api/logging_config.py` — JSON logs to stdout, captured by
`docker compose logs`. Every log call accepts an `extra={"context": {...}}`
payload (image_id, user_id, error_code, timing, etc.) so that both humans and
AI assistants can search/filter by field.

```bash
# Development
docker compose -p hensler_test -f docker-compose.local.yml logs -f api

# Production
docker compose logs -f api

# Filter by error code
docker compose logs api | grep "PROCESSING_CLAUDE_FAILED"
```

---

## Performance Considerations

**Image Optimization**: WebP variants at 3 sizes (1200px/800px/400px),
25–35% smaller than equivalent JPEGs; native lazy loading; responsive
`srcset` on the public sites.

**Database**: SQLite is appropriate at this scale (single-digit thousands of
images, low write volume, embedded — no network latency). Indexes exist on
`user_id`, `published`, `slug`, `image_id` (variants/events), and audit/AI
cost timestamps.

**Caching**: `GET /api/gallery/published` sets
`Cache-Control: public, max-age=300, stale-while-revalidate=60`. Static
assets are cached long-term by Caddy's defaults.

---

## Monitoring & Observability

**Health Checks**:
- `GET /healthz` — `{"status": "ok", "service": "api"}`, used by Docker
  Compose health checks.
- `GET /api/health` — authenticated, detailed diagnostics: database
  connectivity/latency, Claude API key presence, gallery storage free space.

---

## Deployment Architecture

### Environments

**Development** (`/opt/dev/hensler_photography/`):
- Port 8080 for public sites and `/manage`/`/admin`/`/api` (path- and
  host-based routing via `Caddyfile.local`)
- Docker Compose project: `hensler_test`
- Started with `docker compose -p hensler_test -f docker-compose.local.yml up -d`

**Production** (`/opt/prod/hensler_photography/`):
- Ports 80/443, one Caddy container fronting all three domains plus the API
- Docker Compose project: default (`docker-compose.yml`)
- Deployed via `git pull` + `docker compose restart` after a PR merges to
  `main` (direct pushes to `main` are blocked; CI must pass)

### Docker Compose Services

- **web** (Caddy 2): terminates TLS, reverse-proxies to `api:8000`, serves
  `sites/` as static files, mounts `caddy-data`/`caddy-config` volumes.
- **api** (FastAPI/Uvicorn): built from `api/Dockerfile`, requires
  `ANTHROPIC_API_KEY`, `DATABASE_PATH`, `JWT_SECRET_KEY`, and
  `CSRF_SECRET_KEY` in the environment (the app fails fast at import time if
  the JWT/CSRF secrets are missing or too short — see `api/security.py`).

### Deployment Workflow

```bash
# 1. Work in dev, test on port 8080
cd /opt/dev/hensler_photography

# 2. Create feature branch, commit, push
git checkout -b feature/my-improvement
git add <files>
git commit -m "Description"
git push origin feature/my-improvement

# 3. Open a PR (direct pushes to main are blocked; CI must pass)
gh pr create --title "..." --body "..."

# 4. After merge, deploy
cd /opt/prod/hensler_photography
git pull origin main
docker compose restart

# 5. Verify
curl -I https://hensler.photography/healthz
curl -I https://liam.hensler.photography/healthz
curl -I https://adrian.hensler.photography/healthz
```

---

## Backup

See **BACKUP.md** for the complete, authoritative procedure. Summary:
- `scripts/backup.sh` runs `sqlite3 .backup` (online backup, no downtime)
  plus `cp -a` of the gallery images volume.
- Scheduled via root crontab, Monday and Thursday at 2 AM
  (`0 2 * * 1,4 ... scripts/backup.sh`).
- Keeps only the **2 most recent** backups in
  `/opt/backups/hensler_photography/<timestamp>/` on the same host — this is
  protection against accidental deletion/corruption, not a substitute for
  offsite/disaster recovery.
- Full server loss is covered separately by the hosting provider's weekly
  VPS snapshot; worst-case data loss window is 3–4 days.

---

## Future Enhancements

These are aspirational and **not yet implemented**. Check `docs/ROADMAP_PUBLIC.md`
and grep the codebase before assuming any of the below exists.

### AI Chatbot Assistant (Planned)
Natural-language gallery management assistant using Claude's tool/function
calling, scoped to the authenticated user's own images, with guardrails
against destructive actions (no direct delete access, confirmation required
for publish/update).

### Static Site Generator (Planned)
Pre-rendered SEO-friendly individual photo detail pages at `/photo/{slug}`
with Open Graph metadata, sitemap generation.

### E-Commerce Integration (Planned)
Print sales via the existing (currently unused) `products`/`orders` schema,
Stripe integration, order management.

### Metrics/Observability Tooling (Planned)
Prometheus/Grafana or similar for request latency, error rate, and storage
trend dashboards, beyond the current JSON-log-and-grep workflow.

---

## Version History

See **CHANGELOG.md** for detailed version history and release notes.

---

## References

- **CLAUDE.md**: Instructions for Claude Code AI assistant (source of truth
  for current architecture — keep this file in sync with it)
- **docs/ROADMAP_PUBLIC.md**: Sanitized public roadmap with released and upcoming milestones
- **docs/planning/README.md**: Access notes for private sprint planning and task tracking
- **docs/guides/GIT_WORKFLOW.md**: Branching and deployment safeguards
- **DEVELOPMENT.md**: Development best practices and workflow
- **CHANGELOG.md**: Version history and release notes
- **BACKUP.md**: Backup and recovery procedures (authoritative)
- **sites/adrian/README.md**: Adrian's site maintenance guide
- **docs/reviews/**: Historical code/design reviews (archived)

---

**Last Updated**: 2026-07-03
**Maintained By**: Adrian Hensler
**Repository**: Public (https://github.com/adrianhensler/hensler-photography)
