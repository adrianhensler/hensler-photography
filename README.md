# Hensler Photography — Multi-site Portfolio
Static photography portfolio sites with Caddy + Docker. Auto-HTTPS via Let's Encrypt.

## Sites
- **hensler.photography** — Main landing page (Coming Soon)
- **liam.hensler.photography** — Liam's portfolio (Instagram)
- **adrian.hensler.photography** — Adrian's portfolio (Flickr)

All three sites are served from a single Caddy container on standard ports (80/443).

---

## 📚 Documentation

Comprehensive guides for development, deployment, and maintenance:

- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Web development best practices, tools, and workflows
- **[WORKFLOW.md](WORKFLOW.md)** - Complete deployment procedures and checklists
- **[BACKUP.md](BACKUP.md)** - Backup and restore procedures with restic
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and release notes
- **[CLAUDE.md](CLAUDE.md)** - Guide for Claude Code AI assistant (architecture, subagents)
- **[REVERT.md](REVERT.md)** - Rollback procedures (git, backups, emergency revert)
- **[TESTING.md](TESTING.md)** - Playwright testing guide

### For Design Work
- **[sites/adrian/DESIGN_NOTES.md](sites/adrian/DESIGN_NOTES.md)** - Design improvement roadmap for Adrian's site
- **[.claude/agents/](/.claude/agents/)** - Custom AI subagents for design critique and development

---

## Local Testing

Test all sites on port 8080 before deploying to production. This setup runs on the same VPS as production (which uses ports 80/443), allowing you to test changes safely without affecting live sites.

### Quick Start
```bash
cd /opt/testing/hensler_photography

# Option 1: Using npm scripts (recommended)
npm run dev

# Option 2: Direct docker compose
docker compose -f docker-compose.local.yml up -d
```

### Convenience Commands

New npm scripts for common tasks:

```bash
# Development
npm run dev              # Start test server on port 8080
npm run dev:stop         # Stop test server
npm run dev:logs         # View test server logs

# Testing
npm test                 # Run all Playwright tests
npm run test:ui          # Interactive test UI
npm run screenshot       # Generate screenshots only

# Production
npm run prod:start       # Start production (ports 80/443)
npm run prod:stop        # Stop production
npm run prod:restart     # Graceful restart (recommended for updates)
npm run prod:logs        # View production logs

# Health checks
npm run health           # Check all sites (test + production)

# Backups
npm run backup           # Run manual backup
npm run backup:list      # List available backup snapshots
```

### Access Test Sites
- Main site: http://localhost:8080/
- Liam's site: http://localhost:8080/liam
- Adrian's site: http://localhost:8080/adrian
- Health check: http://localhost:8080/healthz

Or from your local machine:
- http://YOUR-VPS-IP:8080/
- http://YOUR-VPS-IP:8080/liam
- http://YOUR-VPS-IP:8080/adrian

### Stop Testing Container
```bash
docker compose -f docker-compose.local.yml down
```

### Benefits
- Runs alongside production on same VPS (different ports)
- Same code as production
- No DNS/hosts file changes needed
- Fast iteration for design changes
- Test all sites simultaneously

---

## Production Deployment

### Prerequisites
1. VPS with Ubuntu (or similar)
2. Docker installed
3. DNS A records pointing to VPS IP:
   - `hensler.photography` → VPS IP
   - `liam.hensler.photography` → VPS IP
   - `adrian.hensler.photography` → VPS IP
4. Ports 80/443 open in firewall

### Deploy Steps

1. **Copy to VPS** (e.g., `/opt/hensler_photography`):
```bash
# On local machine
scp -r /opt/testing/hensler_photography user@VPS:/opt/
```

2. **On VPS** (first time setup):
```bash
# Install Docker (if needed)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && newgrp docker

# Configure firewall
sudo ufw allow 80,443/tcp
sudo ufw enable

# Start services
cd /opt/hensler_photography
docker compose up -d
```

