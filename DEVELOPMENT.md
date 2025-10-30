# Development Guide

## Overview

This guide documents best practices for developing the Hensler Photography websites using Claude CLI. It covers modern web development patterns, iterative design workflows, and critical tool selection.

### Project Roadmap Context

**Current Phase**: Static photography portfolios
- Three domains serving static HTML/CSS/JS
- External links to Instagram/Flickr
- No user data or uploads

**Future Phase**: Image ingestion and storefront
- User-uploaded image management system
- Commerce/storefront capabilities
- **Backups become critical** (user data, transactions, uploaded images)

The development practices in this guide apply to both phases, but security, backups, and data handling become paramount when user data is involved.

### Critical: VPS Development Workflow

**✅ Proper Isolation Implemented (2025-10-14)**

Development and production are now fully isolated in separate directories:

```
/opt/
├── prod/hensler_photography/    # Production (ports 80/443)
│   └── Serves live sites via docker-compose.yml
└── dev/hensler_photography/     # Development (port 8080)
    └── Test server via docker-compose.local.yml
```

**Benefits**:
- True filesystem isolation between test and production
- Changes in `/opt/dev/` do NOT affect `/opt/prod/`
- Safe testing before deployment
- Explicit deployment step via git pull
- Essential for future backend/database development

**Development Workflow**:
```bash
# 1. Work in development directory
cd /opt/dev/hensler_photography

# 2. Make changes and test
# Test server: http://localhost:8080/

# 3. Commit changes
git add .
git commit -m "Description"
git push origin main

# 4. Deploy to production
cd /opt/prod/hensler_photography
git pull origin main
docker compose restart
```

**Migration**: See `MIGRATION_GUIDE.md` for setup instructions.

**Lesson Learned**: Shared filesystem caused production to receive untested changes twice before this isolation was implemented. This is now resolved.

---

## Development Philosophy

### Visual-Driven Development

Claude CLI performs best when given **visual targets** to iterate against. The most effective workflow is:

1. **Build** - Create initial version based on requirements
2. **View** - Test on localhost:8080 and view in browser
3. **Critique** - Provide honest feedback on what works/doesn't work
4. **Refine** - Make specific improvements based on feedback
5. **Repeat** - Continue until design meets goals

**Key Principle:** Don't try to specify everything upfront. Build something viewable quickly, then iterate based on what you see.

### Show, Don't Tell

When requesting design changes:
- ✅ **DO**: Share URLs of sites you like as inspiration
- ✅ **DO**: Take screenshots and annotate what you want changed
- ✅ **DO**: Use the test server to view changes immediately
- ❌ **DON'T**: Try to describe complex visual designs in words alone

---

## Modern Web Design Principles (2025)

### For Photography Portfolios

**Content First:**
- Showcase actual photography, don't just redirect to external platforms
- Include 6-12 hero images in a grid gallery
- Brief bio section (2-3 sentences about your style/approach)
- Clear calls-to-action (contact, social links, portfolio download)

**Design Trends:**
- Micro-interactions (smooth hover effects, transitions)
- Grid-based galleries with lightbox/modal viewing
- Subtle animations on scroll (fade-in, parallax)
- Dark themes with pops of color from photos
- Better typography hierarchy (headlines, subheads, body, captions)
- Intentional white space and breathing room

**Technical Best Practices:**
- Performance optimization (WebP images, lazy loading)
- Accessibility (alt text, ARIA labels, keyboard navigation)
- Responsive design across mobile/tablet/desktop
- Progressive enhancement (works without JS)
- Modern CSS (Grid, Flexbox, CSS Variables, no frameworks)

### What NOT to Do

- Don't create landing pages that only link elsewhere
- Don't use complex frameworks for simple static sites
- Don't sacrifice performance for visual effects
- Don't neglect mobile experience
- Don't use stock photos when you're a photographer

---

## Technology Stack

### Core Technologies

**HTML5**
- Semantic markup (`<main>`, `<article>`, `<figure>`, etc.)
- OpenGraph meta tags for social sharing
- Structured data for SEO (JSON-LD)

