# Analytics & EXIF Sharing Features - TODO

## Current Status

**✅ Already Implemented:**
- Frontend tracking JavaScript (`sites/adrian/index.html`)
  - Page views tracked via `trackEvent('page_view')`
  - Gallery clicks tracked with image index
  - Lightbox opens tracked
  - Privacy-preserving: hashed IPs, ephemeral session IDs
- Backend API endpoint: `POST /api/track`
- Database table: `image_events` (stores all events)
- Main.py handler (lines 425-492)

**❌ Not Yet Implemented:**
- Analytics dashboard to VIEW the data
- Popular images sorting/display
- EXIF sharing controls per-image

---

## Feature 1: Analytics Dashboard

### User Stories

**As a photographer, I want to:**
- See which of my images get the most views
- Understand which tags drive traffic
- Know when people visit my gallery (time patterns)
- Export data for external analysis

**As an admin, I want to:**
- See aggregate statistics across all photographers
- Identify trending images site-wide
- Monitor API costs vs traffic

### Proposed Implementation

#### Route: `/manage/analytics`

**UI Layout:**
```
┌─────────────────────────────────────────────────────┐
│  Analytics Dashboard                                │
├─────────────────────────────────────────────────────┤
│  📊 Overview (Last 30 Days)                         │
│  ┌─────────────┬─────────────┬─────────────┐       │
│  │ 1,234       │ 856         │ 42          │       │
│  │ Total Views │ Image Clicks│ Avg Session │       │
│  └─────────────┴─────────────┴─────────────┘       │
│                                                      │
│  🏆 Most Popular Images                             │
│  ┌────────────────────────────────────────┐        │
│  │ 1. Rainbow's End        (245 views)    │        │
│  │ 2. Poseidon's Fury      (189 views)    │        │
│  │ 3. Mountain Sunrise     (156 views)    │        │
│  └────────────────────────────────────────┘        │
│                                                      │
│  📈 Views Over Time                                 │
│  [Chart: Last 30 days, grouped by day]             │
│                                                      │
│  🏷️  Popular Tags                                   │
│  landscape (412), sunset (234), seascape (189)      │
│                                                      │
│  [Export to CSV]  [View Details]                    │
└─────────────────────────────────────────────────────┘
```

#### Database Queries

**Most viewed images (last 30 days):**
```sql
SELECT
    i.id,
    i.filename,
    i.title,
    COUNT(e.id) as view_count,
    COUNT(DISTINCT e.session_id) as unique_visitors
FROM images i
LEFT JOIN image_events e ON i.id = e.image_id
WHERE e.event_type IN ('gallery_click', 'lightbox_open')
  AND e.timestamp >= datetime('now', '-30 days')
  AND i.user_id = ?
GROUP BY i.id
ORDER BY view_count DESC
LIMIT 10;
```

**Views over time:**
```sql
SELECT
    DATE(timestamp) as date,
    COUNT(*) as view_count
FROM image_events
WHERE event_type = 'page_view'
  AND timestamp >= datetime('now', '-30 days')
GROUP BY DATE(timestamp)
ORDER BY date ASC;
```

**Tag popularity:**
```sql
SELECT
    tag,
    COUNT(DISTINCT e.session_id) as unique_visitors
FROM (
    SELECT
        i.id,
        TRIM(value) as tag
    FROM images i, json_each('["' || REPLACE(i.tags, ',', '","') || '"]')
    WHERE i.user_id = ? AND i.published = 1
) tags
JOIN image_events e ON tags.id = e.image_id
WHERE e.event_type IN ('gallery_click', 'lightbox_open')
  AND e.timestamp >= datetime('now', '-30 days')
GROUP BY tag
ORDER BY unique_visitors DESC
LIMIT 10;
```

#### API Endpoints

**GET `/api/analytics/overview`**
```json
{
  "period": "30d",
  "total_views": 1234,
  "total_clicks": 856,
  "unique_visitors": 342,
  "avg_session_duration": 42
}
```

