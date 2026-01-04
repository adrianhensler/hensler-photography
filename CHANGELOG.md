# Changelog

All notable changes to the Hensler Photography multi-site portfolio will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

(Empty - next release in progress)

---

## [2.1.0] - 2026-01-04

### Changed
- **Refactored gallery.js**: Reduced file size from 1,309 to 1,282 lines (2.1% reduction)
  - Extracted `buildLightboxDescription()` function to eliminate EXIF builder duplication
  - Extracted `applyFilterCriteria()` function to consolidate filtering logic
  - Extracted `createGalleryItem()` function to eliminate gallery renderer duplication
- **Improved code maintainability**: All future EXIF/filtering changes now happen in single location

### Documentation
- Added public GitHub visibility notice to CLAUDE.md
- Added comprehensive JavaScript code quality standards
- Added gallery.js architecture guide for contributors
- Updated security checklist with XSS prevention guidelines

### Technical
- No functional changes to user-facing features
- All automated tests pass (npm test)
- Backward compatible with existing deployments
- Performance unchanged (load time within 5% margin)

---

## [Unreleased - Before 2.1.0]

### Added
- Main landing page directory hub (hensler.photography) linking to Adrian and Liam portfolios
- Branch protection on main branch requiring PR reviews
- Pre-commit hooks for automated code quality checks (trailing whitespace, YAML/JSON validation, Python formatting)
- README.md validation report documenting accuracy checks
- Custom Claude Code agents (web-design-critic, modern-css-developer, expert-code-reviewer, product-marketing-critic)

### Changed
- Made repository public on GitHub for transparency and collaboration
- Reorganized documentation into docs/ structure (planning/, guides/, setup/, reviews/)
- Cleaned up root directory from 15 to 9 markdown files
- Updated README.md deployment workflow to reflect PR-based process
- Fixed GitHub Actions documentation to accurately reflect test status
- Updated version management documentation for automated releases

### Fixed
- Critical flake8 code quality issues (32 warnings resolved)
- Indentation errors in analytics.py
- Missing subdomain filtering in analytics queries
- User model missing subdomain and bio attributes
- CI package-lock.json tracking for reproducible builds

### Security
- Repository audit completed (no secrets or credentials exposed)
- Branch protection prevents direct pushes to main
- All changes now require PR review

---

## [2.0.0] - 2025-11-13

**BREAKING CHANGE**: Architecture migration from static Flickr-linked portfolio to fully API-driven gallery system with backend image management.

### Added - Backend Infrastructure
- FastAPI backend application (`api/main.py`) with async/await throughout
- SQLite database with multi-tenant schema (`api/database.py`)
- JWT authentication with httpOnly cookies
- bcrypt password hashing (12 rounds)
- Role-based access control (admin, photographer)
- Docker containerization for API service (port 4100)
- Caddy reverse proxy integration for API endpoints
- Database seeded with Adrian and Liam as users
- Uvicorn ASGI server for production deployment

### Added - Image Management System
- Admin upload interface with drag-and-drop (`/manage/upload`)
- Gallery management dashboard (`/manage/gallery`)
- Image metadata editor with validation (title, caption, tags, category)
- EXIF extraction from uploaded images (camera, lens, exposure settings)
- Technical field validation (ISO, aperture, shutter speed, focal length)
- Publish/unpublish workflow for image visibility control
- Featured image selection for hero sections
- Image deletion with cascade to variants
- Re-extract EXIF functionality (free operation)
- Regenerate AI metadata on demand (~$0.02 per image)

### Added - AI Integration
- Claude Vision API integration for automatic metadata generation
- Cost tracking for all AI operations (`ai_costs` table)
- Automatic title, caption, tags, and category generation
- Token usage logging (input/output tokens)
- Average cost: ~$0.015-0.03 per image upload

### Added - WebP Image Optimization
- Automatic WebP variant generation on upload:
  - Thumbnail: 400px width (~10-30KB) for grid display
  - Medium: 800px width (~30-80KB) for tablets
  - Large: 1200px width (~40-150KB) for lightbox
- PIL/Pillow image processing pipeline
- `image_variants` table for tracking all generated sizes
- 90-99% file size reduction vs originals
- Cascade deletion when parent image is removed

