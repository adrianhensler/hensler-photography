# Changelog

All notable changes to the Hensler Photography multi-site portfolio will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added (Sprint 1 - Backend Foundation)
- FastAPI backend application (`api/main.py`)
- SQLite database with multi-tenant schema (`api/database.py`)
- Admin dashboard UI (`/admin` endpoint)
- API endpoints for gallery data and tracking
- Docker containerization for API service
- Caddy reverse proxy integration
- Database seeded with Adrian and Liam as users

### Infrastructure
- `api/` directory structure created
- Docker Compose configuration updated with API service
- Caddyfile.local updated for API routing
- Shared volumes for database and image storage
- Network isolation between web and API containers

### Database Schema
Multi-tenant architecture supporting multiple photographers:
- Users table (photographers with subdomains)
- Images table (metadata, EXIF, tags, categories)
- Image variants table (WebP/AVIF/sizes - future)
- Image events table (click tracking and analytics)
- Products table (e-commerce - future)
- Orders table (sales transactions - future)
- Sessions table (multi-user auth - future)

### Development
- Feature branch workflow established (feature/backend-api)
- v1.1.0 tagged as stable baseline
- Test deployment working on port 8080

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

[Unreleased]: https://github.com/adrianhensler/hensler-photography/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/adrianhensler/hensler-photography/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/adrianhensler/hensler-photography/releases/tag/v1.0.0
