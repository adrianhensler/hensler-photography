# Deployment Workflow

## Overview

This document provides step-by-step procedures for the complete development-to-production workflow. Follow these checklists to ensure safe, tested deployments.

---

## Environment Overview

### Testing Environment
- **Location**: `/opt/testing/hensler_photography/` (on VPS)
- **Ports**: 8080 (HTTP only, path-based routing)
- **Purpose**: Safe testing alongside production
- **Docker Compose**: `docker-compose.local.yml`
- **Caddyfile**: `Caddyfile.local`
- **Access**:
  - http://localhost:8080/ (main)
  - http://localhost:8080/liam
  - http://localhost:8080/adrian
  - http://localhost:8080/healthz

### Production Environment
- **Location**: `/opt/testing/hensler_photography/` (same location, different compose file)
- **Ports**: 80 (HTTP) and 443 (HTTPS)
- **Purpose**: Live sites with TLS certificates
- **Docker Compose**: `docker-compose.yml`
- **Caddyfile**: `Caddyfile`
- **Access**:
  - https://hensler.photography/
  - https://liam.hensler.photography/
  - https://adrian.hensler.photography/

**Important**: Testing and production run from the same code directory but use different Docker Compose files and Caddyfiles for different port bindings and routing logic.

---

## Development Workflow

### 1. Make Changes

Edit files in `/opt/testing/hensler_photography/`:
- Site content: `sites/[sitename]/`
- Styling: Within `index.html` or separate CSS files
- Configuration: `Caddyfile` or `Caddyfile.local`

### 2. Start Test Server

```bash
cd /opt/testing/hensler_photography
docker compose -f docker-compose.local.yml up -d
```

**Verify it's running:**
```bash
docker compose -f docker-compose.local.yml ps
# Should show container running on port 8080
```

### 3. View Changes

Open in browser:
- http://localhost:8080/ (or http://VPS-IP:8080/)
- Navigate to /liam and /adrian paths

**Use browser DevTools:**
- Inspect responsive design
- Check console for errors
- Test mobile viewports
- Verify network performance

### 4. Iterate

Make additional changes and test:
```bash
# Restart to pick up changes
docker compose -f docker-compose.local.yml restart

# Or stop and start for clean state
docker compose -f docker-compose.local.yml down
docker compose -f docker-compose.local.yml up -d
```

**View logs if issues:**
```bash
docker compose -f docker-compose.local.yml logs web
```

### 5. Run Automated Tests

```bash
# Ensure test server is running on port 8080
npm test

# Or run with UI for debugging
npm run test:ui
```

**Test output:**
- All tests should pass
- Screenshots generated in `screenshots/`
- Review screenshots for visual regressions

### 6. Stop Test Server

```bash
docker compose -f docker-compose.local.yml down
```

---

## Pre-Deployment Checklist

Before deploying to production, verify:

### Code Quality
- [ ] All changes tested on port 8080
- [ ] Playwright tests pass (`npm test`)
- [ ] No console errors in browser
- [ ] Images optimized and loading correctly
- [ ] External links open in new tabs
- [ ] All content reviewed for typos/errors

### Functionality
- [ ] Health check works: http://localhost:8080/healthz
- [ ] All three sites load correctly
- [ ] Navigation works as expected
- [ ] Forms (if any) submit correctly
- [ ] Animations/transitions smooth

### Responsive Design
- [ ] Mobile viewport (375px, 414px)
- [ ] Tablet viewport (768px, 1024px)
- [ ] Desktop viewport (1920px)
- [ ] No horizontal scroll
- [ ] Touch targets at least 44x44px

### Performance
- [ ] Images use appropriate formats (WebP recommended)
- [ ] Large images compressed
- [ ] Lazy loading for below-fold images
- [ ] No unnecessary JavaScript

### Accessibility
- [ ] All images have alt text
- [ ] Keyboard navigation works
- [ ] Focus indicators visible
- [ ] Sufficient color contrast
- [ ] Semantic HTML used