**GET `/api/analytics/popular-images`**
```json
{
  "images": [
    {
      "id": 5,
      "title": "Rainbow's End",
      "filename": "...",
      "views": 245,
      "clicks": 189,
      "unique_visitors": 156
    }
  ]
}
```

**GET `/api/analytics/views-timeline?period=30d`**
```json
{
  "data": [
    {"date": "2025-11-01", "views": 45},
    {"date": "2025-11-02", "views": 52}
  ]
}
```

**GET `/api/analytics/export.csv`**
- Returns CSV file with all events
- Headers: date, image_id, image_title, event_type, session_id

---

## Feature 2: Popular Images Sort Order

### User Story

**As a photographer, I want:**
- My most-viewed images to automatically rise to the top of my gallery
- Visitors to see my "best" content first (proven by engagement)
- Option to override with manual sorting

### Proposed Implementation

#### Option A: Automatic Sort on Load

**Gallery API Update:**
```python
@router.get("/api/gallery/published")
async def get_published_gallery(
    user_id: int,
    sort: str = "auto"  # "auto", "popular", "recent", "manual"
):
    if sort == "popular":
        # Join with image_events, order by view count
        query = """
            SELECT i.*, COUNT(e.id) as view_count
            FROM images i
            LEFT JOIN image_events e ON i.id = e.image_id
            WHERE i.user_id = ? AND i.published = 1
            GROUP BY i.id
            ORDER BY view_count DESC, i.created_at DESC
        """
    elif sort == "recent":
        query = "... ORDER BY created_at DESC"
    else:  # manual or auto
        query = "... ORDER BY sort_order ASC, created_at DESC"
```

**Frontend Update:**
```javascript
// In adrian's index.html
const response = await fetch('/api/gallery/published?user_id=1&sort=popular');
```

#### Option B: Background Job Updates `sort_order`

**Cron job (daily at 3am):**
```python
async def update_popularity_scores():
    """
    Calculate popularity score based on last 30 days,
    update sort_order field for auto-sorting
    """
    query = """
        UPDATE images SET sort_order = (
            SELECT COUNT(*)
            FROM image_events
            WHERE image_id = images.id
              AND event_type IN ('gallery_click', 'lightbox_open')
              AND timestamp >= datetime('now', '-30 days')
        )
        WHERE published = 1
    """
```

**Gallery Management UI:**
```
[Sort by: Auto (Popular) ▼] [Manual Sort Mode]
                            └─ Drag to reorder
```

---

## Feature 3: EXIF Sharing Toggle

### User Story

**As a photographer, I want to:**
- Choose whether to share EXIF data publicly per-image
- Keep location private for security reasons
- Optionally hide camera gear from competitors
- Default to NOT sharing (privacy-first)

### Proposed Implementation

#### Database Schema Change

```sql
ALTER TABLE images ADD COLUMN share_exif BOOLEAN DEFAULT 0;
```

**Migration:**
```python
# In api/database.py or new migration script
async def migrate_add_share_exif():
    async with get_db_connection() as db:
        await db.execute("""
            ALTER TABLE images
            ADD COLUMN share_exif BOOLEAN DEFAULT 0
        """)
        await db.commit()
```

#### Gallery Management UI

**Update `gallery.html` card display:**
```html
<div class="image-card">
  <img src="..." />
  <div class="image-content">
    <div class="image-title">Rainbow's End</div>
    <div class="image-caption">...</div>

    <div class="image-tags">...</div>

    <div class="image-meta">
      <span class="badge badge-category">landscape</span>

      <!-- NEW: EXIF sharing indicator -->
      <span class="badge ${img.share_exif ? 'badge-exif-shared' : 'badge-exif-private'}">
        ${img.share_exif ? '📷 EXIF Shared' : '🔒 EXIF Private'}
      </span>
    </div>

    <div class="image-actions">
      <button onclick="editImage(${img.id})">Edit</button>

      <button class="visibility-toggle is-public">● Public</button>

      <!-- NEW: EXIF toggle button -->
      <button class="exif-toggle ${img.share_exif ? 'is-shared' : 'is-private'}"
              onclick="toggleEXIF(${img.id}, ${img.share_exif})"
              title="Toggle EXIF data sharing">
        ${img.share_exif ? '📷' : '🔒'}
      </button>

      <button onclick="deleteImage(${img.id})" class="action-danger">Delete</button>
    </div>
  </div>
</div>
```