### Added - Public Gallery API Integration
- `/api/gallery/published` endpoint for public image data
- Returns URLs for all WebP variants (thumbnail, medium, large, original)
- Optional EXIF data sharing via `share_exif` parameter
- Responsive image loading with HTML srcset/sizes attributes
- Native lazy loading (loading="lazy" attribute)
- Dynamic gallery loading on page load (replaces hardcoded images)
- Browser-native image format selection

### Added - Analytics System
- Privacy-preserving event tracking (`image_events` table)
- 6 event types tracked:
  - `page_view` - Site visit (site-level)
  - `image_impression` - Image 50% visible in viewport (IntersectionObserver)
  - `gallery_click` - Thumbnail clicked
  - `lightbox_open` - Full-screen view opened
  - `lightbox_close` - Full-screen closed (includes viewing duration)
  - `scroll_depth` - Scroll milestones (25%, 50%, 75%, 100%)
- IP address hashing (SHA256) for privacy
- Anonymous session IDs (no cookies, client-generated)
- User agent and referrer tracking
- JSON metadata field for event-specific data (duration, depth percentage)

### Added - Analytics Dashboard
- Real-time engagement metrics (`/manage/analytics`)
- Overview statistics: total views, unique visitors, clicks, CTR
- Timeline chart (7/30/90 day views)
- Top performing images by:
  - Impressions (viewport visibility)
  - Clicks (thumbnail interactions)
  - Views (lightbox opens)
- Category performance breakdown
- Scroll depth analysis (milestone completion rates)
- Average viewing duration per image
- Referrer traffic sources
- Expandable "About Analytics" section with metric explanations

### Changed - Architecture
- **BREAKING**: Migrated from static Flickr image links to API-driven gallery
- Adrian's site now loads images dynamically from `/api/gallery/published?user_id=1`
- Gallery grid uses thumbnail variants (400px WebP, ~10-30KB each)
- Slideshow uses large variants (1200px WebP, ~40-150KB each)
- Lightbox uses large variants instead of full-resolution originals
- Image URLs now served from `https://adrian.hensler.photography:4100/assets/gallery/`
- Updated `sites/adrian/index.html` to fetch and render API data
- Removed hardcoded `galleryImages` array

### Changed - Database Schema
- Updated `image_variants` table: changed from "future" to fully implemented
- Updated `image_events` table: added `metadata` column for JSON data
- Updated validation: TrackingEvent model now accepts 6 event types (was 3)
- Added indexes for performance on frequently queried columns

### Performance - Achieved Improvements
- **Gallery grid**: 90-99% smaller images (thumbnails vs 2-5MB originals)
- **Lightbox**: 88-98% smaller images (1200px vs full-resolution)
- **Page load time**: 5-10 seconds → 0.5-1 second on 4G connection
- **Total bandwidth**: ~100MB → ~5-10MB for 21-image gallery
- **10-20x faster** overall page performance
- Maintained visual quality (WebP at 85% quality)
- Native lazy loading reduces initial payload
- Browser-native format selection (no JavaScript required)

### Infrastructure
- `api/` directory structure with modular organization
- Docker Compose configuration with `api` service (ports 4100:8000)
- `Caddyfile.local` updated for API routing at port 4100
- Shared volumes:
  - `/data` for SQLite database persistence
  - `/app/assets/gallery` for image storage
- Network isolation between web and API containers
- Environment variables for configuration (DATABASE_PATH, ANTHROPIC_API_KEY, JWT_SECRET_KEY)

### Database Schema
Multi-tenant architecture supporting multiple photographers:
- `users` table: photographers with subdomains, roles, bio
- `images` table: metadata, EXIF, AI-generated content, publishing control
- `image_variants` table: WebP/AVIF optimized versions (FULLY IMPLEMENTED)
- `image_events` table: analytics tracking with privacy features (FULLY IMPLEMENTED)
- `ai_costs` table: cost tracking for Claude Vision API calls
- `products` table: e-commerce support (future)
- `orders` table: sales transactions (future)
- `sessions` table: multi-user auth (future)

### Development
- Test deployment isolated at port 8080 (`/opt/dev/hensler_photography`)
- Production deployment at ports 80/443 (`/opt/prod/hensler_photography`)
- API development workflow: test → commit → deploy
- Database initialization via `python -m api.database`
- API logs accessible via `docker compose logs api`
- Health check endpoints for monitoring