### Version Control
- [ ] Changes committed to git
- [ ] Commit message describes changes
- [ ] Pushed to GitHub
- [ ] Ready to create version tag

---

## Production Deployment

### Method 1: First-Time Production Deployment

If this is the first deployment (or recovering from major issues):

```bash
# Ensure testing environment is stopped
cd /opt/testing/hensler_photography
docker compose -f docker-compose.local.yml down

# Start production
docker compose up -d

# Wait 1-2 minutes for TLS certificates
sleep 120

# Verify health checks
curl -I https://hensler.photography/healthz
curl -I https://liam.hensler.photography/healthz
curl -I https://adrian.hensler.photography/healthz
```

**Expected output:**
```
HTTP/2 200
```

### Method 2: Updating Existing Production

For updating sites after changes (most common):

```bash
# Option A: Graceful restart (no downtime, ~1 second)
cd /opt/testing/hensler_photography
docker compose restart

# Option B: Full restart (short downtime, ~10 seconds)
docker compose down
docker compose up -d
```

**Use graceful restart (Option A) for:**
- Content changes (HTML, CSS, images)
- Minor configuration changes
- Most updates

**Use full restart (Option B) for:**
- Caddyfile changes requiring re-validation
- Major configuration changes
- Troubleshooting issues

### Verify Deployment

```bash
# Check container is running
docker compose ps

# Check logs for errors
docker compose logs --tail=50 web

# Test all sites
curl -I https://hensler.photography/healthz
curl -I https://liam.hensler.photography/healthz
curl -I https://adrian.hensler.photography/healthz

# Open in browser to visually verify
# https://hensler.photography
# https://liam.hensler.photography
# https://adrian.hensler.photography
```

---

## Version Tagging

After successful deployment, create a version tag.

### Semantic Versioning

