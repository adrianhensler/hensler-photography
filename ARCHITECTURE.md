# Hensler Photography - System Architecture

**Version**: 2.0.0
**Last Updated**: 2025-11-02
**Current Sprint**: Sprint 3 (Error Handling & Logging) - Complete
**Next Sprint**: Sprint 4 (Multi-User Reorganization)

## Executive Summary

Multi-photographer portfolio management system with AI-powered image analysis, multi-tenant database architecture, WebP optimization, and planned authentication system for photographer-specific dashboards.

**Current State**: Admin interface with image upload, Claude Vision analysis, EXIF extraction, gallery management, and comprehensive error handling.

**Next Phase**: Multi-user authentication, photographer dashboards, admin interface migration to main domain, and future AI chatbot assistant.

---

## Technology Stack

### Backend
- **Framework**: FastAPI 0.115.4 (Python 3.11+)
- **Database**: SQLite with multi-tenant schema
- **Image Processing**: Pillow (PIL) for WebP variant generation
- **EXIF Extraction**: piexif library
- **AI Analysis**: Anthropic Claude 3.5 Sonnet (Claude Vision API)
- **Authentication**: JWT tokens with httpOnly cookies (Sprint 4 - planned)
- **Password Hashing**: bcrypt via passlib (Sprint 4 - planned)
- **Server**: Uvicorn ASGI server
- **Logging**: JSON structured logging for AI-assisted debugging

### Frontend
- **Static Sites**: Vanilla HTML/CSS/JavaScript (no framework)
  - **Adrian's Portfolio**: Ghost typography design, GLightbox, pure CSS animations
  - **Liam's Portfolio**: Instagram-style portfolio
  - **Main Landing**: Coming Soon page
- **Admin Interface**: Jinja2 server-side templates
- **Styling**: Apple-inspired design system
- **Lightbox**: GLightbox for full-screen image viewing

### Infrastructure
- **Web Server**: Caddy 2 (automatic HTTPS, reverse proxy)
- **Container Orchestration**: Docker Compose
- **Deployment**: Dual environment (dev: port 8080, prod: ports 80/443)
- **Storage**: Docker volumes for persistent data
- **Backup**: Restic with 7-day retention (automated daily backups)

---

## Directory Structure

```
/opt/dev/hensler_photography/          # Development environment
├── api/                               # FastAPI backend
│   ├── main.py                        # Application entry point, CORS, routes
│   ├── database.py                    # SQLite schema and initialization
│   ├── errors.py                      # Structured ErrorResponse class
│   ├── logging_config.py              # JSON structured logging
│   ├── routes/
│   │   ├── ingestion.py               # Image upload and management API
│   │   └── auth.py                    # (Sprint 4) Authentication endpoints
│   ├── services/
│   │   ├── claude_vision.py           # Claude Vision API integration
│   │   ├── image_processor.py         # WebP variant generation
│   │   └── exif.py                    # EXIF metadata extraction
│   ├── templates/
│   │   ├── admin/                     # Admin interface templates
│   │   │   ├── dashboard.html
│   │   │   ├── upload.html
│   │   │   ├── gallery.html
│   │   │   └── login.html             # (Sprint 4) Authentication
│   │   └── photographer/              # (Sprint 4) Photographer dashboards
│   │       ├── dashboard.html
│   │       ├── upload.html
│   │       └── gallery.html
│   ├── static/                        # CSS, JavaScript assets
│   ├── uploads/                       # Uploaded images (not in git)
│   │   ├── 1/                         # Adrian's images (user_id=1)
│   │   └── 2/                         # Liam's images (user_id=2)
│   └── hensler_photography.db         # SQLite database (not in git)
├── sites/                             # Static portfolio sites
│   ├── main/                          # hensler.photography
│   │   └── index.html
│   ├── adrian/                        # adrian.hensler.photography
│   │   ├── index.html
│   │   ├── assets/gallery/            # Symlink to api/uploads/1/
│   │   └── README.md                  # Site maintenance guide
│   └── liam/                          # liam.hensler.photography
│       ├── index.html
│       └── assets/gallery/            # Symlink to api/uploads/2/
├── tests/                             # Playwright end-to-end tests
│   ├── sites.spec.js
│   └── screenshots/
├── Caddyfile.local                    # Local development routing (port 8080)
├── docker-compose.local.yml           # Local development containers
├── Caddyfile                          # Production routing (ports 80/443)
├── docker-compose.yml                 # Production containers
├── ARCHITECTURE.md                    # This file
├── ROADMAP.md                         # Sprint timeline and features
├── TODO.md                            # Current task list
├── CLAUDE.md                          # Claude Code project instructions
├── DEVELOPMENT.md                     # Development best practices
├── BACKUP.md                          # Backup and recovery procedures
└── CHANGELOG.md                       # Version history

/opt/prod/hensler_photography/         # Production environment (mirrors dev)
```

---

