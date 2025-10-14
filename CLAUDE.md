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

### Directory Structure (Post-Migration)
Development and production are now properly isolated:

```
/opt/
├── prod/hensler_photography/    # Production (ports 80/443)
└── dev/hensler_photography/     # Development (port 8080)
```

**See MIGRATION_GUIDE.md for setup instructions.**

### Testing on VPS (Port 8080)
The testing environment runs in `/opt/dev/hensler_photography` and is fully isolated from production.

```bash
# Start test container
cd /opt/dev/hensler_photography
docker compose -p hensler_test -f docker-compose.local.yml up -d

# Access from VPS or remotely:
# http://localhost:8080/          (main site)
# http://localhost:8080/liam      (Liam's site)
# http://localhost:8080/adrian    (Adrian's site)
# http://localhost:8080/healthz   (health check)
# Or: http://VPS-IP:8080/liam, etc.

# Stop test container
docker compose -p hensler_test -f docker-compose.local.yml down
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
# All work happens on VPS in /opt/dev/
cd /opt/dev/hensler_photography

# Make changes, test on port 8080, commit to git
git add .
git commit -m "Description"
git push origin main

# Deploy to production: Pull changes in prod directory
cd /opt/prod/hensler_photography
git pull origin main
docker compose restart

# Check production health
curl -I https://hensler.photography/healthz
curl -I https://liam.hensler.photography/healthz
curl -I https://adrian.hensler.photography/healthz

# View logs
docker compose logs web

# Start production (first time only)
cd /opt/prod/hensler_photography
docker compose up -d
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

## Using Claude CLI Subagents

### What Are Subagents?

Subagents are specialized AI assistants with their own context windows, custom system prompts, and specific tool access. They enable focused, expert-level work on specialized tasks without polluting the main conversation context.

### When to Use Subagents

**Use subagents for:**
- Complex, specialized tasks requiring domain expertise
- Tasks that benefit from isolated context (design review, code audit)
- Reusable workflows (same agent for same task type)
- Preserving main conversation context for coordination

**Work directly in main agent for:**
- Simple, quick changes
- Continuing work already in progress
- Tasks requiring full project context
- Coordination across multiple tasks

### Best Practices

1. **Early Delegation**: Use subagents early in conversations to verify details or investigate questions without consuming main context
2. **Single-Purpose Agents**: Create focused agents for specific tasks, not general-purpose helpers
3. **Detailed System Prompts**: Write comprehensive instructions in agent configuration
4. **Tool Limitation**: Only grant necessary tools to each agent type
5. **Version Control**: Keep project agents in `.claude/agents/` and commit to git

### Custom Agents in This Project

This project includes specialized agents for web development:

**web-design-critic** (`.claude/agents/web-design-critic.md`)
- Expert in photography portfolio design
- Analyzes UX, visual hierarchy, modern design trends
- Provides actionable improvement suggestions
- Use for: Design reviews, layout critique, inspiration gathering

**modern-css-developer** (`.claude/agents/modern-css-developer.md`)
- Expert in vanilla HTML/CSS/JavaScript
- No frameworks, performance-focused approach
- Accessibility and responsive design specialist
- Use for: Implementing designs, CSS architecture, animations

### How to Invoke Subagents

**Explicit invocation:**
```
Use the web-design-critic subagent to analyze adrian.hensler.photography
```

**Automatic delegation** (Claude decides):
```
Please review the design of adrian.hensler.photography
```

### Subagent Workflow Example

```
Main Agent: "I need to improve adrian.hensler.photography"
  ↓
Subagent (web-design-critic): Analyzes site, provides critique
  ↓
Main Agent: Reviews critique, plans implementation
  ↓
Subagent (modern-css-developer): Implements design improvements
  ↓
Main Agent: Tests changes, coordinates deployment
```

## Development Workflow

For detailed development best practices, see **DEVELOPMENT.md**.

Key workflow:
1. Make changes in `/opt/dev/hensler_photography`
2. Test locally on port 8080
3. Run Playwright tests: `npm test`
4. Commit and push to git
5. Deploy: `cd /opt/prod/hensler_photography && git pull && docker compose restart`
6. Verify production health checks
7. Create git tag for version (see **CHANGELOG.md**)

**Critical**: Production (`/opt/prod/`) and development (`/opt/dev/`) are now fully isolated. Changes in dev do NOT affect production until explicitly deployed.

## Backup and Recovery

For backup procedures, see **BACKUP.md**.

Automated daily backups via restic:
- Docker volumes (caddy-data, caddy-config)
- TLS certificates preserved
- 7-day retention policy
- Restore procedures documented

## Production Marker

Production code lives in `/opt/prod/hensler_photography/`. Development work happens in `/opt/dev/hensler_photography/`. These are fully isolated directories with separate git working trees.

**Never edit files in `/opt/prod/` directly.** Always make changes in `/opt/dev/`, test, commit, and deploy via git pull.
