# Integration Break-Point Documentation

**Date**: November 8, 2025
**Status**: Admin system complete, public gallery integration pending
**Branch**: `feature/backend-api`

---

## Current State Summary

### ✅ What's Complete

**Admin System (Port 4100)** - Fully functional:
- User authentication with JWT cookies
- Image upload with drag-and-drop
- Real-time upload progress tracking
- Batch upload (3 concurrent images max)
- AI-powered metadata generation (Claude Vision API)
- Full EXIF extraction and display
- Comprehensive metadata editing
- Technical validation (ISO, aperture, shutter speed, etc.)
- Re-extract EXIF button (free)
- Regenerate AI metadata button (~$0.02/image)
- Publish/unpublish images
- Featured image marking
- Gallery management with filtering
- AI cost tracking in database

**Database System**:
- SQLite at `/data/gallery.db`
- Multi-tenant support (users, images, variants, analytics, AI costs)
- Currently 4 images uploaded for user `adrian` (ID: 1)
- Images stored in `/app/assets/gallery/` (inside API container)

**Current Images in Database**:
1. `20251108_205306_a5ab42bec9b9205a.jpg` - "Rainbow Over the Harbor" (Published)
2. `20251108_203812_a5ab42bec9b9205a.jpg` - "Rainbow's End" (Featured)
3. `20251108_203653_6140238b60c9a9b7.jpg` - "Poseidon's Fury"
4. `20251108_203612_c1cd03e8db274946.jpg` - "Pensive Gaze"

### ⚠️ What's Disconnected

**Public Gallery (adrian.hensler.photography)** - Static site:
- Currently displays 10 **hardcoded Flickr images**
- Uses `galleryImages` array at line 422 in `sites/adrian/index.html`
- Images stored in `sites/adrian/assets/gallery/`
- **Does NOT pull from database**
- **Does NOT show uploaded images**

**The Gap**:
```
Admin Upload (Port 4100)          Public Site (Port 80/443)
        ↓                                    ↓
Database + API Container        Static JavaScript Array
   /app/assets/gallery/         sites/adrian/assets/gallery/
        ❌ NOT CONNECTED ❌
```

---

## Architecture Overview

### Current Directory Structure

```
/opt/dev/hensler_photography/
├── api/                           # Backend API (Python/FastAPI)
│   ├── routes/                    # API endpoints
│   │   ├── ingestion.py          # Upload, EXIF, AI, PATCH endpoints
│   │   └── auth.py               # Authentication
│   ├── services/
│   │   ├── claude_vision.py      # AI metadata generation
│   │   └── exif.py               # EXIF extraction
│   ├── templates/photographer/   # Admin UI templates
│   │   ├── upload.html           # Upload interface
│   │   └── gallery.html          # Gallery management
│   └── database.py               # SQLite schema
├── sites/
│   └── adrian/
│       ├── index.html            # PUBLIC SITE (static)
│       └── assets/gallery/       # Static Flickr images (10 files)
└── Caddyfile.local               # Routes both domains

Docker Volumes:
- API container: /app/assets/gallery/   (uploaded images, 4 files)
- Web container: /srv/sites/adrian/     (static site files)
```

### Port Architecture

- **Port 8080**: Public portfolios (adrian.hensler.photography, liam.hensler.photography)
- **Port 4100**: Admin interfaces (adrian.hensler.photography:4100, liam.hensler.photography:4100)

### Image Storage

**Admin Uploaded Images** (inside API container):
- Path: `/app/assets/gallery/`
- Served by API: `https://adrian.hensler.photography:4100/assets/gallery/filename.jpg`
- Format: `YYYYMMDD_HHMMSS_hash.jpg`
- Stored in database with metadata

**Static Site Images** (inside web container):
- Path: `/srv/sites/adrian/assets/gallery/`
- Served by Caddy: `https://adrian.hensler.photography/assets/gallery/filename.jpg`
- Format: Flickr filenames (e.g., `52871221196_95f87f72ce_b.jpg`)
- Hardcoded in JavaScript array

---

## Integration Options

### Option 1: API-Powered Dynamic Gallery (Recommended)

**Convert static site to fetch from database API**

**Changes needed**:
1. Create new API endpoint: `GET /api/gallery/published?user_id=1`
   - Returns published images only
   - Includes title, caption, category, thumbnail URLs
   - Orders by `sort_order` and `created_at`

2. Update `sites/adrian/index.html`:
   - Replace hardcoded `galleryImages` array
   - Fetch from API: `fetch('/api/gallery/published?user_id=1')`
   - Dynamically build slideshow and gallery grid

3. Serve uploaded images to public:
   - Add Caddy route to proxy `/gallery-images/` to API container
   - Or: Copy published images to static directory on publish