**CSS for EXIF toggle:**
```css
.exif-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem;
  font-size: 1.1rem;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.exif-toggle.is-private {
  background: #f5f5f7;
  color: #6e6e73;
}

.exif-toggle.is-shared {
  background: #34c759;
  color: white;
}

.badge-exif-shared {
  background: rgba(52, 199, 89, 0.15);
  color: #34c759;
}

.badge-exif-private {
  background: rgba(0, 0, 0, 0.05);
  color: #6e6e73;
}
```

**JavaScript function:**
```javascript
async function toggleEXIF(imageId, currentlyShared) {
  const newState = !currentlyShared;

  try {
    const response = await fetch(`/api/images/${imageId}/exif-sharing?share=${newState}`, {
      method: 'POST',
      credentials: 'include'
    });

    if (!response.ok) throw new Error('Failed to update EXIF sharing');

    // Update local data
    const image = allImages.find(img => img.id === imageId);
    if (image) image.share_exif = newState;

    applyFilters();
  } catch (error) {
    console.error('Error:', error);
    alert('Failed to update EXIF sharing status');
  }
}
```

#### Backend API Endpoint

**POST `/api/images/{image_id}/exif-sharing?share=true`**
```python
@router.post("/{image_id}/exif-sharing")
async def set_exif_sharing(image_id: int, share: bool = True):
    """
    Toggle EXIF data sharing for public gallery.

    When share=False:
    - EXIF data not returned in public API
    - Photographer still sees EXIF in management interface

    Privacy considerations:
    - Location data hidden
    - Camera/lens info hidden
    - Exposure settings hidden
    """
    from api.database import get_db_connection

    async with get_db_connection() as db:
        await db.execute(
            "UPDATE images SET share_exif = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (1 if share else 0, image_id)
        )
        await db.commit()

    return {"success": True, "image_id": image_id, "share_exif": share}
```

#### Public Gallery API Update

**Respect `share_exif` flag:**
```python
@router.get("/published/{slug}")
async def get_published_image(user_id: int, slug: str):
    # ... existing query ...

    # Only return EXIF if share_exif = 1
    exif_data = {}
    if row['share_exif']:
        exif_data = {
            "camera_make": row['camera_make'],
            "camera_model": row['camera_model'],
            "lens": row['lens'],
            "focal_length": row['focal_length'],
            "aperture": row['aperture'],
            "shutter_speed": row['shutter_speed'],
            "iso": row['iso'],
            "date_taken": row['date_taken'],
            "location": row['location']  # Photographer may want this private!
        }

    return {
        "id": row['id'],
        "title": row['title'],
        # ...
        "exif": exif_data if exif_data else None
    }
```

#### Edit Modal Update

**Add EXIF sharing toggle to edit form:**
```html
<form id="editForm">
  <!-- Existing fields: title, caption, tags, category -->

  <h3>Privacy Settings</h3>

  <div class="form-group">
    <label>
      <input type="checkbox" id="editShareEXIF">
      Share EXIF data publicly (camera, lens, exposure settings, location)
    </label>
    <small style="color: #6e6e73;">
      When disabled, technical metadata remains private.
      Only you can see it in the management interface.
    </small>
  </div>

  <!-- Existing EXIF fields -->
</form>
```

---

## Implementation Priority

### Phase 1: EXIF Sharing (Highest Priority)
**Effort:** 2-3 hours
**Impact:** Privacy control, professional feature

