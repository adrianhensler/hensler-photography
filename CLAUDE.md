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

## Working with Claude CLI

### What is Claude CLI?

Claude CLI (claude.ai/code) is an interactive terminal-based interface for working with Claude AI. It provides:
- Direct filesystem access for reading/editing files
- Git integration for version control
- Command execution capabilities
- Persistent conversation context across sessions
- Specialized subagents for focused tasks

### Why Use Claude CLI for This Project?

**Benefits for web development**:
- **Direct file manipulation**: Edit HTML/CSS/JavaScript without copy-pasting
- **Testing integration**: Run Docker commands, check site status, view logs
- **Git workflow**: Commit, push, pull within the conversation
- **Context awareness**: Claude understands project structure from CLAUDE.md
- **Iterative development**: Make changes → test → refine in tight loop
- **Documentation**: Generate comprehensive docs (like this file)

### Typical Claude CLI Workflow for This Project

**Session Start**:
1. SSH into VPS or work locally
2. Navigate to dev directory: `cd /opt/dev/hensler_photography`
3. Launch Claude CLI: `claude` (or `claude chat`)
4. Claude reads CLAUDE.md automatically and understands project context

**Development Cycle**:
1. **User**: "I want to add new images to Adrian's gallery"
2. **Claude**: Reads sites/adrian/README.md, explains process
3. **User**: Uploads images or provides URLs
4. **Claude**: Downloads images to assets/gallery/, updates galleryImages array in index.html
5. **Claude**: Suggests testing: "Let's start the test server and verify"
6. **User**: Approves
7. **Claude**: Runs `docker compose up` command, provides test URL
8. **User**: Views site at http://localhost:8080/adrian, confirms it works
9. **Claude**: Commits changes with descriptive message
10. **User**: "Deploy to production"
11. **Claude**: Switches to /opt/prod/, pulls changes, restarts container, verifies health

**Complex Tasks (Design Changes)**:
1. **User**: "I want to redesign the header"
2. **Claude**: Invokes `web-design-critic` subagent to analyze current design
3. **Subagent**: Provides critique and 3-4 design options
4. **User**: Selects option 4 (ghost typography)
5. **Claude**: Invokes `modern-css-developer` subagent to implement
6. **Subagent**: Updates CSS, tests responsiveness
7. **Main Claude**: Coordinates testing and deployment

### Commands Claude Can Run

**File Operations**:
- `cat sites/adrian/index.html` - Read files
- `ls sites/adrian/assets/gallery/` - List directory contents
- `nano` / `vim` - Edit files (Claude uses its own editing tools)

**Docker Commands**:
```bash
# Start test container
docker compose -p hensler_test -f docker-compose.local.yml up -d

# Check running containers
docker ps

# View logs
docker compose logs web

# Restart production
cd /opt/prod/hensler_photography && docker compose restart
```

**Git Commands**:
```bash
# Check status
git status

# Add and commit
git add sites/adrian/
git commit -m "Add new gallery images"

# Push to GitHub
git push origin main

# Pull in production
cd /opt/prod/hensler_photography && git pull origin main
```

**Testing Commands**:
```bash
# Run Playwright tests
npm test

# Check site health
curl -I https://adrian.hensler.photography/healthz

# Check site is running
curl https://adrian.hensler.photography/ | head -20
```

### Critical Workflow: Test Before Production

**Established Protocol** (after learning experience):

1. ✅ **Make changes** in `/opt/dev/hensler_photography`
2. ✅ **Deploy to test server** (port 8080)
3. ✅ **Show user the test URL**: "Please review at http://localhost:8080/adrian"
4. ✅ **Wait for explicit approval**: User says "looks good" or "deploy"
5. ✅ **Only then commit and push**: Never skip straight to production
6. ✅ **Deploy to production**: Pull in /opt/prod/ and restart
7. ✅ **Verify production**: Check health endpoints and user confirms

**Why This Matters**:
- User values correctness and security above speed
- User wants to see results before they go live
- Mistakes in production affect real visitors
- Testing catches issues early (broken images, CSS bugs, etc.)

### Context Management

**CLAUDE.md as Source of Truth**:
- Claude reads this file at session start
- Provides project overview, architecture, common commands
- Explains dual dev/prod environment
- Documents security headers, testing procedures

**Site-Specific Documentation**:
- `sites/adrian/README.md` - Comprehensive maintenance guide for Adrian's site
- `sites/liam/README.md` - (Future) Liam's site documentation
- `DEVELOPMENT.md` - Development best practices
- `BACKUP.md` - Backup and recovery procedures

