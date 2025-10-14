# Directory Isolation Migration Guide

**Date**: 2025-10-14
**Purpose**: Separate test and production environments to prevent accidental production changes

## Current Problem

Test server (port 8080) and production (ports 80/443) both serve from `/opt/testing/hensler_photography/sites/`, causing:
- Git branches don't provide runtime isolation
- Changes to files immediately affect both environments
- Led to accidental production changes twice

## Solution: Separate Directories

### New Directory Structure

```
/opt/
├── prod/
│   └── hensler_photography/          # Production (ports 80/443)
│       ├── sites/
│       ├── Caddyfile
│       ├── docker-compose.yml
│       └── ... (all project files)
│
└── dev/
    └── hensler_photography/           # Development (port 8080)
        ├── sites/
        ├── Caddyfile.local
        ├── docker-compose.local.yml
        └── ... (all project files)
```

## Migration Steps

### 1. Create New Directories

Run these commands as a user with sudo access:

```bash
# Create directories
sudo mkdir -p /opt/prod /opt/dev
sudo chown adrian:adrian /opt/prod /opt/dev

# Copy current state to production (preserves permissions/timestamps)
sudo cp -a /opt/testing/hensler_photography /opt/prod/

# Move testing to dev (rename)
sudo mv /opt/testing/hensler_photography /opt/dev/

# Clean up old /opt/testing directory if now empty
sudo rmdir /opt/testing 2>/dev/null || true
```

### 2. Stop Current Containers

```bash
# Stop production (from old location)
cd /opt/testing/hensler_photography
docker compose down

# Stop test server
docker compose -p hensler_test -f docker-compose.local.yml down
```

### 3. Start from New Locations

```bash
# Start production from /opt/prod/
cd /opt/prod/hensler_photography
docker compose up -d

# Verify production
curl -I https://hensler.photography/healthz
curl -I https://liam.hensler.photography/healthz
curl -I https://adrian.hensler.photography/healthz

# Start test server from /opt/dev/
cd /opt/dev/hensler_photography
docker compose -p hensler_test -f docker-compose.local.yml up -d

# Verify test server
curl -I http://localhost:8080/healthz
```

### 4. Update Git Remote (if needed)

```bash
cd /opt/dev/hensler_photography
git remote -v  # Verify remote is still correct

# If you had absolute paths anywhere, update them
git config --local --list | grep /opt/testing
```

### 5. Verify Isolation

Test that changes in dev don't affect production:

```bash
# Make a test change in dev
cd /opt/dev/hensler_photography
echo "<!-- TEST -->" >> sites/main/index.html

# Check production doesn't have it
curl -s https://hensler.photography/ | grep TEST
# Should return nothing

# Restore dev
git restore sites/main/index.html
```

## Post-Migration Workflow

### Development Work

```bash
# Always work in /opt/dev/
cd /opt/dev/hensler_photography

# Make changes to files
# Test on http://localhost:8080/
# Commit to git when ready
git add .
git commit -m "Description"
git push origin branch-name
```

### Deploying to Production

```bash
# In dev: Ensure changes are committed
cd /opt/dev/hensler_photography
git status  # Should be clean
git push origin main

# In production: Pull changes
cd /opt/prod/hensler_photography
git pull origin main

# Restart production to pick up changes
docker compose restart

# Verify
curl -I https://hensler.photography/healthz
```

## Updated Commands Reference

### Production Server

```bash
# Location: /opt/prod/hensler_photography

# Start
cd /opt/prod/hensler_photography
docker compose up -d

# Stop
docker compose down

# Restart (after updates)
docker compose restart

# View logs
docker compose logs -f web

# Pull latest code
git pull origin main
```

### Test/Development Server

```bash
# Location: /opt/dev/hensler_photography

# Start
cd /opt/dev/hensler_photography
docker compose -p hensler_test -f docker-compose.local.yml up -d

# Stop
docker compose -p hensler_test -f docker-compose.local.yml down

# Access
# http://localhost:8080/
# http://localhost:8080/liam
# http://localhost:8080/adrian
```

## Benefits

- ✅ True isolation: Changes in dev don't affect production
- ✅ Safe testing: Test all changes before production deployment
- ✅ Clear workflow: Explicit deployment step (git pull in prod)
- ✅ Rollback capability: Prod directory is git-controlled
- ✅ Future-ready: Essential for backend development with databases

## Rollback Plan

If migration causes issues:

```bash
# Stop new containers
docker compose -p hensler_test down  # From /opt/dev/
docker compose down                   # From /opt/prod/

# Restore original structure
sudo cp -a /opt/prod/hensler_photography /opt/testing/
cd /opt/testing/hensler_photography
docker compose up -d
docker compose -p hensler_test -f docker-compose.local.yml up -d
```

## Verification Checklist

After migration, verify:

- [ ] Production sites accessible (all 3 domains)
- [ ] HTTPS certificates working
- [ ] Test server accessible on port 8080
- [ ] Changes in /opt/dev/ don't affect /opt/prod/
- [ ] Git remotes configured correctly
- [ ] Docker volumes preserved (TLS certs)
- [ ] Health checks return 200
- [ ] No console errors in browser

## Next Steps

1. Run migration commands above
2. Update CLAUDE.md with new paths
3. Update DEVELOPMENT.md with new workflow
4. Update WORKFLOW.md deployment procedures
5. Test gallery implementation in isolated /opt/dev/
6. Deploy gallery to production when ready

---

**Important**: Once migration is complete, always use `/opt/dev/` for development and only update `/opt/prod/` via explicit deployment steps.
