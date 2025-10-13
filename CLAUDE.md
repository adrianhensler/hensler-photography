# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-site static photography portfolio deployment using a **single Caddy container** serving three domains:
- `hensler.photography` → sites/main/ (Coming Soon landing page)
- `liam.hensler.photography` → sites/liam/ (Instagram portfolio)
- `adrian.hensler.photography` → sites/adrian/ (Flickr portfolio)

The architecture supports future expansion where the main site will showcase both photographers with links to their individual portfolios.

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

### Testing on VPS (Port 8080)
The testing environment runs on the same VPS as production. Production uses ports 80/443, testing uses port 8080.

```bash
# Start test container (runs alongside production)
cd /opt/testing/hensler_photography
docker compose -f docker-compose.local.yml up -d

# Access from VPS or remotely:
# http://localhost:8080/          (main site)
# http://localhost:8080/liam      (Liam's site)
# http://localhost:8080/adrian    (Adrian's site)
# http://localhost:8080/healthz   (health check)
# Or: http://VPS-IP:8080/liam, etc.

# Stop test container
docker compose -f docker-compose.local.yml down
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
```bash
# Deploy from local to VPS
scp -r /opt/testing/hensler_photography user@VPS:/opt/

# On VPS: Start production (first time)
cd /opt/hensler_photography
docker compose up -d

# Update production sites after changes
scp -r /opt/testing/hensler_photography/sites user@VPS:/opt/hensler_photography/
# On VPS:
docker compose restart

# Check production health
curl -I https://hensler.photography/healthz
curl -I https://liam.hensler.photography/healthz
curl -I https://adrian.hensler.photography/healthz

# View logs
docker compose logs web
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

## Production Marker

`THIS_IS_PRODUCTION.TXT` indicates production code. When copying from `/opt/testing/` to `/opt/` on the VPS, remember this is live infrastructure requiring careful change management and backup considerations.