3. **Wait for TLS** (~1 minute for Let's Encrypt):
```bash
# Check all sites
curl -I https://hensler.photography/healthz
curl -I https://liam.hensler.photography/healthz
curl -I https://adrian.hensler.photography/healthz
```

### Update Production Sites

After making changes in `/opt/testing/hensler_photography`:

```bash
# Local: test changes first
docker compose -f docker-compose.local.yml up

# Local: copy to production
scp -r /opt/testing/hensler_photography/sites user@VPS:/opt/hensler_photography/

# VPS: restart (graceful, preserves TLS certs)
cd /opt/hensler_photography
docker compose restart
```

---

## Customization

### Replace Hero Images
- **Liam's image**: `sites/liam/assets/liam-hero.jpg`
- **Adrian's image**: `sites/adrian/assets/adrian-hero.jpg` (PLACEHOLDER - needs replacement)

### Update Links
- **Liam's Instagram**: Edit `sites/liam/index.html` line 27
- **Adrian's Flickr**: Edit `sites/adrian/index.html` line 27

### Customize Main Site
Edit `sites/main/index.html` to create the family landing page linking to both photographers.

---

## Architecture

### Directory Structure
```
hensler_photography/
├── docker-compose.yml          # Production config
├── docker-compose.local.yml    # Local testing config
├── Caddyfile                   # Production: 3 domains
├── Caddyfile.local             # Local: path-based routing
├── THIS_IS_PRODUCTION.TXT      # Production marker
├── README.md
└── sites/
    ├── main/                   # hensler.photography
    ├── liam/                   # liam.hensler.photography
    └── adrian/                 # adrian.hensler.photography
```

### Security Features
- Strict Transport Security (HSTS)
- X-Frame-Options (clickjacking protection)
- X-Content-Type-Options (MIME sniffing protection)
- Referrer-Policy (privacy)
- Read-only volume mounts
- Auto-HTTPS with Let's Encrypt

---

## Automated Workflows

### GitHub Actions

**Automated Testing** (`.github/workflows/test.yml`)
- Runs on every push and pull request
- Starts test server, runs Playwright tests
- Uploads screenshots and test reports as artifacts
- Blocks merging if tests fail

**Automated Releases** (`.github/workflows/release.yml`)
- Triggers when you push a version tag (e.g., `v1.1.0`)
- Extracts changelog from CHANGELOG.md
- Creates GitHub release with notes
- Makes releases immutable for security

### Version Management

Create releases using semantic versioning:

```bash
# 1. Update CHANGELOG.md with changes

# 2. Create and push tag
git tag -a v1.1.0 -m "Add gallery section to Adrian's site"
git push origin v1.1.0

# 3. GitHub Actions automatically creates release

# View releases
gh release list
```

See [CHANGELOG.md](CHANGELOG.md) for versioning guidelines.

---

## Backup System (Future)

Backup infrastructure is documented and ready to implement when needed:
- **Documentation**: Complete setup guide in [BACKUP.md](BACKUP.md)
- **Scripts**: Automated backup/restore scripts in `scripts/`
- **When to implement**: Before adding image ingestion and storefront features

All backup procedures are ready to go - this will become critical when handling user-uploaded images and transaction data.

---

## Next Steps

### Immediate Priority
- [ ] Design and implement gallery section for Adrian's site (see sites/adrian/DESIGN_NOTES.md)
- [ ] Design and implement the main landing page at hensler.photography

### Future Plans
- [ ] Image ingestion system (user uploads/management)
- [ ] Storefront features (commerce integration)
- [ ] **Then implement backups** (critical for user data)
- [ ] Add Cloudflare proxy (optional performance/security enhancement)

---

## Troubleshooting

### Check container logs
```bash
docker compose logs web
```

### Restart without downtime
```bash
docker compose restart
```

### Full rebuild (preserves TLS certs in volumes)
```bash
docker compose down
docker compose up -d
```

### TLS certificate renewal
Caddy automatically renews certificates 30 days before expiry. No action needed.