### Documentation
- Updated CLAUDE.md with accurate production state (155 lines changed)
- Documented all completed features (analytics, WebP optimization, API integration)
- Added performance metrics and achievements
- Removed outdated "NOT YET CONNECTED" and "future" markers
- Added comprehensive API endpoint documentation
- Documented analytics event types and privacy features
- Updated "Adrian Site Current Architecture" section

### Security
- JWT tokens in httpOnly cookies (not accessible to JavaScript)
- bcrypt password hashing with 12 rounds
- IP address hashing for analytics (SHA256, irreversible)
- No PII collected in analytics
- Anonymous session tracking
- CORS configuration for API endpoints
- Environment variable secrets (not in git)

### Testing
- Manual testing on port 8080 before production deployment
- Browser DevTools verification (Network tab for WebP loading)
- Analytics event verification (console logging)
- Image upload and variant generation testing
- EXIF extraction testing with various image formats
- Responsive design testing (mobile, tablet, desktop)

### Notes
- Original high-resolution images preserved for future use
- AVIF format support deferred (WebP provides sufficient optimization)
- Blur-up placeholder technique deferred (lazy loading sufficient)
- E-commerce features (products, orders) deferred to future release
- CDN integration deferred (single server sufficient for current scale)

---

## [1.1.0] - 2025-11-01

### Added
- IntersectionObserver-based gallery reveal animation for Adrian's site
- Performance attributes for gallery images: `decoding="async"` and `fetchpriority="low"`
- Accessibility support: respects `prefers-reduced-motion` user preference
- Image preload for first slideshow image
- Comprehensive development documentation (DEVELOPMENT.md)
- Deployment workflow documentation (WORKFLOW.md)
- Backup system documentation and scripts (BACKUP.md, scripts/backup.sh, scripts/restore.sh)
- GitHub Actions for automated testing (.github/workflows/test.yml)
- GitHub Actions for release management (.github/workflows/release.yml)
- Custom Claude CLI subagents for web design and development (.claude/agents/)
- Version tagging and release procedures (CHANGELOG.md)
- Design improvement roadmap for Adrian's site (sites/adrian/DESIGN_NOTES.md)
- npm convenience scripts for development, testing, production, and backup operations

### Changed
- Adrian's gallery: replaced hardcoded nth-child animations with scroll-triggered reveals
- Adrian's gallery: all 10 images now animate on reveal (previously only first 4)
- Adrian's gallery: reduced animation translateY from 20px to 8px for more subtle effect
- Adrian's gallery: images reveal 120px before entering viewport for smoother experience
- Expanded CLAUDE.md with subagent guidance and development workflow
- Enhanced REVERT.md with git-based rollback procedures
- Updated README.md with comprehensive documentation links and npm scripts
- Improved .gitignore for backup files and logs

### Performance
- First slideshow image preloaded for faster Largest Contentful Paint (LCP)
- Gallery images now load asynchronously without blocking main thread
- Slideshow images prioritized over gallery images for faster initial paint
- Modern IntersectionObserver API improves scroll performance
- Font display optimization already in place (display=swap) for immediate text rendering

### Notes
- Backup system is fully documented but not yet implemented (planned before image ingestion/storefront features)
- Cloudflare integration deferred to future release

---

## [1.0.0] - 2025-10-13

### Added
- Initial multi-site architecture with single Caddy container
- Three domains: hensler.photography, liam.hensler.photography, adrian.hensler.photography
- Dual configuration system (production and local testing)
- Production deployment on ports 80/443 with auto-HTTPS via Let's Encrypt
- Local testing environment on port 8080 with path-based routing
- Playwright test suite for automated visual testing
- Security headers (HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy)
- Health check endpoints for all sites
- Docker Compose configurations for both environments
- Comprehensive documentation (README.md, CLAUDE.md, TESTING.md, REVERT.md)
- Private GitHub repository with initial commit
- Emergency rollback procedures to legacy single-site setup

### Sites Created
- **hensler.photography**: Family landing page (Coming Soon placeholder)
- **liam.hensler.photography**: Liam's portfolio with Instagram link
- **adrian.hensler.photography**: Adrian's portfolio with Flickr link

### Infrastructure
- Caddy 2 Alpine for web server
- Docker Compose for orchestration
- Let's Encrypt TLS certificates (automatic renewal)
- Named Docker volumes for persistent data (caddy-data, caddy-config)
- Read-only volume mounts for security

