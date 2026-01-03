# Database Documentation

## Overview

The Hensler Photography backend uses **SQLite** for data storage. The database is automatically created and initialized when the API starts for the first time.

**Database Location:**
- Docker container: `/data/gallery.db`
- Host system (mapped volume): `gallery-data` Docker volume

**Key Features:**
- Multi-photographer support (user isolation via `user_id`)
- EXIF metadata storage (camera, lens, exposure settings)
- AI-generated metadata (tags, captions, descriptions)
- Image variants tracking (original, WebP, thumbnails)
- Publishing workflow (public/private images)
- Cost tracking for AI API calls

---

## Database Creation

### Automatic Initialization

The database is automatically created when you start the API container:

```bash
cd /opt/dev/hensler_photography
docker compose -p hensler_test -f docker-compose.local.yml up -d api
```

**What Happens:**
1. API starts and checks if `/data/gallery.db` exists
2. If not found, creates database with full schema (see `api/database.py`)
3. Seeds initial data (admin user, photographer users)
4. Ready to accept uploads

### Manual Database Creation

If you need to manually recreate the database:

```bash
# Stop containers
docker compose -p hensler_test -f docker-compose.local.yml down

# Remove database volume
docker volume rm hensler_photography_gallery-data

# Restart (will recreate database)
docker compose -p hensler_test -f docker-compose.local.yml up -d
```

---

## Database Schema

### Core Tables

#### `users` - Photographer accounts

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role TEXT NOT NULL DEFAULT 'photographer',  -- 'admin' or 'photographer'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**Seed Data:**
- `adrian` (id=1, role='admin') - System administrator
- `liam` (id=2, role='photographer') - Photographer account

**Usage:**
- Each photographer logs in with username/password
- `role='admin'` has access to `/admin` routes
- `role='photographer'` has access to `/manage` routes

---

#### `images` - Uploaded photos with metadata

```sql
CREATE TABLE images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,               -- FK to users.id (photographer ownership)

    -- File information
    filename TEXT NOT NULL,                 -- Storage filename (20251108_205306_hash.jpg)
    slug TEXT NOT NULL,                     -- URL-friendly slug (rainbow-over-harbor)
    original_filename TEXT,                 -- Original upload filename

    -- Descriptive metadata (AI-generated or user-edited)
    title TEXT,                             -- "Rainbow Over the Harbor"
    caption TEXT,                           -- Short description
    description TEXT,                       -- Long-form description
    tags TEXT,                              -- Comma-separated: "landscape,sunset,cityscape"
    category TEXT,                          -- "landscape", "portrait", "wildlife", etc.

    -- EXIF metadata (extracted from image file)
    camera_make TEXT,                       -- "Canon"
    camera_model TEXT,                      -- "EOS R5"
    lens TEXT,                              -- "RF 24-70mm f/2.8"
    focal_length TEXT,                      -- "50mm"
    aperture TEXT,                          -- "f/2.8"
    shutter_speed TEXT,                     -- "1/250s"
    iso INTEGER,                            -- 400
    date_taken DATETIME,                    -- When photo was captured
    location TEXT,                          -- "Halifax, Nova Scotia"
    camera TEXT,                            -- Combined camera_make + camera_model

    -- Image properties
    width INTEGER,                          -- 4032
    height INTEGER,                         -- 3024
    aspect_ratio REAL,                      -- 1.333
    file_size INTEGER,                      -- Bytes

    -- Publishing workflow
    published BOOLEAN DEFAULT 0,            -- 0=Private (draft), 1=Public (on website)
    featured BOOLEAN DEFAULT 0,             -- Highlighted for public gallery weighting/curation
    available_for_sale BOOLEAN DEFAULT 0,   -- Future: e-commerce integration
    sort_order INTEGER,                     -- Manual ordering within gallery

    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Publishing States:**
- `published=0` (Private): Image only visible in `/manage/gallery`
- `published=1` (Public): Image appears on `user.hensler.photography` via API
- `featured=1` (Featured): Used to weight/curate public gallery selections (requires published image)

**Filename Convention:**
```
Format: YYYYMMDD_HHMMSS_shortHash.jpg
Example: 20251108_205306_a5ab42bec9b9205a.jpg
         └─ Date   └─ Time └─ Random hash
```

---

#### `ai_costs` - Track Claude API usage

```sql
CREATE TABLE ai_costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,               -- FK to users.id
    operation TEXT NOT NULL,                -- 'analyze_image' or 'generate_tags'
    model TEXT NOT NULL,                    -- 'claude-opus-4-20250514'
    input_tokens INTEGER NOT NULL,          -- Tokens sent to API
    output_tokens INTEGER NOT NULL,         -- Tokens returned from API
    cost_usd REAL NOT NULL,                 -- Calculated cost in USD
    image_path TEXT,                        -- Reference to image file
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Cost Calculation:**
- Input tokens: $15 per 1M tokens
- Output tokens: $75 per 1M tokens
- Typical image analysis: ~$0.02-0.04 per image

**Usage Example:**
```sql
-- Get total costs for a user
SELECT SUM(cost_usd) as total_cost, COUNT(*) as api_calls
FROM ai_costs
WHERE user_id = 1;
```

---

#### `image_events` - Analytics tracking (planned)

```sql
CREATE TABLE image_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER,                       -- FK to images.id (nullable for page views)
    event_type TEXT NOT NULL,               -- 'view', 'click', 'lightbox_open'
    user_agent TEXT,                        -- Browser user agent
    referrer TEXT,                          -- Where visitor came from
    ip_hash TEXT,                           -- SHA256 hash of IP (privacy-preserving)
    session_id TEXT,                        -- Client-generated ephemeral ID
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (image_id) REFERENCES images(id)
);
```