**When Context Grows Large**:
- Claude CLI has token limits (~200k tokens per conversation)
- Use `/compact` command to summarize and continue
- Start new session for unrelated tasks
- Use subagents for focused work (doesn't consume main context)

### Best Practices for Working with Claude CLI

**Be Explicit About Expectations**:
- "Show me the test site before deploying" - Clear instruction
- "I want to see the result BEFORE production" - Sets expectation
- "Correctness is priority, doing things the right way" - Establishes standards

**Provide Feedback**:
- "That worked great" - Positive reinforcement
- "This isn't what I wanted" - Course correction
- "Let's try a different approach" - Alternative path

**Ask Questions**:
- "What are the options here?" - Claude provides multiple approaches
- "What would a designer do?" - Leverage Claude's knowledge
- "Explain how this works" - Understanding before changes

**Verify and Approve**:
- Always check test site before approving deployment
- Open browser DevTools (F12) to check console for errors
- Test on mobile viewport if changes affect responsive design

**Document Learnings**:
- Request documentation updates after complex work
- "Update CLAUDE.md with what we just learned"
- "Create a guide for this in sites/adrian/README.md"

### Error Handling and Debugging with Claude

**When something breaks**:
1. **Claude**: Checks Docker logs: `docker compose logs web`
2. **Claude**: Checks git status for unexpected changes
3. **Claude**: Reads browser console errors (if you share them)
4. **Claude**: Reviews recent file changes
5. **Claude**: Proposes fix and tests before deploying

**Common Issues Claude Can Solve**:
- **Image not loading**: Check filename spelling in galleryImages array
- **CSS not applying**: Check for syntax errors, missing semicolons
- **Docker container won't start**: Check Caddyfile syntax, port conflicts
- **Git conflicts**: Resolve merge conflicts, explain what happened
- **JavaScript errors**: Debug console errors, fix syntax issues

**When Claude Gets Stuck**:
- Provide more context: Share error messages, screenshots
- Break down the problem: "Let's focus on just the slideshow first"
- Try a different approach: "Let's roll back and try option 2"
- Restart conversation: `/compact` to summarize and continue fresh

### Adrian Site Current Architecture (Claude Reference)

**Key Facts for Claude to Remember**:
- **Single file design**: All HTML/CSS/JS in `sites/adrian/index.html`
- **Dynamic image loading**: `galleryImages` array at line ~418
- **Ghost typography**: Playfair Display, 300 weight, 0.45 opacity, lowercase
- **Slideshow**: Auto-cycles 5s, pauses on hover, manual arrows, line 431-488
- **Gallery grid**: Responsive 3→2→1 columns, `object-fit: contain` (no cropping)
- **GLightbox**: CDN-hosted library for full-screen viewing
- **Image count**: Currently 10 images in assets/gallery/
- **No frameworks**: Pure vanilla HTML/CSS/JS, no build process

**When making changes**:
- Preserve aspect ratios in gallery (user requirement: "not negotiable")
- Check browser console for errors (remind user to do this)
- Test slideshow cycling and manual navigation
- Verify responsive breakpoints (mobile, tablet, desktop)
- Ensure fade-in animations still work

### Session Continuity

**Starting a New Session**:
- Claude reads CLAUDE.md automatically
- Previous conversation context is NOT retained (unless using /compact)
- User should provide context: "I'm continuing work on Adrian's gallery"
- Claude will read relevant files to catch up

**Resuming After Compaction**:
- `/compact` creates a summary of conversation
- New session starts with that summary
- Most technical details preserved
- Some conversational nuance lost

**Long-Term Project Memory**:
- Documentation (CLAUDE.md, README.md) serves as project memory
- Git commit messages document what changed and why
- Site-specific READMEs capture architecture decisions
- This allows Claude to help even without conversation history

### Recovery Without Claude CLI

**If you lose access to Claude CLI**, the documentation in this repo should be sufficient to continue:

**Essential Files**:
1. **sites/adrian/README.md** - Complete maintenance guide
2. **CLAUDE.md** - This file, project overview
3. **DEVELOPMENT.md** - Development workflow
4. **BACKUP.md** - Recovery procedures

**Alternative Tools**:
- Any text editor (nano, vim, VSCode) to edit index.html
- Standard git commands for version control
- Docker Compose commands for deployment
- Browser DevTools for debugging

**The documentation is designed to be Claude-independent**: All procedures are documented step-by-step with actual commands. You can follow them manually without AI assistance.

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