**Tasks:**
1. Add `share_exif BOOLEAN DEFAULT 0` column to images table
2. Update `/manage/gallery` UI with EXIF toggle button
3. Create `POST /api/images/{id}/exif-sharing` endpoint
4. Update public gallery API to respect `share_exif` flag
5. Add EXIF sharing checkbox to edit modal
6. Test: Toggle EXIF on/off, verify public API hides/shows data

---

### Phase 2: Analytics Dashboard (Medium Priority)
**Effort:** 1-2 days
**Impact:** High value for photographers, uses existing tracking data

**Tasks:**
1. Create `/manage/analytics` route and template
2. Implement analytics API endpoints:
   - `/api/analytics/overview`
   - `/api/analytics/popular-images`
   - `/api/analytics/views-timeline`
3. Build UI with charts (Chart.js or similar)
4. Add CSV export functionality
5. Test with real tracking data

---

### Phase 3: Popular Images Sorting (Lower Priority)
**Effort:** 4-6 hours
**Impact:** Nice-to-have, depends on Phase 2 data

**Tasks:**
1. Add `sort` parameter to `/api/gallery/published`
2. Implement view count aggregation in query
3. Add sort dropdown to gallery management UI
4. Optional: Background job to update `sort_order`
5. Test: Verify popular images rise to top

---

## Database Migrations Needed

```sql
-- Migration 001: Add EXIF sharing flag
ALTER TABLE images ADD COLUMN share_exif BOOLEAN DEFAULT 0;

-- Index for analytics queries (performance optimization)
CREATE INDEX idx_image_events_image_id ON image_events(image_id);
CREATE INDEX idx_image_events_timestamp ON image_events(timestamp);
CREATE INDEX idx_image_events_type_timestamp ON image_events(event_type, timestamp);
```

---

## Testing Checklist

### EXIF Sharing
- [ ] Toggle EXIF sharing on an image
- [ ] Verify public API returns EXIF when `share_exif=1`
- [ ] Verify public API hides EXIF when `share_exif=0`
- [ ] Verify photographer still sees EXIF in management interface
- [ ] Test location privacy (should be hideable)

### Analytics Dashboard
- [ ] View overview statistics
- [ ] Verify most popular images list is accurate
- [ ] Check views timeline chart displays correctly
- [ ] Export CSV and verify data integrity
- [ ] Test with no tracking data (graceful empty state)

### Popular Sorting
- [ ] Sort gallery by popular
- [ ] Sort gallery by recent
- [ ] Sort gallery by manual order
- [ ] Verify sort persists across page loads

---

## Documentation Updates Needed

- **CLAUDE.md**: Add analytics and EXIF sharing sections
- **DATABASE.md**: Document `share_exif` column and analytics queries
- **ROADMAP.md**: Mark Sprint 6 (Analytics) as in progress
- **sites/adrian/README.md**: Document EXIF sharing controls

---

## Open Questions

1. **EXIF Granularity**: Should photographers control which EXIF fields to share individually?
   - Option A: All-or-nothing toggle (simpler)
   - Option B: Checkboxes per field (more control but complex UI)

2. **Analytics Privacy**: Should we show visitor IP hashes to photographers?
   - Pro: Helps identify bot traffic
   - Con: Privacy concern even with hashing

3. **Popular Sorting Window**: 30 days? 90 days? All-time?
   - Recommendation: Last 30 days (keeps gallery fresh)

4. **EXIF Display on Public Site**: How to show EXIF when shared?
   - Option A: Tooltip on hover
   - Option B: Lightbox metadata panel
   - Option C: Dedicated image detail page

---

## References

- **Sprint 6 Plan**: ROADMAP.md lines 427-456
- **Tracking Implementation**: sites/adrian/index.html lines 555-614
- **Database Schema**: DATABASE.md, api/database.py
- **Analytics Endpoint**: api/main.py lines 425-492
