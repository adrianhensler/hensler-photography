# Design Notes: Adrian Hensler Photography

## Recent Updates (2025-10-14)

### Phase 0: Typography & Content - COMPLETED ✅
**Branch**: `feature/design-refresh`

**What Changed**:
- ✅ Upgraded typography: Playfair Display (serif headings) + Inter (body text)
- ✅ Increased heading size: 40-64px (was 28-44px) for better visual hierarchy
- ✅ Implemented 8px baseline grid for consistent spacing
- ✅ Improved text contrast: #f5f5f5 (was #eee with opacity)
- ✅ Added contact email: adrianhensler@gmail.com with warm accent color
- ✅ Added bio: "Based in Halifax, Nova Scotia."
- ✅ Better button interactions: subtle lift on hover + border brightening

**Impact**: Site now looks more professional and polished. Typography has personality. Contact information is clear.

**Still Needed**:
- Reduce hero image prominence (currently too dominant)
- Add gallery section with 4+ photography samples
- Visual polish (animations, refinements)

---

## Current State (v1.0.0 → v1.1.0 in progress)

### Overview
Clean, minimalist dark-themed landing page with single hero image and Flickr link. Functions as a professional redirect rather than a full portfolio showcase.

### What Works ✅
- Dark theme creates gallery-like atmosphere appropriate for photography
- Hero image has strong visual impact
- Typography is clean and readable
- Fast loading (minimal assets)
- Mobile-responsive layout
- Security headers properly configured
- Professional, uncluttered aesthetic

### Current Limitations
- **No gallery**: Only shows one hero image
- **Redirect-focused**: Primary CTA sends users to Flickr instead of showcasing work here
- **Limited content**: No bio, no story, minimal information about photography style
- **Single call-to-action**: Only one button (Flickr link)
- **Minimal engagement**: No reason to stay on site vs. going directly to Flickr

---

## Design Improvement Roadmap

### Phase 1: Content Foundation (High Priority)

#### 1. Add Gallery Section
**Goal**: Showcase best photography directly on the site

**Implementation**:
- Create 3x3 grid of featured photos (9-12 images)
- Images should represent photography style/range
- Grid layout: 3 columns desktop, 2 columns tablet, 1 column mobile
- Hover effects: slight zoom + overlay with photo title
- Click to open lightbox/modal for full-screen viewing

**Files needed**:
- `sites/adrian/assets/gallery/` directory
- 9-12 images (400x400px thumbnails, 1920px full-size)
- WebP format with JPEG fallback

**Code additions**:
- Gallery section in HTML
- CSS Grid layout
- Lightbox modal component
- JavaScript for modal interaction

#### 2. Add About Section
**Goal**: Tell the story and connect with viewers

**Content to include**:
- 2-3 sentence bio
- Photography style/approach
- What subjects you shoot (landscape, street, etc.)
- Optional: Equipment/technique mention

**Placement**: Between hero and gallery, or after gallery before footer

#### 3. Enhanced Typography Hierarchy
**Goal**: Better content structure and visual interest

**Changes**:
- Add tagline/subtitle below name (e.g., "Landscape & Street Photography")
- Larger section headings for Gallery and About
- Better spacing between sections
- Improved readability on mobile

### Phase 2: Engagement & Polish (Medium Priority)

#### 4. Multiple Call-to-Actions
**Goal**: Give users multiple engagement options

**Add**:
- Primary: "View Full Portfolio" (gallery on site)
- Secondary: "Follow on Flickr" (external link)
- Tertiary: Contact/email button or link

#### 5. Micro-Interactions
**Goal**: Modern, engaging user experience

**Add**:
- Fade-in animations on scroll for gallery items
- Smooth scroll behavior for navigation
- Hover effects on gallery thumbnails
- Smooth transitions between states

#### 6. Image Optimization
**Goal**: Fast loading without sacrificing quality

**Optimize**:
- Convert to WebP format (80-85% quality)
- Create responsive image sets (srcset)
- Implement lazy loading for below-fold images
- Compress hero image further if needed

### Phase 3: Advanced Features (Lower Priority)

#### 7. Image Categories/Filter
**Goal**: Organize work by theme