**Modern CSS**
- CSS Grid for gallery layouts
- Flexbox for component alignment
- CSS Variables for theming
- `clamp()` for fluid typography
- CSS animations (no heavy JS libraries)
- Media queries for responsive design

**Vanilla JavaScript**
- Lightweight, no frameworks needed
- Use for interactivity (lightbox, smooth scroll, lazy loading)
- Progressive enhancement approach
- Keep bundle size minimal

**Why No Frameworks?**
For static photography portfolios:
- Vanilla HTML/CSS/JS is faster and simpler
- No build step complexity
- Easier to maintain and understand
- Better performance
- Direct control over every element

---

## Tool Selection Guide

### Essential Tools

**1. Claude CLI** ✅
- Core development environment
- Use subagents for specialized tasks (see CLAUDE.md)
- Ideal for iterative visual development

**2. Playwright** ✅ (Already installed)
- Visual regression testing
- Screenshot generation across viewports
- Multi-browser compatibility testing
- Already configured in this project

**3. GitHub CLI (`gh`)** ✅ (Already installed)
- Simple, direct repository management
- Create releases and tags
- Manage issues and PRs
- No complexity overhead

**4. Docker + Caddy** ✅ (Already configured)
- Simple static file serving
- Automatic HTTPS
- Easy local testing
- Production-ready

### MCP Servers: Critical Assessment

**TL;DR: Skip MCP servers for this project.**

MCP (Model Context Protocol) servers are often overhyped. Here's an honest evaluation:

**Potentially Useful (But Not Here):**
- **Figma MCP**: Only valuable if you have Figma designs to convert to code
- **Puppeteer/Playwright MCP**: You already have Playwright locally installed
- **Database MCPs**: Static sites don't need databases

**Not Useful for Static Photography Sites:**
- GitHub MCP (CLI is better, simpler, faster)
- Development environment MCPs (overkill for static sites)
- API connectors (no APIs in static sites)

**When MCP Servers Add Value:**
- Complex integrations with external services
- Real-time data fetching during development
- Working with design tools you use regularly
- Large team workflows with custom tools

**Verdict:** MCP servers add complexity without providing value for simple static portfolios. Stick with direct tools (CLI, local Playwright, browser testing).

---

## Iterative Design Workflow

### Starting a Design Improvement

1. **Current State Analysis**
   - View the current site in browser
   - List what works well
   - Identify specific problems
   - Find 2-3 inspiration sites you like

2. **Planning**
   - Create design notes document
   - Prioritize improvements (high/medium/low impact)
   - Break into small, testable changes
   - Use subagents for specialized critique

3. **Implementation Loop**
   ```
   Make change → Test on :8080 → View in browser → Feedback → Repeat
   ```

4. **Testing**
   - Run Playwright tests: `npm test`
   - Generate screenshots: `npm run screenshot`
   - Test on mobile viewport in browser DevTools
   - Check accessibility with browser tools

5. **Deploy**
   - Follow WORKFLOW.md deployment checklist
   - Create git tag for version
   - Deploy to production
   - Verify with health checks

---

## Using Claude CLI Subagents

Subagents are specialized AI assistants for specific tasks. See `.claude/agents/` for custom agents.

### When to Use Subagents