## Multi-Tenant Database Schema

**Database File**: `hensler_photography.db` (SQLite)

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role TEXT DEFAULT 'photographer',  -- 'admin' or 'photographer'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    -- Sprint 4: password_hash TEXT (bcrypt hashed)
);

-- Seed data
INSERT INTO users (id, username, display_name, email, role) VALUES
(1, 'adrian', 'Adrian Hensler', 'adrian@hensler.photography', 'admin'),
(2, 'liam', 'Liam Hensler', 'liam@hensler.photography', 'photographer');
```

**Current State**: No authentication implemented, password_hash column to be added in Sprint 4.

### Images Table
```sql
CREATE TABLE images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,               -- Foreign key to users.id
    filename TEXT NOT NULL,                 -- Generated filename: YYYYMMDD_HHMMSS_hash.jpg
    slug TEXT NOT NULL,                     -- URL-friendly slug for detail pages
    original_filename TEXT NOT NULL,        -- User's original filename

    -- AI-generated metadata (Claude Vision)
    title TEXT,                             -- Concise, evocative title
    caption TEXT,                           -- Short description
    description TEXT,                       -- Detailed 2-3 sentence description
    tags TEXT,                              -- Comma-separated keywords
    category TEXT,                          -- Primary category (landscape, portrait, etc.)

    -- EXIF metadata
    camera_make TEXT,
    camera_model TEXT,
    lens TEXT,
    focal_length TEXT,                      -- e.g., "35mm"
    aperture TEXT,                          -- e.g., "f/2.8"
    shutter_speed TEXT,                     -- e.g., "1/250s"
    iso INTEGER,
    date_taken DATETIME,
    location TEXT,                          -- GPS coordinates (lat, lon)

    -- Image properties
    width INTEGER,
    height INTEGER,
    aspect_ratio REAL,
    file_size INTEGER,

    -- Publishing controls
    published BOOLEAN DEFAULT 0,
    featured BOOLEAN DEFAULT 0,
    available_for_sale BOOLEAN DEFAULT 0,

    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, slug)
);

-- Indexes for performance
CREATE INDEX idx_images_user_id ON images(user_id);
CREATE INDEX idx_images_published ON images(published);
CREATE INDEX idx_images_featured ON images(featured);
CREATE INDEX idx_images_slug ON images(user_id, slug);
```

### Image Variants Table
WebP responsive variants at different sizes for optimal performance.

```sql
CREATE TABLE image_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER NOT NULL,
    format TEXT NOT NULL,                  -- 'webp'
    size TEXT NOT NULL,                    -- 'large' (1200w), 'medium' (800w), 'thumbnail' (400w)
    filename TEXT NOT NULL,                -- e.g., "20241102_143045_abc123_large.webp"
    width INTEGER,
    height INTEGER,
    file_size INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
);

CREATE INDEX idx_variants_image_id ON image_variants(image_id);
```

**Purpose**:
- Serve appropriately sized images based on device (mobile, tablet, desktop)
- WebP format provides 25-35% smaller file sizes than JPEG
- Lazy loading optimizes page load performance

### Image Events Table (Analytics - Future Sprint 6)
Track views, clicks, shares for analytics dashboard.

```sql
CREATE TABLE image_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER,
    event_type TEXT NOT NULL,              -- 'view', 'click', 'share', 'download'
    user_id INTEGER,                       -- NULL for anonymous visitors
    session_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    referrer TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_events_image_id ON image_events(image_id);
CREATE INDEX idx_events_created_at ON image_events(created_at);
```

### Sessions Table (Authentication - Sprint 4)
User authentication sessions via JWT tokens.

```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,                   -- UUID or JWT ID
    user_id INTEGER NOT NULL,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
