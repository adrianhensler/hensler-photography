# Adrian Hensler Photography - Site Documentation

**Last Updated**: 2025-10-30
**Live Site**: https://adrian.hensler.photography/
**Design Philosophy**: "Invisible design" - high-end minimalism where typography whispers and photography dominates.

---

## Table of Contents

1. [Quick Start: Managing Images](#quick-start-managing-images)
2. [Project Overview](#project-overview)
3. [Current Architecture](#current-architecture)
4. [Image Optimization & Best Practices](#image-optimization--best-practices)
5. [Error Handling & Debugging](#error-handling--debugging)
6. [Security Best Practices](#security-best-practices)
7. [SEO Concepts (Future Implementation)](#seo-concepts-future-implementation)
8. [Performance Monitoring](#performance-monitoring)
9. [Backup Strategy](#backup-strategy)
10. [Testing Workflow](#testing-workflow)
11. [File Structure](#file-structure)

---

## Quick Start: Managing Images

**This is the most common maintenance task - adding or removing gallery images.**

### Adding Images

1. **Export your image** from Lightroom or your editing tool:
   - Format: JPEG
   - Quality: 85-90%
   - Size: 1200-1600px on the long edge
   - File size target: Under 500KB per image

2. **Drop the image file** into `sites/adrian/assets/gallery/`
   - Filenames can be anything (we keep Flickr's long names like `53617286790_597f1818c5_b.jpg`)
   - Avoid spaces and special characters in filenames
   - Use lowercase and hyphens/underscores if needed

3. **Edit index.html** around **line 418** and add the filename to the `galleryImages` array:

```javascript
const galleryImages = [
  '52871221196_95f87f72ce_b.jpg',
  '53225347053_31cd2f818e_b.jpg',
  '53470724843_5747fc8ff5_b.jpg',
  'YOUR_NEW_IMAGE.jpg',  // <-- Add here
  '53615968247_4d4ecff67c_b.jpg',
  // ... rest of images
];
```

4. **That's it!** Both the slideshow and gallery grid populate from this single array.

### Removing Images

1. **Delete the image file** from `sites/adrian/assets/gallery/`
2. **Remove the filename** from the `galleryImages` array in `index.html`
3. **Done!**

### Image Order

The order of filenames in the `galleryImages` array determines:
- The slideshow cycling order
- The gallery grid display order (left-to-right, top-to-bottom)

Rearrange array entries to change order.

---

## Project Overview

Adrian Hensler Photography is a single-page portfolio showcasing photography from Halifax and surrounding areas. The site features:

- **Ghost Typography Header**: Large, low-opacity typography that fades into the background, letting photography dominate
- **Auto-Cycling Slideshow**: Full-size image carousel that cycles every 5 seconds
- **Static Gallery Grid**: Responsive grid of thumbnails with lightbox viewing
- **Minimal, High-End Design**: 2025 "invisible design" aesthetic

### Key Components

1. **Header**: Lowercase "adrian hensler" / "photography" in Playfair Display at 45% opacity
2. **Bio**: Short description and contact email
3. **Slideshow**: Full-width carousel with manual navigation arrows
4. **Gallery Grid**: 3-column responsive grid (3→2→1 on smaller screens)
5. **External Link**: Button to full Flickr portfolio

### Technology Stack

- **Pure HTML/CSS/JavaScript**: No frameworks, no build process
- **Fonts**: Google Fonts (Playfair Display for headings, Inter for body text)
- **Lightbox**: GLightbox library (CDN-hosted) for full-screen image viewing
- **Image Loading**: Dynamic JavaScript population from filename array
- **Responsive**: CSS Grid with mobile-first breakpoints

---

## Current Architecture

### Ghost Typography

The header uses a "ghost effect" design pattern popular in 2025 minimalist design:

```css
h1 {
  font-family: 'Playfair Display', Georgia, serif;
  font-weight: 300;              /* Light weight */
  font-size: clamp(56px, 8vw, 80px);  /* Responsive 56-80px */
  letter-spacing: 0.05em;        /* Loose spacing */
  opacity: 0.45;                 /* Ghost effect */
  text-transform: lowercase;     /* Modern aesthetic */
  line-height: 1.0;
}
```

**Design Intent**: Typography whispers rather than shouts, fading into the background to let photography be the star. The large scale creates visual interest without demanding attention.

### Slideshow Carousel

Located at **index.html lines 431-488** (JavaScript) and **lines 79-153** (CSS).

**How It Works**:

1. **Initialization**: `initSlideshow()` runs on page load, dynamically creating slide divs from the `galleryImages` array
2. **Auto-Cycling**: `setInterval` advances to the next slide every 5000ms (5 seconds)
3. **Pause on Hover**: Event listeners pause auto-cycling when user hovers over slideshow
4. **Manual Navigation**: Arrow buttons call `changeSlide(-1)` or `changeSlide(1)` and reset the timer
5. **Smooth Transitions**: CSS opacity transitions (1s ease-in-out) for fade effects

**Key CSS**:
```css
.slideshow-container {
  height: 600px;  /* Desktop */
  /* 400px on tablet, 300px on mobile */
}

.slideshow-slide {
  position: absolute;
  opacity: 0;
  transition: opacity 1s ease-in-out;
}

.slideshow-slide.active {
  opacity: 1;
  z-index: 2;
}
```

**Image Loading Strategy**:
- First image: `loading="eager"` (loads immediately)
- Subsequent images: `loading="lazy"` (loads as needed)

### Gallery Grid

Located at **index.html lines 490-526** (JavaScript) and **lines 155-225** (CSS).

**Critical Design Decision**: Preserve original aspect ratios, NO CROPPING.

```css
.gallery-item {
  /* NO aspect-ratio property */
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.gallery-item img {
  width: 100%;
  height: auto;              /* Preserves aspect ratio */
  object-fit: contain;       /* No cropping */
}
```

**Why This Matters**: Photography portfolios must show images as the photographer intended. Cropping to fit a grid destroys composition. The grid allows varied heights to accommodate landscape and portrait orientations.

**GLightbox Integration**:
- Each gallery item is an `<a>` tag with `class="glightbox"`
- GLightbox initializes after gallery populates (100ms delay)
- Provides full-screen viewing, touch gestures, keyboard navigation, and image zoom

**Responsive Breakpoints**:
```css
/* Desktop: 3 columns */
.gallery-grid { grid-template-columns: repeat(3, 1fr); }

/* Tablet (≤768px): 2 columns */
@media (max-width: 768px) {
  .gallery-grid { grid-template-columns: repeat(2, 1fr); }
}

/* Mobile (≤480px): 1 column */
@media (max-width: 480px) {
  .gallery-grid { grid-template-columns: 1fr; }
}
```

---

## Image Optimization & Best Practices

### Current Image Format: JPEG

All gallery images are currently high-quality JPEGs exported from Flickr or Lightroom.

**Recommended Export Settings**:
- Format: JPEG
- Quality: 85-90% (balances quality vs file size)
- Long edge: 1200-1600px
- Color space: sRGB (for web)
- Metadata: Strip EXIF data for privacy (or keep for copyright)

**Current File Sizes**: 200-400KB per image (acceptable but could be optimized)

### Future Optimization: WebP Format

**Note**: Not currently implemented. Consider for Phase 2 optimization.

**What is WebP?**
- Modern image format developed by Google
- Achieves 25-35% smaller file sizes than JPEG at equivalent visual quality
- Supports transparency (like PNG) and animation (like GIF)
- Supported by all modern browsers (Chrome, Firefox, Safari, Edge)

**Benefits**:
- **Faster page loads**: Smaller files = less bandwidth = quicker loading
- **Better user experience**: Especially on mobile/slow connections
- **SEO boost**: Page speed is a Google ranking factor
- **Cost savings**: Less bandwidth usage for hosting

**How to Implement** (future):
```html
<picture>
  <source srcset="image.webp" type="image/webp">
  <img src="image.jpg" alt="Fallback for old browsers">
</picture>
```

Browsers that support WebP load the WebP version; older browsers fall back to JPEG.

**Conversion Tools**:
- `cwebp` command-line tool (Google's official converter)
- Squoosh.app (web-based GUI)
- ImageMagick: `convert input.jpg -quality 85 output.webp`

### Blur-Up Placeholder Loading

**Note**: Not currently implemented. Consider for future enhancement.

**What is Blur-Up?**

A progressive loading technique that provides instant visual feedback while images load:

1. **Tiny thumbnail** (20-30px wide, ~2-3KB) is embedded directly in HTML or loaded immediately
2. **Blurred version** is displayed scaled up to full size (blurry but recognizable)
3. **Full image** loads in the background
4. **Smooth fade transition** from blurred to sharp when full image is ready

**User Experience Benefit**:
- No harsh "pop" of images suddenly appearing
- Content is visible instantly (even if blurry)
- Perception of speed: "Something is happening right away"
- Similar to what Medium.com, Pinterest, and Instagram use

**Implementation Approach** (future):
```html
<div style="background: url('tiny-blurred.jpg'); background-size: cover;">
  <img src="full-image.jpg" onload="this.style.opacity=1">
</div>
```

CSS handles the fade-in transition from placeholder to full image.

### Image Naming Conventions

**Current Practice**: Keep Flickr's original filenames (e.g., `53617286790_597f1818c5_b.jpg`)

**Benefits**:
- Unique identifiers (Flickr IDs prevent collisions)
- Traceable back to Flickr source
- No manual renaming needed

**Avoid**:
- Spaces in filenames (use hyphens or underscores instead)
- Special characters: `&`, `?`, `#`, `%`, etc.
- Excessively long names (though Flickr's ~30 chars is fine)

### Lazy Loading

**Status**: Currently implemented via `loading="lazy"` attribute on images.

**How It Works**: Browser delays loading images until they're about to enter the viewport (user scrolls near them). Saves bandwidth and speeds up initial page load.

**Current Implementation**:
- Slideshow: First image `loading="eager"`, rest `loading="lazy"`
- Gallery: All images `loading="lazy"`

---

## Error Handling & Debugging

### Current Error Handling Status

**As of October 2025**: Minimal error handling implemented. If an image file is missing or the filename is misspelled, the browser will show a broken image icon (📷 with a crack). The slideshow will still cycle but display a broken image for that slide.

### Debugging Images

**When images don't appear, follow these steps**:

1. **Open Browser DevTools**: Press `F12` (Chrome/Firefox) or `Cmd+Option+I` (Mac)

2. **Check the Console tab** for errors:
   ```
   GET https://adrian.hensler.photography/assets/gallery/typo.jpg 404 (Not Found)
   ```
   This tells you the filename is wrong or the file doesn't exist.

3. **Check the Network tab**:
   - Filter by "Img" to see all image requests
   - Red entries = failed to load
   - Click on a failed request to see details

4. **Common Issues**:
   - **Typo in filename**: Check `galleryImages` array spelling matches actual file
   - **File not uploaded**: Verify file exists in `assets/gallery/` directory
   - **Case sensitivity**: Linux servers are case-sensitive (`Photo.jpg` ≠ `photo.jpg`)
   - **Path issues**: Images must be in `assets/gallery/`, not root or elsewhere

### Console Warnings (Recommended Practice)

**When testing changes**, always check the browser console. Look for:

- **JavaScript errors**: Syntax errors, undefined variables, function failures
- **404 errors**: Missing images or resources
- **CORS errors**: Cross-origin resource loading issues (shouldn't happen with same-origin images)
- **GLightbox errors**: Lightbox library initialization issues

**Good Practice**: After adding images, do a full page refresh (Cmd+Shift+R / Ctrl+Shift+F5) and check console for any red errors.

### Recommended Future Improvements

**Add error handling to image loading**:

```javascript
// In initSlideshow() and initGallery()
img.onerror = () => {
  console.warn(`Failed to load image: ${filename}`);
  // Option 1: Show placeholder image
  img.src = '/assets/placeholder.jpg';
  // Option 2: Skip this image in slideshow rotation
  // Option 3: Display error message to user
};
```

**Add initialization logging**:

```javascript
// At end of initSlideshow()
console.log(`Slideshow initialized with ${galleryImages.length} images`);

// At end of initGallery()
console.log(`Gallery initialized with ${galleryImages.length} images`);
```

This helps verify everything loaded correctly.

---

## Security Best Practices

### Current Security Measures

**Caddy Security Headers** (configured in `Caddyfile` and `Caddyfile.local`):

```
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
```

**What These Do**:

1. **Strict-Transport-Security (HSTS)**: Forces browsers to only access the site via HTTPS, never HTTP. Protects against SSL-stripping attacks. `max-age=31536000` = 1 year.

2. **X-Frame-Options: DENY**: Prevents the site from being embedded in an `<iframe>` on other domains. Protects against clickjacking attacks where malicious sites overlay your content with invisible buttons.

3. **X-Content-Type-Options: nosniff**: Prevents browsers from MIME-sniffing (guessing file types). Forces strict content-type handling. Prevents security vulnerabilities where browsers might execute a JPEG as JavaScript.

4. **Referrer-Policy**: Controls what referrer information is sent when users click external links. `strict-origin-when-cross-origin` sends only the origin (not full URL) to external sites, protecting user privacy.

### Image Security

**Current Practice**:
- All images served from same-origin (`/assets/gallery/`)
- No user-generated content (all images manually added by you)
- No XSS risk from filenames (JavaScript array is hardcoded by developer, not user input)
- No direct file uploads or dynamic file serving

**Why This Is Safe**:
- No attack surface for file upload vulnerabilities
- No path traversal risks (no user input in file paths)
- No ability for attackers to inject malicious images

### External Dependencies

**GLightbox** (loaded from jsdelivr CDN):
```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/glightbox/dist/css/glightbox.min.css">
<script src="https://cdn.jsdelivr.net/npm/glightbox/dist/js/glightbox.min.js"></script>
```

**Current Risk**: Using `npm/glightbox` without version pinning means you get the latest version. If the library is compromised, your site could load malicious code.

**Recommended Improvement** (future):

1. **Pin specific version**:
   ```html
   <script src="https://cdn.jsdelivr.net/npm/glightbox@3.2.0/dist/js/glightbox.min.js"></script>
   ```

2. **Add Subresource Integrity (SRI) hash**:
   ```html
   <script src="https://cdn.jsdelivr.net/npm/glightbox@3.2.0/dist/js/glightbox.min.js"
           integrity="sha384-HASH_HERE"
           crossorigin="anonymous"></script>
   ```

   Generate SRI hash at: https://www.srihash.org/

3. **Self-host GLightbox** (eliminates CDN dependency):
   - Download glightbox.min.js and glightbox.min.css
   - Place in `assets/` directory
   - Update script/link tags to point to local files

### Future Security Enhancements

**Content Security Policy (CSP)** header:

Restrict what resources the page can load (scripts, styles, images, fonts). Example:

```
Content-Security-Policy: default-src 'self'; img-src 'self'; script-src 'self' https://cdn.jsdelivr.net; style-src 'self' https://fonts.googleapis.com https://cdn.jsdelivr.net; font-src https://fonts.gstatic.com;
```

This would prevent any unauthorized scripts from running, even if an attacker found an XSS vulnerability.

**HTTPS Only**: Already enforced by Caddy's automatic Let's Encrypt TLS certificates and HSTS header.

### Regular Maintenance

- **Keep dependencies updated**: Check for GLightbox updates periodically
- **Monitor security advisories**: Subscribe to GitHub security alerts if self-hosting
- **Review Caddy updates**: Update Caddy Docker image occasionally for security patches
- **Check browser console**: Look for mixed content warnings or CSP violations

---

## SEO Concepts (Future Implementation)

**Note**: These are future enhancements. You plan to create AI tooling/scripts using OpenAI API or similar to auto-generate SEO metadata.

### Open Graph Tags

**What They Are**: Meta tags in the HTML `<head>` that control how your site appears when shared on social media (Facebook, Twitter, LinkedIn, Discord, Slack, etc.).

**Current Implementation** (index.html lines 367-371):
```html
<meta property="og:title" content="Adrian Hensler Photography">
<meta property="og:description" content="View my work on Flickr.">
<meta property="og:image" content="/assets/adrian-hero.jpg">
<meta property="og:type" content="website">
```

**What Happens**: When someone pastes `https://adrian.hensler.photography/` into Facebook or Twitter, the platform fetches these tags and displays a "rich preview card" with your title, description, and hero image.

**"Enhance with Gallery Images" Means**:

Option 1: **Rotate OG image** - Dynamically set `og:image` to different gallery images on each page load, so social shares show variety

Option 2: **Composite preview** - Create a multi-image preview (e.g., 2x2 grid of your top 4 photos) as the OG image

Option 3: **Use first slideshow image** - Set `og:image` to the first image in your gallery array

**Testing**: Use https://www.opengraph.xyz/ or Facebook's Sharing Debugger to preview how your site appears in social shares.

### Schema.org Structured Data

**What It Is**: Machine-readable JSON-LD code embedded in HTML that tells search engines semantic information about your content. Think of it as "explaining your page to a robot."

**Why It Matters**: Google, Bing, and other search engines use Schema.org markup to generate "rich snippets" in search results:
- Star ratings
- Event dates and locations
- Person information boxes
- Image carousels
- Breadcrumbs

**Relevant Schemas for a Photographer**:

1. **Person** (about you):
```json
{
  "@context": "https://schema.org",
  "@type": "Person",
  "name": "Adrian Hensler",
  "jobTitle": "Photographer",
  "address": {
    "@type": "PostalAddress",
    "addressLocality": "Halifax",
    "addressRegion": "NS",
    "addressCountry": "CA"
  },
  "url": "https://adrian.hensler.photography",
  "sameAs": [
    "https://www.flickr.com/photos/adrianhensler/"
  ]
}
```

2. **ImageGallery** (your collection):
```json
{
  "@context": "https://schema.org",
  "@type": "ImageGallery",
  "name": "Adrian Hensler Photography Gallery",
  "description": "Images from Halifax and surrounding areas. Light, land, and life.",
  "url": "https://adrian.hensler.photography"
}
```

3. **Photograph** (individual images):
```json
{
  "@context": "https://schema.org",
  "@type": "Photograph",
  "name": "Halifax Harbour Sunset",
  "creator": {
    "@type": "Person",
    "name": "Adrian Hensler"
  },
  "datePublished": "2024-10-15",
  "description": "Golden hour over Halifax Harbour",
  "contentUrl": "https://adrian.hensler.photography/assets/gallery/52871221196_95f87f72ce_b.jpg"
}
```

**How It Appears in HTML**:
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Person",
  "name": "Adrian Hensler",
  ...
}
</script>
```

**AI Tooling Plan**: Feed your gallery images to GPT-4 Vision or Claude Vision, have it analyze each photo and generate:
- Descriptive titles
- Alt text
- Keywords/tags
- Location data (if EXIF present)
- Subject matter

Then output Schema.org JSON-LD for each image.

### Sitemap.xml

**What It Is**: An XML file (usually at `https://domain.com/sitemap.xml`) listing all pages and resources on your site with metadata.

**Why It Matters**:
- Search engine crawlers fetch sitemaps to efficiently discover and index content
- Tells search engines when pages were last updated and how often they change
- For image-heavy sites, helps Google Images index your photos

**Example Sitemap for Adrian's Site**:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">
  <url>
    <loc>https://adrian.hensler.photography/</loc>
    <lastmod>2025-10-30</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>

    <image:image>
      <image:loc>https://adrian.hensler.photography/assets/gallery/52871221196_95f87f72ce_b.jpg</image:loc>
      <image:caption>Photography by Adrian Hensler</image:caption>
    </image:image>

    <image:image>
      <image:loc>https://adrian.hensler.photography/assets/gallery/53225347053_31cd2f818e_b.jpg</image:loc>
      <image:caption>Photography by Adrian Hensler</image:caption>
    </image:image>

    <!-- ... repeat for all 10 gallery images -->
  </url>
</urlset>
```

**Where to Put It**: Root of your site (`/sitemap.xml`)

**How to Generate**:
- Manually (simple for single-page site)
- Script (read gallery array, output XML)
- Online tools (xml-sitemaps.com)

**Tell Search Engines About It**: Add to `robots.txt`:
```
User-agent: *
Allow: /

Sitemap: https://adrian.hensler.photography/sitemap.xml
```

**For Multi-Page Sites**: Critical for SEO. For single-page sites like yours: Still helpful for image indexing.

---

## Performance Monitoring

### Plausible Analytics (Recommended)

**What It Is**: Privacy-friendly, GDPR-compliant web analytics.

**Why Use It Instead of Google Analytics**:
- No cookies required
- No personal data collection
- Respects "Do Not Track" browser settings
- GDPR/CCPA compliant out of the box
- Lightweight script (~1KB vs Google's ~45KB)
- Simple, clean dashboard

**How It Works**:
1. Sign up at plausible.io (cloud-hosted, $9/month) or self-host
2. Add one-line script tag to `<head>`:
   ```html
   <script defer data-domain="adrian.hensler.photography" src="https://plausible.io/js/script.js"></script>
   ```
3. View dashboard: Real-time visitors, page views, referrers, devices, countries

**What You Can Track**:
- Page views and unique visitors
- Referral sources (where visitors come from)
- Device types (mobile vs desktop vs tablet)
- Browser and OS stats
- Geographic location (country/city level, no IP tracking)

**Custom Events** (future):
- Track lightbox opens: Which images get most engagement?
- Track slideshow arrow clicks: Do users navigate manually?
- Track external link clicks: How many go to Flickr?

### Core Web Vitals

**What They Are**: Google's page experience metrics that affect SEO ranking.

**Three Key Metrics**:

1. **Largest Contentful Paint (LCP)**: How long until the largest image/text block is visible
   - Target: < 2.5 seconds
   - Your site: Likely 1-2s (first slideshow image is LCP)

2. **First Input Delay (FID)**: How quickly the page responds to first user interaction
   - Target: < 100ms
   - Your site: Should be excellent (minimal JavaScript)

3. **Cumulative Layout Shift (CLS)**: How much content jumps around while loading
   - Target: < 0.1
   - Your site: Potential issue if images load and shift grid layout
   - Fix: Reserve space with `min-height` or aspect-ratio (already done)

**How to Monitor**:
- Google Search Console (free, shows real user data)
- PageSpeed Insights: https://pagespeed.web.dev/
- Lighthouse in Chrome DevTools (F12 → Lighthouse tab)

**Recommended**: Run Lighthouse audit quarterly, address any issues.

---

## Backup Strategy

### Current Backup: GitHub

**Status**: ✅ Sufficient for this use case

Your site content (HTML, CSS, JavaScript, images) is fully backed up via Git and GitHub:

- **Full version history**: Every commit is saved, can rollback to any point
- **Remote backup**: GitHub's servers (multiple data centers, redundant)
- **Easy recovery**: Clone repo on new server, you're live in minutes
- **Branching**: Test changes in branches before merging to main

**What Git Backs Up**:
- All source code (`index.html`, `Caddyfile`, `docker-compose.yml`)
- All gallery images in `sites/adrian/assets/gallery/`
- Configuration files
- Documentation

**What Git Does NOT Back Up**:
- Docker volumes: `caddy-data` and `caddy-config` (contain TLS certificates)
- Server configuration outside the repo
- Database content (not applicable - static site)

### Docker Volumes (Separate Backup)

**Covered by restic** (see root `BACKUP.md`):

Daily automated backups via restic of:
- `caddy-data` volume (TLS certificates, critical for HTTPS)
- `caddy-config` volume (Caddy's internal config)
- 7-day retention policy

**Why This Matters**: If server dies, you need TLS certificates to avoid downtime. Restic ensures you can restore them.

### Image File Size Considerations

**Current State**: ~10 images × 300KB average = ~3MB total gallery

**Git Is Fine For This**: GitHub repos can be 1-5GB before issues. Your entire repo is probably under 10MB.

**If You Reach 100+ Images** (30-50MB+):

Consider **Git LFS (Large File Storage)**:
- Git tracks image metadata and pointers
- Actual image files stored on GitHub LFS servers
- Repo stays small, images pulled on demand
- Free tier: 1GB storage + 1GB bandwidth/month
- Paid: $5/month for 50GB storage

**Alternative**: Separate image hosting (Cloudflare R2, Backblaze B2, AWS S3) with Git tracking only metadata JSON.

### Redundancy (Paranoid Mode)

**If you want belt-and-suspenders backup**:

1. **Add second Git remote** (GitLab or Bitbucket):
   ```bash
   git remote add gitlab git@gitlab.com:username/hensler_photography.git
   git push gitlab main
   ```
   Now pushes go to both GitHub and GitLab.

2. **Local backup**: Clone repo to external hard drive monthly

3. **Restic to multiple destinations**: Backup to both Backblaze B2 and local NAS

**Reality Check**: For a personal photography site, GitHub + restic is more than sufficient.

### Disaster Recovery

**Scenario**: VPS explodes, everything gone.

**Recovery Steps**:
1. Provision new VPS (same size, Ubuntu)
2. Install Docker and Docker Compose
3. Clone repo: `git clone https://github.com/yourusername/hensler_photography.git`
4. Restore restic backup to recover TLS certificates (see BACKUP.md)
5. Run `docker compose up -d`
6. DNS already points to your domain, update A record to new VPS IP
7. Site is live in ~30 minutes

---

## Testing Workflow

**Golden Rule**: Always test on development server (port 8080) before deploying to production.

### Local Testing Steps

1. **Make changes** in `/opt/dev/hensler_photography/sites/adrian/`

2. **Start test container** (if not already running):
   ```bash
   cd /opt/dev/hensler_photography
   docker compose -p hensler_test -f docker-compose.local.yml up -d
   ```

3. **Access test site**:
   - From VPS: `http://localhost:8080/adrian`
   - From remote: `http://VPS-IP:8080/adrian`
   - (Or `https://adrian.hensler.photography:8080/` if domain routing configured)

4. **Visual inspection**:
   - Does the page load?
   - Is the ghost typography rendering correctly?
   - Does the slideshow cycle automatically?
   - Do manual arrows work?
   - Does hover pause the slideshow?
   - Does the gallery grid preserve aspect ratios?
   - Click a thumbnail - does the lightbox open?
   - Are all images loading?

5. **Browser DevTools check** (F12):
   - **Console tab**: Look for JavaScript errors (red text)
   - **Network tab**: Filter by "Img", verify all images return 200 OK (not 404)
   - Any warnings about mixed content (HTTP vs HTTPS)?

6. **Responsive testing**:
   - Resize browser window to mobile width (~375px)
   - Gallery should switch to 1 column
   - Slideshow should be shorter (300px height)
   - Text should remain readable
   - Or use DevTools Device Toolbar (Cmd+Shift+M)

7. **Test animations**:
   - Hard refresh (Cmd+Shift+R / Ctrl+Shift+F5) to see fade-in animations
   - Staggered delays should create cascading effect

### Playwright Tests (Automated)

**Location**: `/tests/sites.spec.js`

**Status**: Tests exist but may be outdated after recent changes (slideshow, ghost typography)

**To run tests**:
```bash
cd /opt/dev/hensler_photography

# First time setup
npm install
npx playwright install --with-deps

# Run all tests
npm test

# Interactive mode
npm run test:ui

# Debug mode
npx playwright test --debug tests/sites.spec.js
```

**What tests should verify** (need updating):
- Page loads with correct title: "Adrian Hensler Photography"
- Header shows "adrian hensler" (lowercase)
- Slideshow container exists and has slides
- Gallery grid renders with 10 items
- All images return 200 OK status
- Lightbox functionality works
- Responsive breakpoints function correctly
- No JavaScript errors in console

**Screenshots**: Tests generate screenshots to `/screenshots/` for visual regression testing.

### Pre-Deploy Checklist

Before committing and deploying to production, verify:

- ✅ Test site looks correct at `http://localhost:8080/adrian`
- ✅ Browser console has no errors (F12 → Console)
- ✅ All images load (F12 → Network → Img)
- ✅ Slideshow cycles automatically every 5 seconds
- ✅ Manual navigation arrows work
- ✅ Gallery grid preserves aspect ratios
- ✅ Lightbox opens and displays images full-screen
- ✅ Responsive design works on mobile width
- ✅ (Optional) Playwright tests pass: `npm test`

**Only after all checks pass**: Commit and deploy.

### Deployment to Production

See root `DEVELOPMENT.md` and `CLAUDE.md` for detailed workflow. Summary:

```bash
# In /opt/dev/hensler_photography
git add sites/adrian/
git commit -m "Update Adrian gallery with new images"
git push origin main

# Switch to production
cd /opt/prod/hensler_photography
git pull origin main
docker compose restart

# Verify production
curl -I https://adrian.hensler.photography/
# Should return 200 OK
```

**Post-Deploy Verification**:
- Visit https://adrian.hensler.photography/ in browser
- Check that changes are live
- Test slideshow and gallery
- Check browser console for errors
- Test from mobile device

---

## File Structure

```
sites/adrian/
├── index.html                  # Main HTML/CSS/JavaScript (all-in-one)
├── assets/
│   └── gallery/
│       ├── 52871221196_95f87f72ce_b.jpg
│       ├── 53225347053_31cd2f818e_b.jpg
│       ├── 53470724843_5747fc8ff5_b.jpg
│       ├── 53615968247_4d4ecff67c_b.jpg
│       ├── 53617286790_597f1818c5_b.jpg
│       ├── 53777597401_77cf321b21_b.jpg
│       ├── 53904082912_fd86ce3ff5_b.jpg
│       ├── 54097487564_56266abcf2_b.jpg
│       ├── 54770451360_a3eb449678_b.jpg
│       └── 54770451375_d527619b96_b.jpg  # (10 images total)
├── FUTURE_ENHANCEMENTS.md      # Long-term AI vision for site
└── README.md                   # This documentation file
```

**Key Files**:

- **index.html**: Everything is in this one file
  - Lines 1-371: HTML structure and meta tags
  - Lines 17-366: CSS styles (embedded in `<style>` tag)
  - Lines 415-532: JavaScript (embedded in `<script>` tag)
  - Line 418-429: `galleryImages` array ← **Edit this to add/remove images**

- **assets/gallery/**: All gallery images (must match filenames in array)

- **FUTURE_ENHANCEMENTS.md**: Documents the long-term vision for AI-powered image ingestion, auto-tagging, multiple gallery categories, and dynamic content management

---

## Maintenance Checklist

### Weekly
- Check site is loading correctly: https://adrian.hensler.photography/
- Verify HTTPS certificate is valid (green padlock in browser)

### Monthly
- Review browser console for any errors (F12 → Console)
- Check Core Web Vitals in Google Search Console
- Update gallery with new images (if available)

### Quarterly
- Run Lighthouse audit for performance/accessibility
- Review and update documentation if workflow changes
- Check for GLightbox library updates
- Review backup integrity (test restic restore)

### Annually
- Review security headers (still current best practices?)
- Consider WebP conversion for performance boost
- Review and update FUTURE_ENHANCEMENTS.md roadmap

---

## Getting Help Without Claude CLI

If you lose access to Claude CLI or other AI tools, this documentation should be sufficient to maintain the site. Key resources:

**For HTML/CSS/JavaScript questions**:
- MDN Web Docs: https://developer.mozilla.org/
- CSS-Tricks: https://css-tricks.com/
- Stack Overflow: https://stackoverflow.com/

**For GLightbox issues**:
- Official docs: https://github.com/biati-digital/glightbox
- CDN jsdelivr: https://www.jsdelivr.com/package/npm/glightbox

**For Docker/Caddy issues**:
- Caddy docs: https://caddyserver.com/docs/
- Docker Compose docs: https://docs.docker.com/compose/

**For Git/GitHub issues**:
- Git documentation: https://git-scm.com/doc
- GitHub docs: https://docs.github.com/

**Emergency Contact**: If the site goes down and you're stuck, the most critical files are:
1. `Caddyfile` (web server config)
2. `docker-compose.yml` (container config)
3. `sites/adrian/index.html` (site content)

These three files can rebuild the site from scratch on a new server.

---

**End of Documentation**

*For questions about the overall project architecture and multi-site deployment, see root `/opt/prod/hensler_photography/CLAUDE.md` and `DEVELOPMENT.md`.*