### Testing
- Playwright test suite covering all three sites
- Multi-browser testing (Chromium, Firefox, WebKit)
- Responsive design testing (mobile, tablet, desktop)
- Automated screenshot generation

---

## Version Guidelines

### Version Format

Following [Semantic Versioning](https://semver.org):

```
MAJOR.MINOR.PATCH

Example: 1.2.3
```

- **MAJOR** version (X.0.0): Incompatible changes, complete redesigns
- **MINOR** version (0.X.0): New features, significant additions (backward compatible)
- **PATCH** version (0.0.X): Bug fixes, minor content updates (backward compatible)

### When to Increment

**MAJOR (v2.0.0, v3.0.0)**
- Complete site redesign
- Changing architecture (e.g., adding backend, switching frameworks)
- Breaking changes to URLs or structure
- Major infrastructure changes

**MINOR (v1.1.0, v1.2.0)**
- Adding new site features (gallery, contact form, blog)
- Adding new domain/site to multi-site setup
- Significant content additions
- New integrations or functionality

**PATCH (v1.0.1, v1.0.2)**
- Fixing bugs or broken links
- Updating images or content
- Minor CSS/styling tweaks
- Security patches
- Dependency updates

### Example Versioning

```
v1.0.0 - Initial deployment
v1.0.1 - Fix broken link on Adrian's site
v1.1.0 - Add gallery section to Adrian's site
v1.2.0 - Add contact form to main site
v2.0.0 - Complete redesign with new layout
```

---

## How to Update This Changelog

### Adding Changes

As you work, add entries under `[Unreleased]` section:

```markdown
## [Unreleased]

### Added
- New gallery section on Adrian's site with 12 featured photos
- Lightbox modal for full-screen image viewing

### Changed
- Updated hero image on Liam's site
- Improved mobile responsiveness for all sites

### Fixed
- Fixed broken Flickr link on Adrian's site
- Corrected copyright year in footer
```

### Creating a Release

When ready to deploy, move unreleased changes to a new version:

1. **Update CHANGELOG.md**:
   ```markdown
   ## [1.1.0] - 2025-10-15

   ### Added
   - New gallery section on Adrian's site with 12 featured photos
   - Lightbox modal for full-screen image viewing

   ### Changed
   - Updated hero image on Liam's site
   - Improved mobile responsiveness for all sites

   ### Fixed
   - Fixed broken Flickr link on Adrian's site
   - Corrected copyright year in footer
   ```

2. **Commit changes**:
   ```bash
   git add CHANGELOG.md
   git commit -m "Update CHANGELOG for v1.1.0"
   ```

3. **Create git tag**:
   ```bash
   git tag -a v1.1.0 -m "Add gallery section and mobile improvements"
   git push origin v1.1.0
   ```

4. **Create GitHub release**:
   ```bash
   gh release create v1.1.0 \
     --title "v1.1.0 - Gallery Section & Mobile Improvements" \
     --notes-file <(sed -n '/## \[1.1.0\]/,/## \[/p' CHANGELOG.md | head -n -1)
   ```

---

## Categories

Use these standard categories in changelog entries:

### Added
For new features, pages, or functionality.

Examples:
- Added gallery section to Adrian's site
- Added contact form to main landing page
- Added social media links to footer

### Changed
For changes to existing functionality.

Examples:
- Updated hero image on Liam's site
- Improved mobile navigation menu
- Changed color scheme for better contrast

### Deprecated
For features that will be removed in future versions.

Examples:
- Deprecated old contact form (use new form instead)
- Deprecated /old-gallery path (redirects to /gallery)

### Removed
For removed features or files.

Examples:
- Removed placeholder "Coming Soon" page
- Removed unused CSS files
- Removed deprecated contact form

### Fixed
For bug fixes.

Examples:
- Fixed broken external links
- Fixed mobile menu not closing on iOS
- Fixed image loading issue on slow connections

### Security
For security-related changes.

Examples:
- Updated security headers configuration
- Added CSP (Content Security Policy) headers
- Fixed XSS vulnerability in form validation

---

## Links

- [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
- [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)

---

[Unreleased]: https://github.com/adrianhensler/hensler-photography/compare/v2.0.0...HEAD
[2.0.0]: https://github.com/adrianhensler/hensler-photography/compare/v1.1.0...v2.0.0
[1.1.0]: https://github.com/adrianhensler/hensler-photography/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/adrianhensler/hensler-photography/releases/tag/v1.0.0