**Privacy Features:**
- IP addresses are hashed (cannot be reversed)
- No cookies or persistent identifiers
- Session IDs are client-generated and temporary

---

## Common Queries

### Get published images for a photographer

```sql
SELECT id, filename, title, caption, tags, category, width, height
FROM images
WHERE user_id = 1 AND published = 1
ORDER BY sort_order ASC, created_at DESC;
```

**Used by:** `/api/gallery/published?user_id=1` (public gallery API)

---

### Get all images for gallery management

```sql
SELECT id, filename, title, caption, tags, category, published, created_at
FROM images
WHERE user_id = 1
ORDER BY created_at DESC
LIMIT 1000;
```

**Used by:** `/manage/gallery` interface

---

### Calculate AI costs for a user

```sql
SELECT
    COUNT(*) as total_calls,
    SUM(input_tokens) as total_input_tokens,
    SUM(output_tokens) as total_output_tokens,
    SUM(cost_usd) as total_cost,
    AVG(cost_usd) as avg_cost_per_image
FROM ai_costs
WHERE user_id = 1 AND operation = 'analyze_image';
```

**Used by:** Future cost analytics dashboard

---

### Get images by tag (album view)

```sql
SELECT id, filename, title, caption, published
FROM images
WHERE user_id = 1
  AND tags LIKE '%landscape%'
  AND published = 1
ORDER BY created_at DESC;
```

**Note:** Current implementation uses comma-separated tags. Future enhancement could normalize to a separate `tags` table with many-to-many relationship.

---

## Database Migrations

**Current Status:** No formal migration system implemented.

**Schema Changes:**
1. Stop API container
2. Manually ALTER TABLE or recreate database
3. Update `api/database.py` schema
4. Restart API container

**Future Enhancement:** Implement Alembic or similar migration tool for version-controlled schema changes.

---

## Backup and Recovery

### Backup Database

```bash
# Export SQLite database
docker compose -p hensler_test exec api python3 -c "
import shutil
shutil.copy('/data/gallery.db', '/data/gallery.db.backup')
"

# Copy to host
docker cp hensler_test-api-1:/data/gallery.db.backup ./gallery_backup_$(date +%Y%m%d).db
```

### Restore Database

```bash
# Stop containers
docker compose -p hensler_test -f docker-compose.local.yml down

# Copy backup to volume
docker volume create hensler_photography_gallery-data
docker run --rm -v hensler_photography_gallery-data:/data -v $(pwd):/backup alpine sh -c "cp /backup/gallery_backup_20251109.db /data/gallery.db"

# Restart
docker compose -p hensler_test -f docker-compose.local.yml up -d
```

---

## Accessing the Database

### Via Python (Inside Container)

```bash
docker compose -p hensler_test exec api python3 -c "
import asyncio
import aiosqlite

async def query():
    async with aiosqlite.connect('/data/gallery.db') as db:
        cursor = await db.execute('SELECT COUNT(*) FROM images')
        count = await cursor.fetchone()
        print(f'Total images: {count[0]}')

asyncio.run(query())
"
```

### Via SQLite CLI (Inside Container)

```bash
# Enter container shell
docker compose -p hensler_test exec api sh

# Open SQLite
sqlite3 /data/gallery.db

# Example queries
.tables
.schema images
SELECT COUNT(*) FROM images WHERE published = 1;
.quit
```

---

## Schema Evolution

### Future Enhancements Planned

**Normalized Tags:**
```sql
CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE image_tags (
    image_id INTEGER,
    tag_id INTEGER,
    PRIMARY KEY (image_id, tag_id),
    FOREIGN KEY (image_id) REFERENCES images(id),
    FOREIGN KEY (tag_id) REFERENCES tags(id)
);
```

**Collections (Albums/Galleries):**
```sql
CREATE TABLE collections (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    description TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE collection_images (
    collection_id INTEGER,
    image_id INTEGER,
    sort_order INTEGER,
    PRIMARY KEY (collection_id, image_id),
    FOREIGN KEY (collection_id) REFERENCES collections(id),
    FOREIGN KEY (image_id) REFERENCES images(id)
);
```

**Print Sizes & Sales:**
```sql
CREATE TABLE print_options (
    id INTEGER PRIMARY KEY,
    image_id INTEGER NOT NULL,
    size TEXT NOT NULL,              -- "8x10", "16x20", etc.
    price_usd REAL NOT NULL,
    stock_available BOOLEAN DEFAULT 1,
    FOREIGN KEY (image_id) REFERENCES images(id)
);
```

---

## Troubleshooting

### Database is locked

```bash
# Check for active connections
docker compose -p hensler_test exec api python3 -c "
import sqlite3
conn = sqlite3.connect('/data/gallery.db')
print('Connected successfully')
conn.close()
"

# If locked, restart API
docker compose -p hensler_test restart api
```

### Schema mismatch errors

```bash
# Check current schema version
docker compose -p hensler_test exec api python3 -c "
import aiosqlite, asyncio
async def check():
    async with aiosqlite.connect('/data/gallery.db') as db:
        cursor = await db.execute('PRAGMA table_info(images)')
        cols = await cursor.fetchall()
        print('Current columns:')
        for col in cols:
            print(f'  {col[1]} ({col[2]})')
asyncio.run(check())
"

# If outdated, recreate database (WARNING: DELETES DATA)
docker compose -p hensler_test -f docker-compose.local.yml down
docker volume rm hensler_photography_gallery-data
docker compose -p hensler_test -f docker-compose.local.yml up -d
```

---

## References

- **Schema Definition:** `/opt/dev/hensler_photography/api/database.py`
- **API Routes:** `/opt/dev/hensler_photography/api/routes/`
- **SQLite Documentation:** https://www.sqlite.org/docs.html
