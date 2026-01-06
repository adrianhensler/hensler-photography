# Public Analytics Feature - Planning Document

**Status**: PLANNED (Not yet implemented)
**Proposed Version**: v2.2.0
**Last Updated**: 2026-01-04

## Overview
Add public analytics display on hensler.photography showing comparative performance metrics for Adrian's and Liam's photography portfolios. This showcases real portfolio activity, highlights top-performing images, demonstrates AI-assisted development, while maintaining privacy-first principles.

## Business Goals
1. **Transparency**: Show portfolios are actively viewed and engaged with
2. **Showcase**: Highlight most popular images from each photographer
3. **Competition**: Friendly comparison between Adrian and Liam (requires Liam's approval first)
4. **AI Demonstration**: Showcase AI-generated code quality in production

## Requirements Summary

### User Preferences (from planning session Jan 4, 2026)
- **Security**: No concerns about showing aggregated metrics (all privacy-preserving)
- **Layout**: Side-by-side comparison with radio/toggle buttons to switch views
- **Visualization**: Color-coded graphs for top performing images
- **Update Frequency**: Smart caching - update only if >2 hours since last fetch
- **Scalability**: Keep simple for now (2 photographers), think about expansion later
- **Focus**: Photography site first - analytics are supplementary

## Current Analytics System

### What's Already Tracked (Privacy-Safe)
The existing private dashboard (at `/manage/analytics`) tracks:
- **Impressions**: Images reaching 50%+ viewport visibility
- **Clicks**: Thumbnail clicks in grid or slideshow
- **Lightbox views**: Full-screen image opens
- **CTR**: Click-through rate (clicks / impressions)
- **View-through rate**: Views / clicks
- **Lightbox duration**: Time spent viewing each image
- **Scroll depth**: 25%, 50%, 75%, 100% milestones
- **Categories**: Performance by image category
- **Timeline**: Daily aggregates over 7/30/90 days

### Privacy Protection Built-In
✅ IP addresses hashed (SHA256), never stored raw
✅ No cookies or persistent identifiers
✅ Session IDs are client-generated, ephemeral (sessionStorage)
✅ No PII collected (no names, emails, locations)
✅ User agents captured but not individually linked
✅ All public data will be aggregated only

## Proposed Architecture

### Backend: Public API Endpoint

**New endpoint**: `/api/analytics/public/comparison` (NO auth required)

Returns JSON structure:
```json
{
  "period": "30 days",
  "updated_at": "2026-01-04T12:34:56Z",
  "photographers": [
    {
      "user_id": 1,
      "name": "Adrian",
      "metrics": {
        "impressions": 1247,
        "clicks": 342,
        "views": 189,
        "ctr": 27.4,
        "view_through_rate": 55.3
      },
      "top_images": [
        {"title": "...", "thumbnail_url": "...", "impressions": 189, "clicks": 52}
      ],
      "leading_category": {"name": "Landscape", "impressions": 847},
      "timeline": [{"date": "2025-12-05", "impressions": 42}]
    },
    {
      "user_id": 2,
      "name": "Liam",
      // ... same structure
    }
  ]
}
```

### Frontend: Embedded Section on Main Landing Page

Add to `/sites/main/index.html`:
- **Photographer toggle**: Radio buttons (Adrian | Liam | Compare)
- **Metrics cards**: Impressions, clicks, views, CTR
- **Top Images chart**: Bar chart, color-coded (Adrian=blue, Liam=green)
- **Timeline graph**: Dual-line chart showing impression trends
- **Privacy notice**: Link to `/about-analytics` page

### Smart Caching Strategy
- **localStorage** cache with 2-hour TTL
- Fetch fresh data only when:
  - Page first loads AND cache expired
  - User manually forces refresh
- Log cache age in console for debugging

## Files to Create

### New Files
1. `/sites/main/css/analytics.css` - Styling for analytics section
2. `/sites/main/js/public-analytics.js` - Fetch, cache, and render logic
3. `/sites/main/about-analytics.html` - Privacy explainer page
4. `/docs/planning/PUBLIC_ANALYTICS.md` - This document

### Files to Modify
1. `/api/routes/analytics.py` - Add public comparison endpoint
2. `/sites/main/index.html` - Add analytics section
3. `/CLAUDE.md` - Document feature
4. `/CHANGELOG.md` - Add v2.2.0 entry

## Implementation Phases

### Phase 1: Backend (30 minutes)
- [ ] Add `/api/analytics/public/comparison` endpoint to analytics.py
- [ ] Reuse existing query patterns from private dashboard
- [ ] Test with curl: `curl https://adrian.hensler.photography/api/analytics/public/comparison?days=30`
- [ ] Verify JSON structure

### Phase 2: Frontend HTML/CSS (45 minutes)
- [ ] Add analytics section to /sites/main/index.html
- [ ] Create /sites/main/css/analytics.css
- [ ] Add Chart.js CDN (already used in private dashboard)
- [ ] Test responsive layout (desktop, tablet, mobile)

### Phase 3: Frontend JavaScript (60 minutes)
- [ ] Create /sites/main/js/public-analytics.js
- [ ] Implement localStorage caching with 2-hour TTL
- [ ] Build photographer toggle (radio buttons)
- [ ] Render metrics cards
- [ ] Render Chart.js graphs (bar + line charts)
- [ ] Test cache logic and toggle functionality

### Phase 4: Documentation (15 minutes)
- [ ] Create /sites/main/about-analytics.html privacy page
- [ ] Update CLAUDE.md with feature description
- [ ] Add v2.2.0 entry to CHANGELOG.md

### Phase 5: Testing & Deployment (30 minutes)
- [ ] Manual testing on dev server (port 8080)
- [ ] Verify cache (check localStorage, wait 2 hours, refresh)
- [ ] Test mobile viewport
- [ ] **Get Liam's approval** before deploying
- [ ] Deploy to production
- [ ] Verify live

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Too much data → cluttered page | Medium | Start minimal, hide details behind expand/toggle |
| Cache invalidation issues | Low | Add "Force Refresh" button |
| Liam doesn't want comparison | High | **Get approval BEFORE implementing** |
| Low traffic → embarrassing numbers | Low | Use 30-day window for cumulative data |
| Security - exposing too much | Low | All aggregated, document what's NOT shown |

## Privacy Safeguards

### What Will Be Shown Publicly
- ✅ Aggregate impressions, clicks, views (counts only)
- ✅ CTR and view-through rates (calculated metrics)
- ✅ Top 5 images by title + thumbnail
- ✅ Category performance summaries
- ✅ Daily timeline trends (aggregates)

### What Will NOT Be Shown
- ❌ Individual session data or paths
- ❌ IP addresses (even hashed)
- ❌ User agents or browser details
- ❌ Referrer URLs (could contain sensitive params)
- ❌ Individual event timestamps
- ❌ Real-time "current viewers" counts

## Success Criteria

- [ ] Page loads in <2 seconds
- [ ] Graphs render with correct color coding
- [ ] Photographer toggle works smoothly
- [ ] Cache prevents unnecessary API calls (<1 per 2 hours per visitor)
- [ ] No privacy concerns (verified with user)
- [ ] Mobile-friendly responsive design
- [ ] Liam approves comparison feature
- [ ] Photography remains primary focus

## Future Enhancements (Out of Scope)

Potential v3 features:
- Real-time updates via WebSocket
- "Hall of Fame" - all-time top performers
- Visitor location heatmap (country-level only, privacy-safe)
- Export analytics as shareable graphics
- Embed widgets for social media
- Multiple photographer dropdown (when >2 users)

## Estimated Effort

- **Planning**: ✅ Complete (2 hours on Jan 4, 2026)
- **Implementation**: ~3-4 hours
- **Testing**: 30-60 minutes
- **Liam approval**: Variable
- **Total**: ~4-5 hours development work

## Next Steps

1. **Confirm with Liam**: Get explicit approval for public comparison
2. **Schedule implementation**: Block time for 4-5 hour sprint
3. **Backend first**: Build API endpoint and test
4. **Frontend second**: Build UI components
5. **Preview**: Show user working version on dev server
6. **Deploy**: Push to production as v2.2.0

## Related Documentation

- **Current Analytics**: `/api/templates/photographer/analytics.html` (private dashboard)
- **Analytics API**: `/api/routes/analytics.py` (authenticated endpoints)
- **Database Schema**: `/api/database.py` (image_events table)
- **CLAUDE.md**: Main project documentation
- **ROADMAP_PUBLIC.md**: Public-facing roadmap

---

**Notes:**
- This document should remain in `/docs/planning/` for future reference
- DO NOT implement without explicit user approval
- Review privacy considerations before deployment
- Test thoroughly on dev server (port 8080) before production

**Last reviewed**: 2026-01-04 by Adrian
