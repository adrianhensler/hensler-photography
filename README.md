# Hensler Photography — Multi-site Portfolio

Modern photography portfolio system with API-driven galleries, backend image management, and analytics. Built with Caddy, Docker, FastAPI, and SQLite. Auto-HTTPS via Let's Encrypt.

## Overview

**Public Portfolio Sites** (Port 80/443):
- **hensler.photography** — Main landing page (Coming Soon)
- **liam.hensler.photography** — Liam's portfolio (ready for API integration)
- **adrian.hensler.photography** — Adrian's portfolio (✓ API-driven, 21 published images)

**Backend Management System** (Port 4100):
- Image upload with AI metadata generation (Claude Vision API)
- Gallery management (publish/unpublish, featured images)
- Analytics dashboard (impressions, clicks, views, scroll depth)
- WebP optimization (automatic 400px/800px/1200px variants)
- EXIF extraction and editing
- SQLite database with multi-tenant support

**Performance**: 10-20x faster page loads with WebP variants (5-10s → 0.5-1s on 4G)

---

## 📚 Documentation

Comprehensive guides for development, deployment, and maintenance:

### Core Documentation
- **[CLAUDE.md](CLAUDE.md)** - Complete architecture overview and Claude Code AI guide
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development best practices and workflows
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and technical architecture
- **[DATABASE.md](DATABASE.md)** - Database schema and common queries
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and release notes (current: v2.0.0)

### Operational Guides
- **[WORKFLOW.md](WORKFLOW.md)** - Deployment procedures and checklists
- **[BACKUP.md](BACKUP.md)** - Backup and restore procedures with restic
- **[REVERT.md](REVERT.md)** - Rollback procedures (git, backups, emergency)
- **[TESTING.md](TESTING.md)** - Playwright testing guide

### Design Work
- **[sites/adrian/DESIGN_NOTES.md](sites/adrian/DESIGN_NOTES.md)** - Design improvement roadmap
- **[sites/adrian/README.md](sites/adrian/README.md)** - Adrian's site maintenance guide (33KB comprehensive)
- **[.claude/agents/](/.claude/agents/)** - Custom AI subagents for design critique and development

---

## Quick Start (Development)

### Prerequisites
- Docker and Docker Compose installed
- Git
- Node.js 18+ (for tests)

### Development Environment

Work in `/opt/dev/hensler_photography` (isolated from production):

```bash
cd /opt/dev/hensler_photography

# Start both web and API services on port 8080/4100
npm run dev

# Or use docker compose directly
docker compose -p hensler_test -f docker-compose.local.yml up -d
```

### Access Development Sites

**Public Portfolios** (Port 8080):
- Main: http://localhost:8080/
- Liam: http://localhost:8080/liam
- Adrian: http://localhost:8080/adrian
- Health: http://localhost:8080/healthz

**Management Interface** (Port 4100):
- Login: http://localhost:4100/admin/login
- Dashboard: http://localhost:4100/manage
- Upload: http://localhost:4100/manage/upload
- Gallery: http://localhost:4100/manage/gallery
- Analytics: http://localhost:4100/manage/analytics

Or from remote machine: `http://YOUR-VPS-IP:8080/` and `http://YOUR-VPS-IP:4100/manage`

### Development Credentials

```bash
# Set password for adrian user
docker compose -p hensler_test exec api python -m api.cli set-password adrian
```

### Stop Development Environment

```bash
npm run dev:stop

# Or manually
docker compose -p hensler_test -f docker-compose.local.yml down
```

---

## Convenience Commands (npm scripts)

### Development
```bash
npm run dev              # Start test server (ports 8080/4100)
npm run dev:stop         # Stop test server
npm run dev:logs         # View test server logs
npm run dev:restart      # Restart test server
```