**Use subagents when:**
- Task requires specialized expertise (design critique, CSS patterns)
- You want isolated context (don't pollute main conversation)
- Task is well-defined and bounded (review this component)
- You need fresh perspective (new agent, new eyes)

**Work directly when:**
- Simple, straightforward changes
- Continuing existing work in current context
- Quick iterations on same component

### Available Custom Agents

**web-design-critic**
- Expert in photography portfolio design
- Analyzes layout, color, typography, UX
- References 2025 web design trends
- Provides actionable improvements

**modern-css-developer**
- Expert in modern CSS/HTML patterns
- No frameworks, vanilla approach
- Performance and accessibility focused
- Implements visual designs with clean code

### How to Invoke

**Explicit invocation:**
```
Use the web-design-critic subagent to review adrian.hensler.photography
```

**Let Claude decide:**
```
Review the design of adrian.hensler.photography and suggest improvements
```
(Claude may automatically delegate to appropriate subagent)

---

## Testing Strategy

### Local Testing (Port 8080)

Always test changes on port 8080 before production:

```bash
# Start test server
cd /opt/dev/hensler_photography
docker compose -p hensler_test -f docker-compose.local.yml up -d

# Access sites
# http://localhost:8080/
# http://localhost:8080/liam
# http://localhost:8080/adrian

# Stop when done
docker compose -p hensler_test -f docker-compose.local.yml down
```

### Automated Testing

Run Playwright tests before every deployment:

```bash
# Run all tests
npm test

# Interactive UI
npm run test:ui

# Generate screenshots
npm run screenshot

# Debug specific test
npx playwright test --debug tests/sites.spec.js
```

### Manual Testing Checklist

- [ ] All pages load correctly
- [ ] Images display properly
- [ ] Links work and open in new tabs
- [ ] Responsive on mobile (use DevTools)
- [ ] Smooth animations/transitions
- [ ] No console errors
- [ ] Accessibility (keyboard navigation, screen reader)

---

## Performance Optimization

### Image Optimization

**Hero Images:**
- Max width: 2000px for high-DPI displays
- Format: WebP with JPEG fallback
- Compression: 80-85% quality is sweet spot
- Lazy loading for below-the-fold images

**Gallery Images:**
- Thumbnails: 400x400px, highly compressed
- Full-size: 1920px wide maximum
- Use `srcset` for responsive images
- Lazy load with `loading="lazy"`

### CSS Optimization

- Use CSS Grid/Flexbox (native, fast)
- Minimize use of shadows/blur (GPU intensive)
- Use `transform` for animations (GPU accelerated)
- Avoid layout thrashing
- Use `will-change` sparingly

### JavaScript Optimization

- Defer non-critical JS
- Use Intersection Observer for scroll effects
- Minimize DOM manipulation
- Use event delegation for lists

---

## Accessibility Guidelines

### Required Elements

- Semantic HTML (`<nav>`, `<main>`, `<footer>`)
- Alt text for all images (descriptive, not generic)
- ARIA labels for interactive elements
- Keyboard navigation support
- Focus indicators (visible outlines)
- Sufficient color contrast (WCAG AA minimum)

### Testing Accessibility

1. **Keyboard Navigation**
   - Tab through entire page
   - All interactive elements reachable
   - Visible focus indicators

2. **Screen Reader**
   - Test with macOS VoiceOver or NVDA
   - All content announced correctly
   - Skip navigation links work

3. **Browser DevTools**
   - Lighthouse accessibility audit
   - Check contrast ratios
   - Verify ARIA labels

---

## Common Pitfalls

### Design Mistakes

- Creating "coming soon" pages instead of real content
- Redirecting to external platforms instead of showcasing work
- Over-complicating simple static sites
- Neglecting mobile experience
- Using too many fonts/colors

### Development Mistakes

- Adding frameworks when vanilla would work
- Not testing on actual devices
- Ignoring performance metrics
- Over-engineering simple features
- Not version controlling changes

### Workflow Mistakes

- Deploying without testing locally first
- Making multiple changes without testing between
- Not using git tags for versions
- Skipping backups before major changes
- Not documenting design decisions

---

## Resources

### Documentation in This Project

- **CLAUDE.md** - Claude CLI guidance and architecture
- **WORKFLOW.md** - Deployment procedures
- **BACKUP.md** - Backup and restore procedures
- **TESTING.md** - Playwright testing guide
- **REVERT.md** - Emergency rollback procedures

### External Resources

- **Claude Code Docs**: https://docs.claude.com/en/docs/claude-code
- **Playwright Docs**: https://playwright.dev
- **Caddy Docs**: https://caddyserver.com/docs
- **MDN Web Docs**: https://developer.mozilla.org (HTML/CSS/JS reference)

### Inspiration

When looking for design inspiration, search for:
- "photography portfolio design 2025"
- "minimalist gallery websites"
- "photographer landing page examples"

Focus on sites that:
- Showcase actual photography prominently
- Use clean, uncluttered layouts
- Load quickly and work on mobile
- Have clear calls-to-action

---

## Site-Specific Documentation

Each site has its own comprehensive maintenance documentation in its directory:

### Adrian's Site

**Location**: `sites/adrian/README.md`

**Complete guide covering**:
- Quick start: Adding/removing gallery images (most common task)
- Current architecture: Ghost typography, slideshow, gallery grid
- Image optimization: WebP, lazy loading, blur-up placeholders
- Error handling: Console debugging, common issues
- Security best practices: Headers, CDN dependencies, image serving
- SEO concepts: Open Graph, Schema.org, sitemaps (future AI implementation)
- Performance monitoring: Plausible Analytics, Core Web Vitals
- Backup strategy: Git + restic approach
- Testing workflow: Pre-deploy checklist, Playwright tests
- File structure: Complete reference

**Key Technical Details**:
- Single-file design: All HTML/CSS/JS in `index.html`
- Dynamic images: `galleryImages` array at line ~418
- Ghost typography: Playfair Display, 300 weight, 0.45 opacity
- Slideshow: Auto-cycles 5s, pauses on hover
- Gallery grid: `object-fit: contain` preserves aspect ratios (critical requirement)
- GLightbox: CDN-hosted library for full-screen viewing
- No frameworks: Pure vanilla HTML/CSS/JS

**When to Use**: Any maintenance work on Adrian's site should reference this documentation first. It's designed to be usable even without Claude CLI access.

### Liam's Site

**Location**: `sites/liam/` (documentation TBD)

Currently simpler Instagram link-based portfolio. If significant features are added, create a similar `sites/liam/README.md`.

### Main Landing Page

**Location**: `sites/main/` (currently "Coming Soon" placeholder)

Future design: Split-image layout with left half → Adrian, right half → Liam. See "Main Landing Page Ideas" section in CLAUDE.md.

## Content Management Workflow

### Adding Images to Adrian's Gallery

**Quick Reference** (see `sites/adrian/README.md` for details):

1. Export image: JPEG, 85-90% quality, 1200-1600px long edge
2. Drop file into `sites/adrian/assets/gallery/`
3. Edit `sites/adrian/index.html` line ~418
4. Add filename to `galleryImages` array
5. Test on port 8080
6. Commit and deploy

**Why It's This Simple**: Both slideshow and gallery populate from a single JavaScript array. No database, no config files, just add the filename to the array.

### Updating Site Content

**For text/bio changes**:
- Edit `sites/[sitename]/index.html` directly
- Find the relevant `<p>` or `<h1>` tag
- Update text content
- Test and deploy

**For design changes**:
- Consider using `web-design-critic` subagent for initial review
- Use `modern-css-developer` subagent for implementation
- Follow iterative workflow: build → view → critique → refine
- Always test on port 8080 before production

### Site-Specific Best Practices

**Adrian's Site**:
- **Critical**: Preserve aspect ratios in gallery (no cropping)
- Always check browser console for errors (F12)
- Test slideshow: Auto-cycle, manual navigation, hover pause
- Verify GLightbox lightbox functionality
- Test responsive breakpoints (3→2→1 columns)

**Error Handling Reminder**:
- Images that fail to load show broken icon (no graceful fallback yet)
- Check console warnings after adding images
- Verify all filenames match exactly (case-sensitive)
- Common issue: Typo in `galleryImages` array

## Next Steps

1. Review current sites and identify improvements needed
2. Consult site-specific documentation (`sites/[sitename]/README.md`)
3. Use subagents for specialized critique/development
4. Iterate using visual-driven workflow
5. Test thoroughly on port 8080
6. Deploy following WORKFLOW.md procedures (or site-specific deployment guide)
7. Create git tag for version tracking
8. Update site documentation if workflow changes