**Add**:
- Categories: Landscape, Street, Portrait, etc.
- Filter buttons above gallery
- Smooth transitions when filtering

#### 8. Lightbox Gallery Navigation
**Goal**: Browse all images without returning to page

**Add**:
- Previous/Next buttons in lightbox
- Keyboard navigation (arrow keys)
- Image counter (e.g., "3 of 12")
- Optional: Thumbnails strip at bottom

#### 9. Contact Form
**Goal**: Enable direct inquiries

**Add**:
- Simple contact form (name, email, message)
- Or: Prominent email link with mailto
- Response time expectations

---

## Inspiration Sites

### Photography Portfolios to Study
When designing improvements, reference these approaches:

**Minimalist Approach** (similar to current):
- Keep dark theme
- Focus on imagery
- Minimal text
- Clean typography

**Gallery Patterns**:
- Grid layouts with consistent sizing
- Hover effects revealing titles
- Lightbox modals for viewing
- Category filters

**Engagement**:
- Clear CTAs throughout
- About section that tells a story
- Multiple ways to connect

---

## Technical Specifications

### Image Requirements

**Hero Image** (existing):
- Current: `adrian-hero.jpg`
- Recommended: 1920px wide, WebP @ 85% quality
- Mobile version: 800px wide

**Gallery Thumbnails** (to add):
- Size: 400x400px
- Format: WebP with JPEG fallback
- Quality: 80%
- Naming: `img-01-thumb.webp`, `img-01-thumb.jpg`

**Gallery Full-Size** (to add):
- Size: 1920px wide max
- Format: WebP with JPEG fallback
- Quality: 85%
- Naming: `img-01.webp`, `img-01.jpg`

### Color Palette

**Current**:
- Background: `#0b0b0b` (near black)
- Text: `#eeeeee` (off-white)
- Accent: Border `#444` (dark gray)

**Suggested additions**:
- Accent color for CTAs: Consider subtle blue or warm tone
- Hover states: Lighter background `#151515`
- Link color: Inherit with underline or subtle accent

### Typography

**Current**:
- Font: `system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Arial, sans-serif`
- Heading: `clamp(28px, 4vw, 44px)` - good, keep this
- Body: Default size

**Suggested**:
- Tagline: `clamp(18px, 2vw, 22px)`, `opacity: 0.8`
- Section headings: `clamp(24px, 3vw, 32px)`
- Gallery captions: `14px`, `opacity: 0.7`

---

## Development Workflow

When implementing improvements:

1. **Plan**: Update this document with specific changes
2. **Test locally**: Use port 8080 test environment
3. **Get critique**: Use `web-design-critic` subagent for feedback
4. **Implement**: Use `modern-css-developer` subagent for code
5. **Test**: Run Playwright tests, check mobile
6. **Deploy**: Follow WORKFLOW.md procedures
7. **Tag**: Create version tag (v1.1.0, v1.2.0, etc.)

---

## Questions to Answer

Before implementing major changes, consider:

### Content
- Which 9-12 photos best represent your work?
- What story do you want to tell in the About section?
- What's your tagline? (e.g., "Landscape Photographer | Halifax, Nova Scotia")

### Design
- Keep dark theme or explore other options?
- Prefer minimalist or more detailed?
- Any specific photography sites you love?

### Features
- Priority: Gallery first, or About section first?
- Need contact form, or just email link?
- Want image categories, or single gallery for now?

---

## Next Steps

1. **Immediate**: Use `web-design-critic` subagent to analyze current site
2. **Content prep**: Select 9-12 best photos for gallery
3. **Write bio**: Draft About section content
4. **Implement Phase 1**: Gallery section with lightbox
5. **Test and iterate**: View on port 8080, gather feedback
6. **Deploy**: Push to production when ready

---

## Version History

- **v1.0.0** (2025-10-13): Initial site with hero image and Flickr link
- **v1.x.x** (Future): Gallery section added
- **v1.x.x** (Future): About section and enhanced typography

---

## Resources

- **Documentation**: See `/DEVELOPMENT.md` for development best practices
- **Subagents**: See `.claude/agents/` for specialized AI assistance
- **Deployment**: See `/WORKFLOW.md` for deployment procedures
- **Inspiration**: Browse photography portfolio sites for ideas