### Backend Commands
```bash
# Initialize database (creates schema + seed data)
docker compose -p hensler_test exec api python -m api.database

# Set user password
docker compose -p hensler_test exec api python -m api.cli set-password adrian

# Check database contents
docker compose -p hensler_test exec api python -c "
from api.database import get_db
conn = get_db().__enter__()
cursor = conn.execute('SELECT id, title, published FROM images WHERE user_id = 1')
for row in cursor.fetchall(): print(dict(row))
"

# View API logs
docker compose -p hensler_test logs api --tail 50

# Restart API only
docker compose -p hensler_test restart api
```

### Testing
```bash
npm test                 # Run all Playwright tests
npm run test:ui          # Interactive test UI
npm run screenshot       # Generate screenshots only
```

### Production
```bash
npm run prod:start       # Start production (ports 80/443/4100)
npm run prod:stop        # Stop production
npm run prod:restart     # Graceful restart (recommended for updates)
npm run prod:logs        # View production logs
```

### Health Checks
```bash
npm run health           # Check all sites (dev + production)
```

### Backups
```bash
npm run backup           # Run manual backup
npm run backup:list      # List available backup snapshots
```

---

## Backend Management System

### Features

**Image Upload** (`/manage/upload`):
- Drag-and-drop or file picker
- Batch upload (max 3 concurrent)
- Automatic AI metadata generation (~$0.02 per image)
- Full EXIF extraction (camera, lens, exposure settings)
- WebP variant generation (400px/800px/1200px, 90-99% size reduction)

**Gallery Management** (`/manage/gallery`):
- View all uploaded images with thumbnails
- Filter by status (published/draft) and featured
- Search by title/caption/tags
- Edit all metadata fields with validation
- Re-extract EXIF from original file (free)
- Regenerate AI metadata on demand
- Publish/unpublish workflow
- Mark images as featured
- Delete images (cascade to variants)

**Analytics Dashboard** (`/manage/analytics`):
- Real-time engagement metrics (views, visitors, clicks, CTR)
- Timeline chart (7/30/90 day trends)
- Top performing images by impressions/clicks/views
- Category performance breakdown
- Scroll depth analysis (25%, 50%, 75%, 100% milestones)
- Average viewing duration
- Privacy-preserving (IP hashed, no PII, anonymous sessions)

### Technology Stack

- **Backend**: Python 3.11+ with FastAPI (async/await)
- **Database**: SQLite at `/data/gallery.db`
- **Authentication**: JWT tokens in httpOnly cookies, bcrypt password hashing
- **AI**: Claude Vision API (Anthropic) for metadata generation
- **Image Processing**: PIL/Pillow for EXIF and WebP conversion
- **Server**: Uvicorn ASGI server

### Database Schema

Multi-tenant architecture:
- `users` - Photographers with subdomains, roles, bio
- `images` - Full metadata, EXIF, AI-generated content, publishing control
- `image_variants` - WebP optimized versions (thumbnail/medium/large)
- `image_events` - Analytics tracking (6 event types, privacy-preserving)
- `ai_costs` - Cost tracking for Claude Vision API calls

See **[DATABASE.md](DATABASE.md)** for complete schema and queries.

---

## Production Deployment

### Directory Structure

- **`/opt/prod/hensler_photography/`** - Production (ports 80/443/4100)
- **`/opt/dev/hensler_photography/`** - Development (ports 8080/4100)

**Critical**: Always make changes in `/opt/dev/`, test, then deploy via git.

### Prerequisites

1. VPS with Ubuntu (or similar) with Docker installed
2. DNS A records pointing to VPS IP:
   - `hensler.photography` → VPS IP
   - `liam.hensler.photography` → VPS IP
   - `adrian.hensler.photography` → VPS IP
3. Ports 80/443/4100 open in firewall

### Initial Production Setup

```bash
# On VPS (first time only)
cd /opt/prod/hensler_photography

# Start services (Caddy + API)
docker compose up -d

# Wait ~1 minute for Let's Encrypt TLS certificates

# Set admin password
docker compose exec api python -m api.cli set-password adrian

# Initialize database (if not already done)
docker compose exec api python -m api.database

# Verify all sites are running
curl -I https://hensler.photography/healthz
curl -I https://liam.hensler.photography/healthz
curl -I https://adrian.hensler.photography/healthz
```