Follow [semver](https://semver.org):
- **MAJOR** (v2.0.0): Breaking changes, complete redesigns
- **MINOR** (v1.1.0): New features, significant additions
- **PATCH** (v1.0.1): Bug fixes, minor content updates

### Creating a Release

```bash
# Update CHANGELOG.md first with changes

# Create annotated git tag
git tag -a v1.1.0 -m "Add gallery section to Adrian's site"

# Push tag to GitHub
git push origin v1.1.0

# Create GitHub release
gh release create v1.1.0 \
  --title "v1.1.0 - Gallery Section" \
  --notes "Added gallery section to adrian.hensler.photography with 12 featured photos"
```

### View Releases

```bash
# List all tags
git tag -l

# View tag details
git show v1.1.0

# List GitHub releases
gh release list
```

---

## Rollback Procedures

### Rollback Using Git Tags

If new deployment has issues, rollback to previous version:

```bash
# List available versions
git tag -l

# Check out previous version
git checkout v1.0.0

# Restart production with old version
docker compose restart

# Verify old version is working
curl -I https://hensler.photography/healthz

# If rollback successful, document issue
# Then fix issue and re-deploy

# Return to latest code (when ready)
git checkout main
```

### Emergency Rollback to Old Single-Site

If multi-site system has critical issues, revert to old single-site production:

**See REVERT.md for complete instructions.**

Quick version:
```bash
# Stop new production
cd /opt/testing/hensler_photography
docker compose down

# Start old production
cd /opt/liam_site_project
docker compose up -d
```

**Note**: This only works if `/opt/liam_site_project` still exists and has TLS certificates.

---

## Common Operations

### View Logs

```bash
# Real-time logs
docker compose logs -f web

# Last 100 lines
docker compose logs --tail=100 web

# Search logs for errors
docker compose logs web | grep -i error
```

### Check TLS Certificates

```bash
# View certificate info
docker compose exec web caddy trust list

# Check certificate expiry
echo | openssl s_client -servername liam.hensler.photography -connect localhost:443 2>/dev/null | openssl x509 -noout -dates
```

**Caddy automatically renews certificates 30 days before expiry.**

### Update Caddy Image

```bash
# Pull latest Caddy image
docker compose pull

# Restart with new image
docker compose up -d
```

### Manual Backup Before Major Changes

```bash
# Run backup script
cd /opt/testing/hensler_photography
sudo ./scripts/backup.sh

# Verify backup exists
restic -r /opt/backups/hensler_photography snapshots
```

---

## Monitoring and Health Checks

### Health Check Endpoints

All sites have `/healthz` endpoint:
- https://hensler.photography/healthz
- https://liam.hensler.photography/healthz
- https://adrian.hensler.photography/healthz

**Expected response**: HTTP 200 with body "ok"

### Automated Monitoring

Consider setting up external monitoring:
- **UptimeRobot** (free): Check sites every 5 minutes
- **Healthchecks.io**: Monitor cron jobs (backups)
- **CloudFlare**: If using CF, monitor via dashboard

### Manual Checks

```bash
# Quick health check all sites
for site in hensler.photography liam.hensler.photography adrian.hensler.photography; do
  echo "Checking $site..."
  curl -I https://$site/healthz
done
```

---

## Troubleshooting

### Test Server Not Starting

```bash
# Check if port 8080 is already in use
docker compose -f docker-compose.local.yml ps
ss -tlnp | grep 8080

# Stop any existing test container
docker compose -f docker-compose.local.yml down

# Check logs for errors
docker compose -f docker-compose.local.yml logs
```

### Production Site Not Loading

```bash
# Check if container is running
docker compose ps

# Check logs for errors
docker compose logs --tail=100 web

# Check if ports are bound
ss -tlnp | grep -E ':(80|443)'

# Verify Caddyfile syntax
docker compose exec web caddy validate --config /etc/caddy/Caddyfile
```

### TLS Certificate Issues

```bash
# Check certificate status
docker compose logs web | grep -i "certificate"

# Verify DNS points to correct IP
dig hensler.photography +short
dig liam.hensler.photography +short
dig adrian.hensler.photography +short

# Ensure port 443 is accessible externally
# (firewall, security groups, etc.)
sudo ufw status | grep 443
```

### Changes Not Appearing

```bash
# Restart container (picks up volume changes)
docker compose restart

# Clear browser cache and hard refresh
# Chrome/Firefox: Ctrl+Shift+R
# Safari: Cmd+Shift+R
```

---

## Best Practices

### Do's
- ✅ Always test on port 8080 first
- ✅ Run Playwright tests before production deployment
- ✅ Create git tags for versions
- ✅ Use graceful restart for most updates
- ✅ Monitor health check endpoints
- ✅ Document changes in CHANGELOG.md
- ✅ Keep backups before major changes

### Don'ts
- ❌ Don't deploy untested changes directly to production
- ❌ Don't skip version tagging
- ❌ Don't forget to commit changes before deploying
- ❌ Don't make multiple unrelated changes at once
- ❌ Don't ignore test failures
- ❌ Don't forget to check mobile responsiveness

---

## Quick Reference

### Common Commands

```bash
# Start testing
docker compose -f docker-compose.local.yml up -d

# Run tests
npm test

# Deploy to production (graceful restart)
docker compose restart

# Check health
curl -I https://liam.hensler.photography/healthz

# View logs
docker compose logs -f web

# Create release
git tag -a v1.1.0 -m "Description"
git push origin v1.1.0
gh release create v1.1.0

# Rollback to previous version
git checkout v1.0.0
docker compose restart
```

### Port Reference

- **8080**: Testing environment (HTTP only)
- **80**: Production HTTP (redirects to HTTPS)
- **443**: Production HTTPS (main traffic)

### File Reference

- **sites/**: Site content (HTML, CSS, images)
- **Caddyfile**: Production server config
- **Caddyfile.local**: Testing server config
- **docker-compose.yml**: Production compose
- **docker-compose.local.yml**: Testing compose
- **CHANGELOG.md**: Version history
- **BACKUP.md**: Backup procedures
- **REVERT.md**: Emergency rollback