**Pros**:
- Real-time updates (no deployment needed)
- Images appear immediately when published
- Can include metadata (titles, captions)
- Supports unpublish/republish workflow

**Cons**:
- Requires JavaScript on public site (already uses JS)
- API must be running for gallery to work

---

### Option 2: Static File Generation

**Generate static JavaScript file on publish**

**Changes needed**:
1. Create script: `generate_gallery_json.py`
   - Queries database for published images
   - Writes `sites/adrian/assets/gallery-data.js` with image list
   - Copies images from `/app/assets/gallery/` to `/srv/sites/adrian/assets/gallery/`

2. Trigger generation:
   - Run script when image is published/unpublished
   - Or: Run as cron job every 5 minutes
   - Or: Manual deploy button in admin

3. Update `sites/adrian/index.html`:
   - Load `gallery-data.js` instead of hardcoded array

**Pros**:
- Works without API running
- Fast loading (static files)
- Traditional static site approach

**Cons**:
- Requires deployment step
- Images not immediately visible after publish
- Need to sync files between containers

---

### Option 3: Hybrid Approach

**Use API in development, static export for production**

**Changes needed**:
1. Implement Option 1 (API-powered) for testing
2. Add export script for production deployment
3. Switch between modes with environment variable

**Pros**:
- Best of both worlds
- Test dynamic, deploy static
- Can switch strategies later

**Cons**:
- More complexity
- Two codepaths to maintain

---

## Recommended Next Steps

### Immediate (Session 1-2 hours):

1. **Create Public Gallery API Endpoint**
   ```python
   # api/routes/gallery.py
   @router.get("/gallery/published")
   async def get_published_gallery(user_id: int):
       # Query published images
       # Return: id, filename, title, caption, thumbnail_url
   ```

2. **Update Public Site to Fetch from API**
   ```javascript
   // sites/adrian/index.html (around line 422)
   async function loadGallery() {
       const response = await fetch('/api/gallery/published?user_id=1');
       const images = await response.json();
       // Populate slideshow and grid
   }
   ```

3. **Configure Caddy to Serve Uploaded Images Publicly**
   ```
   # Caddyfile.local
   adrian.hensler.photography:8080 {
       handle /gallery-images/* {
           reverse_proxy api:8000
       }
   }
   ```

4. **Test Flow**:
   - Upload image at `:4100/manage/upload`
   - Mark as Published
   - Verify appears on `:8080/` homepage

### Future Enhancements:

5. **Add Admin "Preview Public Site" Button**
   - Shows how gallery will look before publishing

6. **Implement Sort Order Management**
   - Drag-and-drop reordering in admin gallery

7. **Add Thumbnail Generation**
   - Already have image_variants table
   - Generate WebP thumbnails for faster loading

8. **Cache Management**
   - Add cache headers to gallery API
   - Implement invalidation on publish/unpublish

---

## Current Database Schema (Relevant Tables)

```sql
-- Users
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    display_name TEXT,
    role TEXT DEFAULT 'photographer',
    subdomain TEXT
);

-- Images
CREATE TABLE images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    slug TEXT NOT NULL,
    title TEXT,
    caption TEXT,
    description TEXT,
    tags TEXT,
    category TEXT,
    published BOOLEAN DEFAULT 0,    -- ← Key field for public visibility
    featured BOOLEAN DEFAULT 0,
    sort_order INTEGER DEFAULT 0,   -- ← For custom ordering
    camera TEXT,
    lens TEXT,
    aperture TEXT,
    shutter_speed TEXT,
    iso TEXT,
    focal_length TEXT,
    location TEXT,
    date_taken DATETIME,
    width INTEGER,
    height INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Image variants (thumbnails, WebP, AVIF)
CREATE TABLE image_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER NOT NULL,
    format TEXT,
    size TEXT,
    filename TEXT,
    width INTEGER,
    height INTEGER,
    FOREIGN KEY (image_id) REFERENCES images(id) ON DELETE CASCADE
);

-- AI cost tracking
CREATE TABLE ai_costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    operation TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## API Endpoints Reference

### Authentication
- `POST /api/auth/login` - Login (returns JWT cookie)
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Get current user

### Image Management
- `POST /api/images/upload` - Upload image(s) with AI analysis
- `GET /api/images/list?user_id=1&limit=1000` - List images
- `GET /api/images/{image_id}` - Get image details with EXIF
- `PATCH /api/images/{image_id}` - Update metadata
- `DELETE /api/images/{image_id}` - Delete image
- `POST /api/images/{image_id}/publish` - Toggle publish status
- `POST /api/images/{image_id}/featured?featured=true` - Toggle featured
- `POST /api/images/{image_id}/reextract-exif` - Re-extract EXIF
- `POST /api/images/{image_id}/regenerate-ai` - Regenerate AI metadata (~$0.02)

### **MISSING** (needs to be created):
- `GET /api/gallery/published?user_id=1` - Get published images for public gallery

---

## Environment Variables

```bash
# In docker-compose.local.yml
DATABASE_PATH=/data/gallery.db
ANTHROPIC_API_KEY=sk-ant-...     # Required for AI features
JWT_SECRET_KEY=dev-secret-...    # Auto-generated in dev
```

---

## Cost Summary (This Session)

- **Total Cost**: $12.79
- **Duration**: 2h 44m (wall time), 42m 44s (API time)
- **Code Changes**: 1,580 lines added, 182 lines removed
- **Models Used**:
  - Claude Haiku: 118.6k input, 5.1k output ($0.15)
  - Claude Sonnet: 1.8k input, 116.2k output, 16.2M cache read ($12.64)

---

## Testing URLs

**Admin System** (authenticated):
- Login: `https://adrian.hensler.photography:4100/admin/login`
- Upload: `https://adrian.hensler.photography:4100/manage/upload`
- Gallery: `https://adrian.hensler.photography:4100/manage/gallery`
- Dashboard: `https://adrian.hensler.photography:4100/manage`

