# Operations Guide

Production website hosting photography portfolios for Adrian Hensler and his son Liam Hensler.

## Sites

- **hensler.photography** — Main family landing page
- **adrian.hensler.photography** — Adrian's portfolio (Flickr)
- **liam.hensler.photography** — Liam's portfolio (Instagram)

## Running Claude CLI at `/opt/prod/` Level

This guide is for **big picture operations** managed via Claude CLI from the parent directory:

### Primary Operations
- **Backups**: Automated restic backups of Docker volumes and TLS certificates
- **Uptime Monitoring**: Health checks across all three domains
- **GitHub Operations**: Version control, releases, pushing changes upstream
- **System Maintenance**: Updates, security patches, log monitoring

### Quick Status Checks

```bash
# Check all sites are responding
curl -I https://hensler.photography/healthz
curl -I https://adrian.hensler.photography/healthz
curl -I https://liam.hensler.photography/healthz

# View production logs
docker compose logs web

# Run backup
npm run backup

# List backup snapshots
npm run backup:list
```

## Production Context

This is production (`/opt/prod/hensler_photography/`). The `THIS_IS_PRODUCTION.TXT` marker exists to prevent accidental changes.

**Development workflow:**
1. All changes happen in `/opt/dev/hensler_photography/` (isolated environment)
2. Test locally on port 8080
3. Run tests: `npm test`
4. Commit and push to GitHub
5. Deploy to production: `cd /opt/prod/hensler_photography && git pull && docker compose restart`
6. Verify with health checks

## GitHub Operations

```bash
# Push changes
git push origin main

# Create version release
git tag -a v1.x.x -m "Description"
git push origin v1.x.x

# View releases
gh release list
```

## System Health

```bash
# Check Docker status
docker compose ps

# View resource usage
docker stats

# Check disk space
df -h

# View system logs
docker compose logs --tail=100
```

## Related Documentation

- **[README.md](README.md)** - Complete project documentation and setup
- **[WORKFLOW.md](WORKFLOW.md)** - Detailed deployment procedures
- **[BACKUP.md](BACKUP.md)** - Backup and restore procedures
- **[CHANGELOG.md](CHANGELOG.md)** - Version history

---

**Family Project**: This website showcases photography work by Adrian and his son Liam, each with their own portfolio subdomain served from a single Caddy container with automated HTTPS.
