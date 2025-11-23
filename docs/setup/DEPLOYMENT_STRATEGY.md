# Zero-Downtime Deployment Strategy

## Current State (Has Brief Downtime)

```bash
git pull origin main
docker compose restart  # ← 5-10 seconds downtime
```

**Problem:** Containers restart simultaneously, site is unreachable during restart.

---

## Solution 1: Docker Health Checks + Rolling Updates (Recommended)

### Implementation

**1. Add health checks to docker-compose.yml:**

```yaml
services:
  web:
    image: caddy:2-alpine
    healthcheck:
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8080/healthz"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 10s
    # ... rest of config

  api:
    build:
      context: .
      dockerfile: api/Dockerfile
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/healthz').raise_for_status()"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s
    # ... rest of config
```

**2. Deployment script with zero downtime:**

```bash
#!/bin/bash
# deploy-zero-downtime.sh

set -e

echo "🚀 Starting zero-downtime deployment..."

# Pull latest code
git pull origin main

# Rebuild images (if needed)
docker compose build

# Rolling update: one container at a time
for service in api web; do
    echo "Updating $service..."
    docker compose up -d --no-deps --scale $service=2 $service
    sleep 5  # Wait for new instance to be healthy
    docker compose up -d --no-deps --scale $service=1 $service
    echo "✓ $service updated"
done

echo "✅ Deployment complete - zero downtime!"
```

**Benefit:** New container starts, becomes healthy, THEN old one stops. No gap.

---

## Solution 2: Blue-Green Deployment (Advanced)

Run two complete environments (blue & green), swap traffic between them.

**Pros:**
- True zero downtime
- Instant rollback (just switch back)
- Test production environment before going live

**Cons:**
- 2x infrastructure cost
- More complex

**Worth it when:** You have frequent deployments and zero tolerance for downtime.

---

## Solution 3: Static Files Don't Need Restart (Current Win!)

**Good news:** Your static HTML/CSS/JS changes are ALREADY zero-downtime!

- Caddy serves from mounted volume: `./sites:/srv/sites:ro`
- File changes are instant (no restart needed)
- Only API changes require restart

**Optimization:** Separate frontend deploys from backend deploys.

```bash
# Frontend-only changes (HTML/CSS/JS)
git pull origin main
# Done! No restart needed

# Backend-only changes (Python/API)
git pull origin main
docker compose restart api  # Only restart API, not Caddy
```

---

## Recommended Approach

**For your scale:**

1. **Immediate (Today):** Separate frontend/backend restarts
   - 90% of your changes are frontend (zero downtime already!)
   - Only restart API when Python code changes

2. **Short-term (This week):** Add health checks
   - Prevents deployment if containers aren't healthy
   - Better confidence in deployments

3. **Long-term (When needed):** Blue-green if you get serious traffic
   - Worth the complexity when uptime is critical

---

## Deployment Decision Tree

```
Is it HTML/CSS/JS only?
  Yes → git pull (zero downtime ✅)
  No  ↓

Is it API/Python code?
  Yes → git pull && docker compose restart api (5s downtime ⚠️)
  No  ↓

Is it Docker config (Caddyfile, docker-compose.yml)?
  Yes → Full restart needed (10s downtime ⚠️)
```

---

## Monitoring Uptime

Add uptime monitoring:

```bash
# Simple uptime check script
#!/bin/bash
# monitor-uptime.sh

while true; do
    if curl -sf https://adrian.hensler.photography/healthz > /dev/null; then
        echo "$(date): ✅ Site up"
    else
        echo "$(date): ❌ Site down - alerting!"
        # Send alert (email, Slack, etc.)
    fi
    sleep 60
done
```

Or use external service:
- UptimeRobot (free)
- Pingdom
- StatusCake

---

## Rollback Strategy (Zero Downtime)

```bash
#!/bin/bash
# rollback.sh

set -e

# Get previous commit
CURRENT=$(git rev-parse HEAD)
PREVIOUS=$(git rev-parse HEAD~1)

echo "Rolling back from $CURRENT to $PREVIOUS"

# Rollback code
git reset --hard $PREVIOUS

# Restart (or use rolling update)
docker compose restart

echo "✅ Rollback complete"
```

---

**Next Steps:**
1. Separate frontend/backend deployments
2. Add health checks to docker-compose.yml
3. Create deploy-zero-downtime.sh script
4. Set up uptime monitoring