**Public Site** (open):
- Homepage: `https://adrian.hensler.photography:8080/`
- Static Gallery: Currently Flickr images only

**Credentials**:
- Username: `adrian`
- Password: `AdrianTest123!`

---

## Files to Review When Resuming

1. **Admin Upload Interface**:
   - `/opt/dev/hensler_photography/api/templates/photographer/upload.html`
   - Features: Batch upload, progress bars, EXIF editing, AI regeneration

2. **Gallery Management**:
   - `/opt/dev/hensler_photography/api/templates/photographer/gallery.html`
   - Features: Edit metadata, re-extract EXIF, regenerate AI, publish/unpublish

3. **Public Site**:
   - `/opt/prod/hensler_photography/sites/adrian/index.html`
   - Lines 422-433: `galleryImages` array (needs to become dynamic)

4. **API Routes**:
   - `/opt/dev/hensler_photography/api/routes/ingestion.py`
   - Contains all image management endpoints

5. **Database**:
   - `/opt/dev/hensler_photography/api/database.py`
   - Schema definitions

---

## Quick Commands

```bash
# Start test environment
cd /opt/dev/hensler_photography
docker compose -p hensler_test -f docker-compose.local.yml up -d

# Check logs
docker compose -p hensler_test logs api --tail 50
docker compose -p hensler_test logs web --tail 50

# Restart containers
docker compose -p hensler_test restart api web

# Access database
docker compose -p hensler_test exec api python -c "from api.database import get_db; conn = get_db().__enter__(); ..."

# View uploaded images
ls /opt/dev/hensler_photography/api/assets/gallery/

# Git status
git status
git log --oneline -10
```

---

## Decision Point: Gallery Integration Strategy

**You mentioned being open to blanking out the current gallery** - here are your options:

### A) Replace Static Gallery with API-Powered (Clean Slate)
- **Action**: Delete current 10 Flickr images
- **Result**: Gallery shows only uploaded images from database
- **Timeline**: 1-2 hours implementation
- **Risk**: Low (can always restore Flickr images)

### B) Keep Both Galleries Separate
- **Action**: Admin for new work, Flickr remains on site
- **Result**: Two galleries coexist
- **Timeline**: 0 hours (do nothing)
- **Risk**: None (but confusing long-term)

### C) Migrate Flickr Images to Database
- **Action**: Import 10 Flickr images into database
- **Result**: All images managed through admin
- **Timeline**: 2-3 hours (manual upload or script)
- **Risk**: Low (preserves existing gallery)

**My Recommendation**: **Option A** (Replace with API-powered)
- Clean break, forward-looking
- Uploaded images are better quality (have EXIF, AI metadata)
- Can always add Flickr images back through upload interface

---

## When You Resume

**First 5 Minutes**:
1. Read this document
2. Check if containers are running: `docker ps`
3. Verify database: `docker compose -p hensler_test exec api python -c "from api.database import get_all_users; print(get_all_users())"`
4. Check git branch: `git branch` (should be on `feature/backend-api`)

**Next Steps**:
1. Decide on integration strategy (A, B, or C above)
2. Create public gallery API endpoint
3. Update static site to fetch from API
4. Test publish/unpublish workflow
5. Deploy to production

---

## Key Achievements This Session

✅ Full image upload system with AI metadata
✅ Batch upload with concurrent processing
✅ Comprehensive EXIF extraction and editing
✅ Technical field validation (ISO, aperture, etc.)
✅ Re-extract EXIF and regenerate AI features
✅ Gallery management with publish/featured controls
✅ AI cost tracking in database
✅ Port architecture (8080 public, 4100 admin)

**What's Left**: Connect admin system to public gallery display

---

**End of Break-Point Document**