```

---

## URL Structure

### Current State (Sprint 3)

**Public Sites** (port 8080 locally, ports 80/443 in production):
- `hensler.photography` → sites/main/ (Coming Soon landing page)
- `liam.hensler.photography` → sites/liam/ (Liam's portfolio)
- `adrian.hensler.photography` → sites/adrian/ (Adrian's portfolio)

**Admin Interface** (port 4100, temporary - will be removed in Sprint 4):
- `adrian.hensler.photography:4100/admin` → Admin dashboard
- `adrian.hensler.photography:4100/admin/upload` → Image upload
- `adrian.hensler.photography:4100/admin/gallery` → Gallery management
- `adrian.hensler.photography:4100/api/*` → Backend API
- `adrian.hensler.photography:4100/assets/gallery/*` → Image files

### Future State (Sprint 4+)

**Public Sites** (unchanged):
- Same as current

**Admin Interface** (main domain, authenticated):
- `hensler.photography/admin` → Admin dashboard (Adrian only, all users visible)
- `hensler.photography/admin/upload` → Upload for any user
- `hensler.photography/admin/gallery` → View/edit all images
- `hensler.photography/api/*` → Backend API

**Photographer Dashboards** (subdomain /manage, authenticated):
- `liam.hensler.photography/manage` → Liam's dashboard (filtered to user_id=2)
- `liam.hensler.photography/manage/upload` → Upload to Liam's gallery
- `liam.hensler.photography/manage/gallery` → View/edit Liam's images only
- `adrian.hensler.photography/manage` → Adrian's photographer view (filtered to user_id=1)

**Gallery Assets** (served via Caddy reverse proxy):
- `liam.hensler.photography/assets/gallery/*` → Proxied from api/uploads/2/
- `adrian.hensler.photography/assets/gallery/*` → Proxied from api/uploads/1/

**Port 4100 removed entirely** (admin interface moves to main domain).

---

## Authentication Flow (Sprint 4 - To Be Implemented)

### Current State
**No authentication.** Admin interface is unprotected on port 4100 (dev environment only).

### Planned Implementation

**Technology**:
- **Password Hashing**: bcrypt via passlib (cost factor 12)
- **Tokens**: JWT via python-jose
- **Storage**: httpOnly cookies (XSS protection)
- **Session Duration**: 24 hours (configurable)
- **Security**: Secure flag in production (HTTPS-only), SameSite=Lax (CSRF protection)

**Login Flow**:
```
1. User visits /admin or /manage
2. If no valid session cookie → redirect to /admin/login
3. User submits username + password
4. Backend validates credentials (bcrypt verify)
5. Generate JWT token: {user_id, username, role, exp: 24h}
6. Set httpOnly cookie: session_token=<JWT>
7. Redirect to original destination (/admin or /manage)
```

**Authorization Flow**:
```
Every protected route requires: current_user = Depends(get_current_user)

get_current_user() function:
1. Read session_token cookie
2. Validate JWT signature and expiration
3. Load user from database by user_id
4. Return User object or raise HTTPException(401)

Routes check:
- Role: if current_user.role != 'admin': raise HTTPException(403)
- Ownership: if image.user_id != current_user.id: raise HTTPException(403)
```

**Logout Flow**:
```
1. User clicks "Logout"
2. POST /api/auth/logout
3. Clear session_token cookie
4. Redirect to /admin/login
```

**Code Example** (Sprint 4):
```python
# api/routes/auth.py
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, Response

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET_KEY")

async def get_current_user(request: Request) -> User:
    """Dependency that validates JWT and returns current user"""
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(401, "Not authenticated")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = get_user_by_id(payload["user_id"])
        if not user:
            raise HTTPException(401, "User not found")
        return user
    except JWTError:
        raise HTTPException(401, "Invalid token")

@router.post("/api/auth/login")
async def login(username: str, password: str, response: Response):
    user = get_user_by_username(username)
    if not user or not pwd_context.verify(password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    # Generate JWT
    token = jwt.encode(
        {"user_id": user.id, "username": user.username, "role": user.role, "exp": datetime.utcnow() + timedelta(hours=24)},
        SECRET_KEY,
        algorithm="HS256"
    )

    # Set httpOnly cookie
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=True,  # HTTPS only in production
        samesite="lax",
        max_age=86400  # 24 hours
    )

    return {"status": "success", "user": {"id": user.id, "username": user.username, "role": user.role}}

# Usage in routes
@app.get("/admin/dashboard")
async def dashboard(request: Request, current_user: User = Depends(get_current_user)):
    if current_user.role != 'admin':
        raise HTTPException(403, "Admin only")
    # Show all images from all users
    return templates.TemplateResponse("admin/dashboard.html", {...})
```

---

## Permission Model (Sprint 4)

### Roles

**Admin** (Adrian):
- Access /admin interface
- View all images from all photographers
- Upload images for any photographer
- Edit/delete any image
- Publish/unpublish any image
- Manage user accounts (create, edit, delete users)
- View all analytics

**Photographer** (Liam, others):
- Access /manage interface (subdomain only)
- View only their own images
- Upload images to their own gallery
- Edit/delete their own images only
- Publish/unpublish their own images
- View their own analytics only
- Cannot access /admin
- Cannot see other photographers' images

### Permission Matrix

| Action                    | Admin | Photographer (Own) | Photographer (Other) |
|---------------------------|-------|--------------------|----------------------|
| Access /admin             |   ✓   |         ✗          |          ✗           |
| Access /manage            |   ✓   |         ✓          |          ✗           |
| View all images           |   ✓   |         ✗          |          ✗           |
| View own images           |   ✓   |         ✓          |          ✗           |
| Upload image              |   ✓   |         ✓ (own)    |          ✗           |
| Edit own image            |   ✓   |         ✓          |          ✗           |
| Edit other's image        |   ✓   |         ✗          |          ✗           |
| Delete own image          |   ✓   |         ✓          |          ✗           |
| Delete other's image      |   ✓   |         ✗          |          ✗           |
| Publish/unpublish         |   ✓   |         ✓ (own)    |          ✗           |
| Manage users              |   ✓   |         ✗          |          ✗           |
| View all analytics        |   ✓   |         ✗          |          ✗           |
| View own analytics        |   ✓   |         ✓          |          ✗           |

### Enforcement Strategy

**Database Level**:
```sql
-- Non-admin users: Always filter by user_id
SELECT * FROM images WHERE user_id = ? AND id = ?

-- Admin users: Can query without filter
SELECT * FROM images WHERE id = ?
```

**API Level** (Sprint 4):
```python
@router.get("/api/images/list")
async def list_images(current_user: User = Depends(get_current_user)):
    query = "SELECT * FROM images"
    params = []

    # If not admin, restrict to user's own images
    if current_user.role != 'admin':
        query += " WHERE user_id = ?"
        params.append(current_user.id)

    return execute_query(query, params)

@router.put("/api/images/{id}")
async def update_image(id: int, current_user: User = Depends(get_current_user)):
    image = get_image_by_id(id)

    # Check ownership if not admin
    if current_user.role != 'admin' and image.user_id != current_user.id:
        raise HTTPException(403, "You can only edit your own images")

    # Update image...
```

**Frontend Level**:
- Show /admin navigation only to admin role
- Show /manage link on subdomain to all authenticated users
- Hide "All Photographers" dropdown from non-admin users
- Display only relevant images in gallery

---

## API Architecture

### FastAPI Application Structure

**Main Application** (`api/main.py`):
- FastAPI instance with CORS middleware
- Global exception handlers (structured error responses)
- Health check endpoints
- Admin UI routes (dashboard, upload, gallery HTML templates)
- Static file serving
- Includes routers from `api/routes/`

**Routers**:
- `api/routes/ingestion.py` - Image upload and management endpoints
- `api/routes/auth.py` (Sprint 4) - Authentication endpoints

**Services** (business logic):
- `api/services/claude_vision.py` - AI image analysis
- `api/services/image_processor.py` - WebP variant generation
- `api/services/exif.py` - EXIF metadata extraction

**Utilities**:
- `api/errors.py` - Structured ErrorResponse class, error codes
- `api/logging_config.py` - JSON structured logging
- `api/database.py` - SQLite schema and helpers

### Core API Endpoints

**Image Management**:
```
POST   /api/images/ingest                  # Upload and process image
GET    /api/images/list                    # List images (filtered by user)
GET    /api/images/{id}                    # Get image details
PATCH  /api/images/{id}                    # Update metadata
POST   /api/images/{id}/publish            # Toggle published status
POST   /api/images/{id}/featured           # Toggle featured status
DELETE /api/images/{id}                    # Delete image and variants
```

**Authentication** (Sprint 4):
```
POST   /api/auth/login                     # Username + password → JWT cookie
POST   /api/auth/logout                    # Clear session
GET    /api/auth/me                        # Get current user info
POST   /api/auth/register                  # Create user (admin only)
POST   /api/auth/change-password           # Update password
```

**Health & Status**:
```
GET    /healthz                            # Simple health check (Docker)
GET    /api/health                         # Detailed diagnostics
```

### Image Ingest API Example

**Request**:
```http
POST /api/images/ingest
Content-Type: multipart/form-data

Body:
- file: <binary image data>
- user_id: 1 (admin can specify, otherwise current_user.id)
- auto_publish: true (optional, default false)
```

**Response** (Success):
```json
{
  "success": true,
  "image_id": 123,
  "filename": "20241102_143045_abc123.jpg",
  "slug": "sunset-over-mountains",
  "ai_analysis": {
    "title": "Sunset Over Mountains",
    "caption": "Golden hour illuminates the peaks",
    "description": "A dramatic sunset bathes the mountain range in warm golden light, creating striking contrast between the illuminated peaks and shadowed valleys below.",
    "tags": ["landscape", "sunset", "mountains", "golden-hour", "dramatic"],
    "category": "landscape"
  },
  "exif": {
    "camera_make": "Canon",
    "camera_model": "EOS R5",
    "lens": "RF 24-70mm F2.8 L IS USM",
    "focal_length": "35mm",
    "aperture": "f/2.8",
    "shutter_speed": "1/250s",
    "iso": 200,
    "date_taken": "2024-10-15T14:30:22Z"
  },
  "variants": [
    {"size": "large", "width": 1200, "filename": "20241102_143045_abc123_large.webp"},
    {"size": "medium", "width": 800, "filename": "20241102_143045_abc123_medium.webp"},
    {"size": "thumbnail", "width": 400, "filename": "20241102_143045_abc123_thumbnail.webp"}
  ]
}
```

**Response** (Partial Success with Warnings):
```json
{
  "success": true,
  "image_id": 124,
  "filename": "20241102_150123_def456.jpg",
  "warnings": [
    {
      "code": "PROCESSING_EXIF_FAILED",
      "user_message": "Could not extract camera metadata from this image",
      "technical_details": "No EXIF data found in image headers"
    },
    {
      "code": "AUTH_MISSING_KEY",
      "user_message": "AI captions unavailable - please configure Anthropic API key in environment",
      "technical_details": "ANTHROPIC_API_KEY not set"
    }
  ]
}
```

**Response** (Error):
```json
{
  "success": false,
  "error_code": "VALIDATION_FILE_TOO_LARGE",
  "user_message": "Image file is too large (32.5 MB). Maximum size is 20 MB",
  "technical_details": "file_size=34078720 bytes, max_size=20971520 bytes",
  "context": {
    "filename": "huge_photo.jpg",
    "user_id": 1
  }
}
```

---

## Caddy Reverse Proxy Configuration

### Current Configuration (Sprint 3)

**Development** (`Caddyfile.local`):
```caddy
# Public sites (port 8080)
hensler.photography:8080 {
    root * /srv/sites/main
    file_server
    encode zstd gzip
}

liam.hensler.photography:8080 {
    root * /srv/sites/liam
    file_server
    encode zstd gzip
}

adrian.hensler.photography:8080 {
    root * /srv/sites/adrian
    file_server
    encode zstd gzip
}

# Admin interface (port 4100, temporary)
adrian.hensler.photography:4100 {
    handle /admin* {
        reverse_proxy api:8000
    }
    handle /api/* {
        reverse_proxy api:8000
    }
    handle /assets/gallery/* {
        reverse_proxy api:8000
    }
}
```

### Future Configuration (Sprint 4)

**Development** (`Caddyfile.local`):
```caddy
# Main domain with admin interface (port 8080)
hensler.photography:8080 {
    handle /admin* {
        reverse_proxy api:8000  # Admin interface (authenticated)
    }
    handle /api/* {
        reverse_proxy api:8000  # API endpoints
    }
    handle /assets/gallery/* {
        reverse_proxy api:8000  # Serve gallery images
    }
    handle {
        root * /srv/sites/main
        file_server
        encode zstd gzip
    }
}

# Subdomains with photographer dashboards (port 8080)
liam.hensler.photography:8080 {
    handle /manage* {
        reverse_proxy api:8000  # Liam's dashboard (user_id=2)
    }
    handle /assets/gallery/* {
        reverse_proxy api:8000  # Liam's images only
    }
    handle {
        root * /srv/sites/liam
        file_server
        encode zstd gzip
    }
}

adrian.hensler.photography:8080 {
    handle /manage* {
        reverse_proxy api:8000  # Adrian's dashboard (user_id=1)
    }
    handle /assets/gallery/* {
        reverse_proxy api:8000  # Adrian's images only
    }
    handle {
        root * /srv/sites/adrian
        file_server
        encode zstd gzip
    }
}

# Port 4100 removed entirely
```

**Production** (`Caddyfile`):
- Same structure as development
- No port numbers (Caddy handles 80/443 automatically)
- Automatic HTTPS via Let's Encrypt
- Separate TLS certificates per domain

**Security Headers** (applied to all routes):
```caddy
header {
    Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
    X-Frame-Options "DENY"
    X-Content-Type-Options "nosniff"
    Referrer-Policy "strict-origin-when-cross-origin"
}
```

---

## Image Processing Pipeline

### Upload Flow

```
1. User uploads image via drag-and-drop or file picker
2. JavaScript validates file type (JPEG, PNG, WebP) and size (<20MB) client-side
3. POST to /api/images/ingest with multipart/form-data
4. FastAPI validates file type and size server-side
5. Generate unique filename: YYYYMMDD_HHMMSS_<hash>.jpg
6. Save original to /app/uploads/{user_id}/{filename}
7. Extract EXIF metadata (camera, lens, settings, GPS)
   - If fails: Log warning, continue with null values
8. Analyze with Claude Vision API (title, caption, description, tags, category)
   - If fails: Use fallback metadata, return warning
9. Generate WebP variants at 3 sizes:
   - Large: 1200px width (desktop)
   - Medium: 800px width (tablet)
   - Thumbnail: 400px width (mobile)
   - If fails: Continue without variants, return warning
10. Insert record into images table with all metadata
11. Insert records into image_variants table (one per variant)
12. Return success response with image_id, metadata, warnings (if any)
13. Frontend displays preview with editable metadata fields
```

### Error Handling Strategy

**Graceful Degradation**:
- **EXIF extraction fails**: Continue with null metadata, return warning
- **Claude Vision fails**: Use fallback metadata ("Untitled", "No description"), return warning
- **WebP generation fails**: Keep original only, return warning
- **Database insert fails**: Clean up files, return error, rollback

**Structured Error Response** (`api/errors.py`):
```python
class ErrorResponse:
    success: bool = False
    error_code: str          # e.g., "VALIDATION_FILE_TOO_LARGE"
    user_message: str        # Human-readable explanation
    technical_details: str   # For developers/AI diagnosis
    context: dict            # Additional context (user_id, filename, etc.)
```

### Claude Vision Prompt

**System Prompt** (`services/claude_vision.py`):
```
You are an expert photography curator analyzing images for a professional
portfolio website. Analyze this image and provide:

1. **Title** (5-10 words max): Concise, evocative, captures the essence
2. **Caption** (1 sentence): Brief description for thumbnail hover
3. **Description** (2-3 sentences): Detailed analysis focusing on:
   - Subject and composition
   - Lighting and mood
   - Technical excellence or artistic merit
4. **Tags** (5-10 keywords): Relevant categorization keywords:
   - Subject matter: landscape, portrait, architecture, wildlife, etc.
   - Style: black-and-white, long-exposure, minimalist, dramatic, etc.
   - Mood: serene, vibrant, moody, ethereal, etc.
   - Technical: golden-hour, blue-hour, bokeh, reflection, etc.
5. **Category** (single word): Primary category (landscape, portrait, architecture,
   wildlife, abstract, street, event, macro, aerial)

Return JSON format:
{
    "title": "...",
    "caption": "...",
    "description": "...",
    "tags": ["tag1", "tag2", ...],
    "category": "landscape"
}
```

**Response Handling**:
- Parse JSON response
- Store in `title`, `caption`, `description`, `tags`, `category` columns
- Log to structured JSON logs with analysis_time_ms

---

## Security Model

### Current Security Posture (Sprint 3)

**Strengths**:
- Docker container isolation (non-root user)
- Separate dev/prod environments
- Security headers on all responses (HSTS, X-Frame-Options, etc.)
- Structured error handling (no stack trace leaks to frontend)
- Input validation (file type, size limits)
- Parameterized SQL queries (SQL injection prevention)
- Jinja2 auto-escaping (XSS prevention)

**Weaknesses** (to be addressed in Sprint 4):
- ❌ No authentication on admin interface
- ❌ Admin port (4100) open to network (dev only, but still vulnerable)
- ❌ No rate limiting
- ❌ No CSRF protection
- ❌ No user isolation (photographers can theoretically access other's images)

### Planned Security Improvements (Sprint 4)

**Authentication**:
- bcrypt password hashing (cost factor 12)
- JWT tokens with 24-hour expiration
- httpOnly cookies (prevents XSS attacks on tokens)
- Secure flag in production (HTTPS-only cookies)
- SameSite=Lax (CSRF protection)

**Authorization**:
- Role-based access control (admin, photographer)
- User ownership checks on all image operations
- Admin-only endpoints (user management, global analytics)
- Database-level filtering by user_id for non-admin users

**Input Validation**:
- File type whitelist (JPEG, PNG, WebP only)
- File size limit (20MB max, configurable)
- Filename sanitization (prevent path traversal)
- Metadata sanitization (XSS prevention in descriptions/tags)
- SQL injection protection (parameterized queries)

**Rate Limiting** (Sprint 5 - Future):
- Login attempts: 5 failures/hour per IP → lockout
- Image upload: 100 uploads/day per user
- API requests: 1000 requests/hour per user
- Chatbot messages: 20 messages/hour per user

**CSRF Protection** (Sprint 4):
- CSRF tokens for state-changing operations (POST, PUT, DELETE)
- SameSite=Lax on session cookies
- Origin/Referer header validation

---

## Structured Logging for AI Diagnosis

### JSON Log Format

**Configuration**: `api/logging_config.py`

**Info Log Example**:
```json
{
    "timestamp": "2025-11-02T14:30:45.123Z",
    "level": "INFO",
    "logger": "hensler_photography.services.claude_vision",
    "message": "Claude Vision analysis complete",
    "module": "claude_vision",
    "function": "analyze_image",
    "line": 87,
    "context": {
        "image_id": 42,
        "filename": "sunset_mountains.jpg",
        "user_id": 1,
        "analysis_time_ms": 1234,
        "tags_count": 7
    }
}
```

**Error Log Example**:
```json
{
    "timestamp": "2025-11-02T14:31:12.456Z",
    "level": "ERROR",
    "logger": "hensler_photography.routes.ingestion",
    "message": "Image upload failed",
    "module": "ingestion",
    "function": "ingest_image",
    "line": 156,
    "error_code": "PROCESSING_CLAUDE_FAILED",
    "context": {
        "user_id": 1,
        "filename": "test.jpg",
        "file_size": 12345678
    },
    "exception": {
        "type": "AnthropicAPIError",
        "message": "Rate limit exceeded (429)",
        "traceback": "Traceback (most recent call last):\n  File..."
    }
}
```

**Purpose**:
- Enable Claude Code to quickly diagnose issues
- Machine-readable format for log analysis tools
- Preserve context across service boundaries
- Track performance metrics (analysis_time_ms, file_size, etc.)

**View Logs**:
```bash
# Development
docker compose -p hensler_test logs -f api

# Production
docker compose logs -f api

# Filter by error code
docker compose logs api | grep "PROCESSING_CLAUDE_FAILED"
```

---

## Performance Considerations

### Image Optimization

**WebP Variants**:
- 25-35% smaller file sizes compared to JPEG
- Three sizes for responsive images:
  - Large (1200w): Desktop displays
  - Medium (800w): Tablets and small laptops
  - Thumbnail (400w): Mobile devices and grid previews
- Lazy loading: Images load only when scrolled into viewport
- CDN-ready: Static assets can be moved to CDN for global distribution

**Gallery Performance**:
- Grid uses `object-fit: contain` to preserve aspect ratios
- IntersectionObserver for staggered reveal animations
- Preload critical images above the fold
- Fade-in animations for progressive enhancement

### Database Performance

**SQLite Suitability**:
- Ideal for read-heavy, low-write workloads
- Handles thousands of images efficiently
- Single-file database simplifies backups
- No network latency (embedded database)

**Indexes**:
```sql
CREATE INDEX idx_images_user_id ON images(user_id);
CREATE INDEX idx_images_published ON images(published);
CREATE INDEX idx_images_featured ON images(featured);
CREATE INDEX idx_images_slug ON images(user_id, slug);
CREATE INDEX idx_variants_image_id ON image_variants(image_id);
```

**Future Optimization** (if needed):
- Connection pooling (currently not implemented)
- Read replicas for public site queries
- Migration to PostgreSQL for multi-server deployments

### Caching Strategy

**Browser Caching**:
- Static assets: `Cache-Control: max-age=31536000` (1 year)
- Images: `Cache-Control: max-age=2592000` (30 days)
- HTML: `Cache-Control: no-cache` (always revalidate)

**CDN Integration** (Future):
- Cloudflare or AWS CloudFront for image delivery
- Edge caching for global performance
- Automatic WebP conversion at edge

**API Caching** (Future - Sprint 6):
- Redis for frequently accessed data (featured images, popular tags)
- Cache invalidation on image updates
- TTL-based expiration

---

## Monitoring & Observability

### Logging

**Structured JSON Logs** (`api/logging_config.py`):
- All requests logged with context (user_id, image_id, etc.)
- Errors include full stack traces
- Performance metrics (processing_time_ms, file_size, etc.)
- Searchable by error code, user, timestamp
- Output to stdout (Docker Compose captures to docker logs)

### Health Checks

**Simple** (`GET /healthz`):
```json
{"status": "ok"}
```
- Used by Docker Compose health checks
- Returns 200 if application is running

**Detailed** (`GET /api/health`):
```json
{
    "status": "healthy",
    "database": {
        "status": "ok",
        "latency_ms": 2.3,
        "images_count": 127,
        "users_count": 2
    },
    "storage": {
        "status": "ok",
        "total_gb": 50.0,
        "used_gb": 12.5,
        "free_gb": 37.5
    },
    "ai": {
        "status": "configured",
        "api_key_set": true
    },
    "warnings": []
}
```
- Comprehensive diagnostics for troubleshooting
- Database connectivity and latency
- Storage usage metrics
- Claude API configuration status

### Metrics (Future - Sprint 6)

**Planned Metrics**:
- Request counts and latency by endpoint
- Error rates by error_code
- Image processing times (EXIF, AI, WebP generation)
- Storage usage trends
- User activity metrics (uploads per day, etc.)

**Potential Tools**:
- Prometheus for metrics collection
- Grafana for visualization
- Alerts for error rate spikes, storage limits

---

## Deployment Architecture

### Environments

**Development** (`/opt/dev/hensler_photography/`):
- Port 8080: Public sites
- Port 4100: Admin interface (temporary, Sprint 4 will remove)
- Docker Compose project: `hensler_test`
- Database: `/opt/dev/hensler_photography/api/hensler_photography.db`
- Images: `/opt/dev/hensler_photography/api/uploads/`
- Purpose: Testing and iteration before production

**Production** (`/opt/prod/hensler_photography/`):
- Ports 80/443: All sites and admin
- Docker Compose project: default
- Database: `/opt/prod/hensler_photography/api/hensler_photography.db`
- Images: `/opt/prod/hensler_photography/api/uploads/`
- Purpose: Live site serving visitors

### Docker Compose Services

**web** (Caddy):
```yaml
services:
  web:
    image: caddy:2-alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - ./sites:/srv/sites
      - ./api/uploads:/srv/uploads  # Serve gallery images
      - caddy-data:/data
      - caddy-config:/config
    restart: unless-stopped
```

**api** (FastAPI):
```yaml
  api:
    build: ./api
    volumes:
      - ./api:/app
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - DATABASE_PATH=/app/hensler_photography.db
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}  # Sprint 4
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**Networking**: Internal Docker network, Caddy reverse proxies to `api:8000`.

### Deployment Workflow

```bash
# 1. Make changes in development
cd /opt/dev/hensler_photography
# ... edit files ...

# 2. Test locally
docker compose -p hensler_test up -d
curl http://localhost:8080/

# 3. Run Playwright tests
npm test

# 4. Commit to git
git add .
git commit -m "Description of changes"
git push origin feature/backend-api

# 5. Deploy to production
cd /opt/prod/hensler_photography
git pull origin main
docker compose restart

# 6. Verify production
curl -I https://hensler.photography/healthz
curl -I https://adrian.hensler.photography/
```

---

## Future Enhancements

### Sprint 5: AI Chatbot Assistant (Planned)

**Goal**: Give photographers an AI assistant to manage their galleries via natural conversation.

**Technology**:
- Anthropic Claude 3.5 Sonnet API
- Tool/function calling for gallery operations
- Streaming responses for real-time interaction
- Persistent conversation history per user

**Architecture**:
```
User types message → Chat Widget (JS) → POST /api/chat/message
                                              ↓
                                    Validate session (get_current_user)
                                              ↓
                                    Load conversation history
                                              ↓
                                    Call Claude API with tools
                                              ↓
                                    Claude analyzes request, calls tools
                                              ↓
                                    Execute tool functions (filtered by user_id)
                                              ↓
                                    Return tool results to Claude
                                              ↓
                                    Stream response to user
                                              ↓
                                    Save message to database
```

**Tool Functions**:
- `list_images(filters)` - Search gallery with natural language
- `get_image_details(image_id)` - Show full metadata
- `suggest_tags(image_id)` - AI-powered tag suggestions
- `update_metadata(image_id, changes)` - Edit title/description/tags
- `publish_image(image_id)` - Make image visible on public site
- `find_similar(image_id)` - Find similar images in gallery

**Guardrails**:
- System prompt explicitly restricts to authenticated user_id
- All tool functions verify image ownership before executing
- Cannot call DELETE endpoints (safety measure)
- Requires confirmation for state-changing actions (publish, update)
- Rate limiting: 20 messages/hour per user
- Cannot access admin functions (user creation, other photographers' data)

**UI Design**:
- Persistent chat widget in /manage dashboard (bottom-right corner)
- Expandable/collapsible panel
- Message history preserved per session
- Suggested prompts: "Show me unpublished images", "Find landscapes from October", "Suggest tags for image 42"

**Implementation Estimate**: 20-25 hours (Sprint 5)

### Sprint 6: Analytics Dashboard

**Goal**: Track and visualize image performance metrics.

**Features**:
- Image views and clicks tracking
- Popular images report (most viewed/clicked)
- Geographic visitor distribution (if available)
- Time-series charts (views over time)
- Tag popularity analysis
- Export analytics data to CSV

**Technology**:
- `image_events` table (already defined in schema)
- Chart.js for visualization
- Aggregation queries for reporting

### Sprint 7+: Static Site Generator

**Goal**: Generate SEO-friendly static photo detail pages.

**Features**:
- Pre-render individual photo pages at `/photo/{slug}`
- Server-side generated HTML with Open Graph meta tags
- Pagination for gallery grids
- Export static JSON for frontend consumption
- Sitemap generation for search engines

### Future: E-Commerce Integration

**Goal**: Enable print sales and ordering.

**Features**:
- Print size and framing options
- Stripe payment integration
- Order management dashboard
- Shipping tracking
- Customer communication

---

## Version History

See **CHANGELOG.md** for detailed version history and release notes.

**Current Version**: 2.0.0 (Sprint 3 Complete)
- ✅ Sprint 1: Foundation (Database, FastAPI, Docker, Caddy)
- ✅ Sprint 2: Image Ingestion (Upload, EXIF, Claude Vision, WebP variants)
- ✅ Sprint 2.5: Gallery Management (View, edit, publish, bulk actions)
- ✅ Sprint 3: Error Handling & Logging (Structured errors, JSON logs)
- 📋 Sprint 4: Multi-User Auth & Dashboards (Planned)
- 📋 Sprint 5: AI Chatbot Assistant (Planned)
- 📋 Sprint 6: Analytics Dashboard (Planned)

---

## References

- **CLAUDE.md**: Instructions for Claude Code AI assistant
- **ROADMAP.md**: Sprint timeline and feature roadmap
- **TODO.md**: Current task list and Sprint 4 plan
- **DEVELOPMENT.md**: Development best practices and workflow
- **CHANGELOG.md**: Version history and release notes
- **BACKUP.md**: Backup and recovery procedures
- **sites/adrian/README.md**: Adrian's site maintenance guide

---

**Last Updated**: 2025-11-02
**Maintained By**: Adrian Hensler
**Repository**: Public (https://github.com/adrianhensler/hensler-photography)
**License**: All Rights Reserved (consider adding LICENSE file to specify terms)