### Standard Deployment Workflow

After making changes in `/opt/dev/hensler_photography`:

```bash
# 1. Test locally on port 8080/4100
cd /opt/dev/hensler_photography
npm run dev
# Browse to http://localhost:8080/adrian and verify changes

# 2. Commit and push changes
git add .
git commit -m "Description of changes"
git push origin main

# 3. Deploy to production
cd /opt/prod/hensler_photography
git pull origin main
docker compose restart  # Graceful restart, preserves TLS certs

# 4. Verify production
curl -I https://adrian.hensler.photography/healthz
```

### Port Configuration

- **Port 80/443**: Public portfolios (web container, auto-HTTPS)
- **Port 8080**: Public portfolios (development only)
- **Port 4100**: Management interface (API container, both environments)

**Security Note**: Port 4100 is currently open for development. Add firewall rules to restrict access in production:

```bash
# Restrict port 4100 to specific IP (optional)
sudo ufw allow from YOUR_IP to any port 4100
```

---

## Architecture

### Two-Tier System

```
┌─────────────────────────────────────────────────────────────┐
│  Public Sites (Port 80/443)                                 │
│  - Static HTML/CSS/JS served by Caddy                       │
│  - adrian.hensler.photography (API-driven gallery)          │
│  - liam.hensler.photography (ready for API)                 │
│  - Dynamic loading via /api/gallery/published               │
│  - Responsive WebP variants (400px/800px/1200px)            │
│  - 10-20x faster with optimized images                      │
└─────────────────────────────────────────────────────────────┘
                         ↕ (FULLY INTEGRATED ✓)
┌─────────────────────────────────────────────────────────────┐
│  Management System (Port 4100) - Python/FastAPI            │
│  - adrian.hensler.photography:4100/manage                   │
│  - JWT authentication with httpOnly cookies                 │
│  - Image upload with drag-and-drop                          │
│  - AI-powered metadata (Claude Vision API)                  │
│  - EXIF extraction and editing                              │
│  - WebP variant generation (400px/800px/1200px)             │
│  - Analytics dashboard with impression tracking             │
│  - SQLite database with multi-photographer support          │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
/opt/prod/hensler_photography/       # Production
├── docker-compose.yml               # Production config (ports 80/443/4100)
├── Caddyfile                        # Production: 3 domains + API proxy
├── sites/
│   ├── main/                        # hensler.photography
│   ├── liam/                        # liam.hensler.photography
│   ├── adrian/                      # adrian.hensler.photography
│   │   ├── index.html               # API-driven gallery
│   │   ├── assets/
│   │   └── README.md                # Comprehensive maintenance guide
│   └── shared/                      # Shared JS/CSS for galleries
├── api/
│   ├── main.py                      # FastAPI application
│   ├── database.py                  # SQLite schema and queries
│   ├── routes/                      # API endpoints
│   ├── templates/                   # Admin UI templates
│   └── assets/gallery/              # Uploaded images + variants
└── README.md                        # This file

/opt/dev/hensler_photography/        # Development (isolated)
├── docker-compose.local.yml         # Dev config (ports 8080/4100)
├── Caddyfile.local                  # Dev: path-based routing
└── (same structure as prod)
```

### Security Features

- **HTTPS**: Auto-HTTPS with Let's Encrypt (production only)
- **HSTS**: Strict Transport Security (force HTTPS)
- **X-Frame-Options**: Clickjacking protection
- **X-Content-Type-Options**: MIME sniffing protection
- **Referrer-Policy**: Privacy protection
- **JWT Authentication**: httpOnly cookies for admin access
- **Password Hashing**: bcrypt with 12 rounds
- **IP Hashing**: SHA256 for analytics (irreversible)
- **Read-only Volumes**: Container security
- **No PII**: Analytics collect no personally identifiable information

---

## Performance Optimizations

Adrian's gallery achieves **10-20x faster loading** through:

### WebP Variant Generation
- **Thumbnail**: 400px width (~10-30KB) for grid display
- **Medium**: 800px width (~30-80KB) for tablets
- **Large**: 1200px width (~40-150KB) for lightbox
- **Original**: Full-resolution preserved for future use

### Responsive Image Loading
- HTML `srcset` attribute for browser-native size selection
- Native lazy loading (`loading="lazy"`) for off-screen images
- Progressive loading: thumbnails → medium → large (never full-res in browser)

### Performance Metrics
- **Gallery grid**: 90-99% smaller images (thumbnails vs originals)
- **Lightbox**: 88-98% smaller images (1200px vs 2-5MB originals)
- **Page load time**: 5-10 seconds → 0.5-1 second on 4G
- **Total bandwidth**: ~100MB → ~5-10MB for 21-image gallery
- **Visual quality**: Maintained (WebP at 85% quality)

### Analytics Tracking

Privacy-preserving engagement metrics:
- **6 Event Types**: page_view, image_impression, gallery_click, lightbox_open, lightbox_close, scroll_depth
- **No Cookies**: Client-generated anonymous session IDs
- **IP Hashing**: SHA256 (irreversible, privacy-safe)
- **No PII**: No personally identifiable information collected
- **IntersectionObserver**: 50% viewport visibility threshold for impressions

---

## Automated Workflows

### GitHub Actions

**Automated Testing** (`.github/workflows/test.yml`):
- Runs on every push and pull request
- Starts test server, runs Playwright tests
- Uploads screenshots and test reports as artifacts
- Blocks merging if tests fail

**Automated Releases** (`.github/workflows/release.yml`):
- Triggers when you push a version tag (e.g., `v2.0.0`)
- Extracts changelog from CHANGELOG.md
- Creates GitHub release with notes
- Makes releases immutable for security

### Version Management

Create releases using semantic versioning (see [CHANGELOG.md](CHANGELOG.md)):

```bash
# 1. Update CHANGELOG.md with changes

# 2. Create and push tag
git tag -a v2.1.0 -m "Description of release"
git push origin v2.1.0

# 3. GitHub Actions automatically creates release

# View releases
gh release list
```

**Current Version**: v2.0.0 (Nov 13, 2025) - API-driven gallery with analytics

---

## Image Management Workflow

### Upload New Images

1. **Login**: http://adrian.hensler.photography:4100/admin/login
2. **Navigate**: Click "Upload Images"
3. **Select**: Drag-and-drop or click to browse
4. **Process**: AI generates metadata (~$0.02 per image)
5. **Edit**: Review and adjust title/caption/tags
6. **Publish**: Toggle "Published" to make visible on public site

### Edit Existing Images

1. **Navigate**: http://adrian.hensler.photography:4100/manage/gallery
2. **Find Image**: Use search or filter by category/status
3. **Edit**: Click pencil icon to modify metadata
4. **Re-extract EXIF**: Free operation if metadata is wrong
5. **Regenerate AI**: ~$0.02 if you want new AI suggestions
6. **Save**: Changes appear immediately on public site

### View Analytics

1. **Navigate**: http://adrian.hensler.photography:4100/manage/analytics
2. **Select Period**: 7/30/90 days
3. **Review Metrics**: Views, visitors, CTR, scroll depth
4. **Top Images**: See which photos perform best
5. **Categories**: Identify popular content types

---

## Backup System

**Status**: Infrastructure documented and ready, **needs implementation**.

### Documentation
- **[BACKUP.md](BACKUP.md)** - Complete setup guide with restic
- **[scripts/backup.sh](scripts/backup.sh)** - Automated backup script
- **[scripts/restore.sh](scripts/restore.sh)** - Recovery procedures

### Critical to Backup
- `/data/gallery.db` - SQLite database (images metadata, users, analytics)
- `api/assets/gallery/` - All uploaded images and WebP variants
- Docker volumes: `caddy-data`, `caddy-config` (TLS certificates)

