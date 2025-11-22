# Proper Staging Environment Setup

## Current Problem

Dev environment (`/opt/dev/` on port 8080) is out of sync with production and not usable for testing.

---

## Solution: Mirror Production Exactly

### **Option 1: Fix Existing Dev Environment (Recommended)**

**Goal:** Make `/opt/dev/` an exact clone of `/opt/prod/` that runs on port 8080.

#### Setup Steps:

```bash
# 1. Sync dev with production
cd /opt/dev/hensler_photography
git fetch origin
git reset --hard origin/main  # Match production exactly

# 2. Use separate database
# Dev should have its own database at /opt/dev/data/gallery.db
# Don't share database with production!

# 3. Start dev environment
docker compose -p hensler_test -f docker-compose.local.yml up -d --build

# 4. Verify it matches production
curl https://adrian.hensler.photography:8080/healthz
```

#### Keep Dev in Sync:

```bash
#!/bin/bash
# sync-dev-with-prod.sh

set -e

echo "Syncing dev with production main branch..."

cd /opt/dev/hensler_photography
git fetch origin
git reset --hard origin/main
docker compose -p hensler_test restart

echo "✅ Dev environment synced"
```

**Run this:** After every production deployment to keep dev current.

---

### **Option 2: Docker-Based Staging (Better Isolation)**

Create a true staging environment using Docker that mirrors production exactly.

#### docker-compose.staging.yml:

```yaml
# Identical to docker-compose.yml but with:
# - Different ports (8080 instead of 80/443)
# - Different volume names (staging-caddy-data, staging-gallery-db)
# - Environment variable: ENV=staging

services:
  web:
    image: caddy:2-alpine
    ports:
      - "8080:8080"
      - "4100:4100"
    volumes:
      - ./sites:/srv/sites:ro
      - ./Caddyfile.local:/etc/caddy/Caddyfile:ro
      - staging-caddy-data:/data
      - staging-caddy-config:/config
      - staging-gallery-images:/srv/assets/gallery:ro
    # ... rest identical to production

  api:
    build:
      context: .
      dockerfile: api/Dockerfile
    environment:
      - DATABASE_PATH=/data/staging-gallery.db
      - ENV=staging
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - ./api:/app/api:ro
      - staging-gallery-data:/data
      - staging-gallery-images:/app/assets/gallery
    # ... rest identical to production

volumes:
  staging-caddy-data:
  staging-caddy-config:
  staging-gallery-data:
  staging-gallery-images:

networks:
  staging-network:
```

**Benefits:**
- ✅ Complete isolation from production
- ✅ Can test database migrations safely
- ✅ Identical configuration to production
- ✅ Run staging and production simultaneously

---

### **Option 3: Branch-Based Previews (Most Advanced)**

Deploy every PR to a temporary preview environment automatically.

**How it works:**
1. Open PR #7
2. GitHub Actions automatically deploys to `pr-7.hensler.photography`
3. Test the PR on that URL
4. Merge → preview environment deleted
5. Changes go to production

**Requires:**
- Wildcard DNS (`*.hensler.photography`)
- Dynamic reverse proxy (Traefik or Nginx)
- GitHub Actions workflow

**Worth it when:** You have multiple developers or frequent PRs.

---

## Testing Workflow (With Staging)

### Current (Risky):
```
Change code → Deploy to prod → Hope it works → Fix if broken
```

### Recommended:
```
1. Create feature branch
2. Deploy to staging
3. Test thoroughly on staging
4. Create PR
5. Review & approve
6. Merge to main
7. Deploy to production (with confidence!)
```

---

## Staging Environment Checklist

Your staging should have:

- ✅ Same Docker images as production
- ✅ Same Caddyfile (with port changes)
- ✅ Same Python dependencies
- ✅ Separate database (test data, not production data!)
- ✅ Same environment variables (except API keys can be test keys)
- ✅ Accessible URL (port 8080 or staging subdomain)

---

## Database Strategy

**Production DB:** `/opt/prod/data/gallery.db` (real user data)
**Staging DB:** `/opt/dev/data/staging-gallery.db` (test data)

**Important:** NEVER point staging at production database!

### Sync Production Data to Staging (Optional):

```bash
#!/bin/bash
# sync-prod-db-to-staging.sh

set -e

echo "Copying production database to staging..."

# Stop staging
docker compose -p hensler_test down

# Copy database
cp /opt/prod/data/gallery.db /opt/dev/data/staging-gallery.db

# Restart staging
docker compose -p hensler_test up -d

echo "✅ Staging now has production data (read-only testing)"
```

**Use case:** Testing analytics queries with real data without risking production.

---

## Quick Start: Fix Dev Environment Now

```bash
# 1. Sync dev code with production
cd /opt/dev/hensler_photography
git reset --hard origin/main

# 2. Rebuild containers
docker compose -p hensler_test down
docker compose -p hensler_test up -d --build

# 3. Test it works
curl https://adrian.hensler.photography:8080/
curl https://liam.hensler.photography:8080/

# 4. Create sync script for future
cat > /opt/dev/sync-with-main.sh <<'EOF'
#!/bin/bash
cd /opt/dev/hensler_photography
git fetch origin
git reset --hard origin/main
docker compose -p hensler_test restart
echo "✅ Dev synced with production"
EOF

chmod +x /opt/dev/sync-with-main.sh
```

**Going forward:** Run `/opt/dev/sync-with-main.sh` after every production deployment.

---

## Recommended Approach

**For your current scale:**

1. **This week:** Fix the existing dev environment
   - Make it mirror production exactly
   - Test every change there first
   - Builds confidence before production deploy

2. **Next month:** Consider docker-compose.staging.yml
   - Better isolation
   - More production-like
   - Worth it when you want separate databases

3. **Future:** Branch-based previews
   - When you have multiple developers
   - Or frequent experimental features

---

**Next Steps:**
1. Run the "Quick Start" commands above
2. Test a change in staging before production
3. Create sync script for ongoing maintenance