**Priority**: High - Should be implemented now that user data exists.

---

## Troubleshooting

### Check Container Status
```bash
docker ps
docker compose logs web    # Caddy logs
docker compose logs api    # FastAPI logs
```

### Restart Services
```bash
# Graceful restart (preserves TLS certs)
docker compose restart

# Restart specific service
docker compose restart api
docker compose restart web
```

### Full Rebuild
```bash
# Stop containers
docker compose down

# Rebuild API image
docker compose build api

# Start services
docker compose up -d
```

### Database Issues
```bash
# Check database exists
docker compose exec api ls -l /data/

# Re-initialize database (WARNING: destructive)
docker compose exec api python -m api.database

# Query database directly
docker compose exec api python -c "
from api.database import get_db
conn = get_db().__enter__()
cursor = conn.execute('SELECT COUNT(*) FROM images')
print(f'Total images: {cursor.fetchone()[0]}')
"
```

### API Not Responding
```bash
# Check API is running
curl http://localhost:4100/api/health

# Check logs for errors
docker compose logs api --tail 100

# Restart API
docker compose restart api
```

### TLS Certificate Issues
- Caddy automatically renews certificates 30 days before expiry
- Certificates stored in `caddy-data` Docker volume
- Check renewal: `docker compose logs web | grep -i certificate`

### Performance Issues
```bash
# Check image variant generation
ls -lh api/assets/gallery/ | grep thumbnail

# Verify WebP variants exist for all images
docker compose exec api python -c "
from api.database import get_db
conn = get_db().__enter__()
cursor = conn.execute('SELECT COUNT(*) FROM image_variants')
print(f'Total variants: {cursor.fetchone()[0]}')
"
```

---

## Contributing

### Development Workflow

1. **Work in development**: `/opt/dev/hensler_photography`
2. **Start test server**: `npm run dev` (ports 8080/4100)
3. **Make changes**: Edit code, test locally
4. **Run tests**: `npm test` (Playwright)
5. **Commit**: Clear, descriptive commit messages
6. **Deploy**: Pull in `/opt/prod/` and restart

### Code Style

- **Python**: Follow PEP 8, use async/await throughout
- **JavaScript**: Vanilla JS (no frameworks), modern ES6+
- **HTML/CSS**: Semantic HTML, mobile-first responsive design
- **Documentation**: Update relevant docs when changing features

### Testing

- **Playwright**: Visual testing for all three sites
- **Manual**: Test on port 8080 before deploying to 80/443
- **Cross-browser**: Chrome, Firefox, Safari
- **Responsive**: Mobile, tablet, desktop viewports

---

## License

Private project - All rights reserved.

---

## Current Status (v2.0.0)

### ✅ Complete
- Backend infrastructure (FastAPI, SQLite, Docker)
- Image upload with AI metadata generation
- Gallery management (publish/unpublish, featured)
- Analytics system (6 event types, dashboard)
- WebP optimization (10-20x faster page loads)
- Public gallery API integration (Adrian's site)
- EXIF extraction and editing
- Authentication and authorization
- Performance optimization (90-99% size reduction)

### 🚧 In Progress
- Backup system implementation (documented, not deployed)

### 📋 Planned
- Liam's site API integration (backend ready, frontend pending)
- Main landing page design and implementation
- E-commerce features (print sales, products, orders)
- Advanced search/filtering on public site
- AVIF format support (even smaller than WebP)
- CDN integration (if scaling beyond single server)

See **[ROADMAP.md](ROADMAP.md)** for detailed future plans.

---

## Support

For issues, questions, or contributions, see project documentation:
- **Architecture**: [CLAUDE.md](CLAUDE.md), [ARCHITECTURE.md](ARCHITECTURE.md)
- **Development**: [DEVELOPMENT.md](DEVELOPMENT.md)
- **Deployment**: [WORKFLOW.md](WORKFLOW.md)
- **Database**: [DATABASE.md](DATABASE.md)

**Version**: 2.0.0 (Nov 13, 2025)
