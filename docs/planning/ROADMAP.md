# Hensler Photography - Product Roadmap

**Version**: 2.0.0
**Last Updated**: 2025-11-23
**Status**: Sprint 3 Complete, Sprint 4 Planning

---

## Vision

Build a scalable, AI-powered photography portfolio management system that empowers multiple photographers to manage their galleries independently while providing centralized administration. Future enhancements will include an AI assistant that helps photographers curate and manage their work through natural conversation.

---

## Sprint Timeline

### Sprint 1: Foundation ✅ **COMPLETE**

**Goal**: Establish core infrastructure and multi-tenant database architecture.

**Duration**: ~2 weeks
**Status**: ✅ Complete

**Delivered**:
- ✅ SQLite database with multi-tenant schema (users, images, variants tables)
- ✅ FastAPI backend application structure
- ✅ Docker Compose orchestration (dev + prod environments)
- ✅ Caddy reverse proxy with automatic HTTPS
- ✅ Dual configuration system (local testing on port 8080, prod on 80/443)
- ✅ Health check endpoints (`/healthz`, `/api/health`)
- ✅ Initial admin dashboard HTML template
- ✅ Seeded database with Adrian (admin) and Liam (photographer) users

**Technical Decisions**:
- SQLite chosen for simplicity (suitable for read-heavy workloads)
- Docker volumes for persistent data
- Separate dev/prod directories for safe testing

---

### Sprint 2: Image Ingestion ✅ **COMPLETE**

**Goal**: Enable image upload with AI-powered analysis and metadata extraction.

**Duration**: ~3 weeks
**Status**: ✅ Complete

**Delivered**:
- ✅ Image upload interface (drag-and-drop + file picker)
- ✅ EXIF metadata extraction (camera, lens, settings, GPS)
- ✅ Claude Vision integration (AI-generated titles, captions, descriptions, tags)
- ✅ WebP variant generation (large 1200w, medium 800w, thumbnail 400w)
- ✅ Image storage organized by user_id (`/uploads/1/`, `/uploads/2/`)
- ✅ Database insertion with full metadata
- ✅ Upload status feedback (success, warnings, errors)
- ✅ API endpoint: `POST /api/images/ingest`

**Technical Achievements**:
- Graceful degradation (EXIF fails → continue, AI fails → use fallback)
- Responsive image optimization (WebP 25-35% smaller than JPEG)
- Unique filename generation to prevent collisions

---

### Sprint 2.5: Gallery Management ✅ **COMPLETE**

**Goal**: Build admin interface for viewing, editing, and publishing images.

**Duration**: ~1 week
**Status**: ✅ Complete

**Delivered**:
- ✅ Gallery management page at `/admin/gallery`
- ✅ Grid view with responsive cards
- ✅ Search and filter (by user, published status, tags)
- ✅ Edit modal for updating metadata (title, description, tags, location)
- ✅ Publish/unpublish toggle
- ✅ Delete functionality with confirmation
- ✅ Bulk actions (select multiple, publish/unpublish all, delete all)
- ✅ API endpoints: `GET /api/images/list`, `PATCH /api/images/{id}`, `DELETE /api/images/{id}`

**User Experience**:
- Real-time updates without page refresh
- Keyboard shortcuts (Esc to close modal)
- Visual feedback for all actions

---

### Sprint 3: Error Handling & Logging ✅ **COMPLETE**

**Goal**: Implement comprehensive error handling and structured logging for diagnosis.

**Duration**: ~1 week
**Status**: ✅ Complete

**Delivered**:
- ✅ **Phase 1**: Structured ErrorResponse class (`api/errors.py`)
  - Error codes (e.g., `VALIDATION_FILE_TOO_LARGE`, `PROCESSING_CLAUDE_FAILED`)
  - Dual-purpose messages (human-readable + technical details)
  - Context injection (user_id, filename, file_size, etc.)
- ✅ **Phase 2**: JSON structured logging (`api/logging_config.py`)
  - Machine-readable logs for AI diagnosis
  - Context fields (user_id, image_id, processing_time_ms)
  - Error logs with stack traces
- ✅ **Phase 3**: Error handling in all services
  - EXIF extraction errors → warning, continue
  - Claude Vision errors → fallback metadata, warning
  - WebP generation errors → skip variants, warning
  - Database errors → clean up files, return error
- ✅ **Phase 4**: Frontend error display
  - Toast notifications for errors and warnings
  - Detailed error messages in upload interface
  - User-friendly explanations

**Technical Quality**:
- No stack traces leaked to frontend
- All errors logged with full context for debugging
- Graceful degradation ensures uploads succeed even if optional steps fail

---

### Sprint 4: Multi-User Reorganization 📋 **PLANNED** (Next)

**Goal**: Implement authentication, move admin to main domain, create photographer dashboards.

**Duration**: ~2-3 weeks
**Status**: 📋 Planned (starts after Sprint 3)

**Objectives**:
1. **Authentication System**
   - Add `password_hash` column to users table
   - Implement JWT authentication with httpOnly cookies
   - Build login page and auth endpoints
   - Create `get_current_user()` FastAPI dependency
   - Seed passwords for Adrian and Liam
2. **Admin Interface Migration**
   - Move admin from `adrian.hensler.photography:4100` to `hensler.photography/admin`
   - Remove port 4100 entirely
   - Update Caddyfile routing
   - Restrict admin interface to role='admin' only
3. **Photographer Dashboards**
   - Create `/manage` routes on each subdomain
   - Build photographer-specific templates (filtered by user_id)
   - Implement user isolation (photographers can only see their own images)
   - Add logout functionality
4. **Authorization & Permissions**
   - Role-based access control (admin vs photographer)
   - Database-level filtering by user_id
   - API endpoint authorization checks
   - Frontend permission-based UI (hide admin links from photographers)

**Deliverables**:
- ✅ `POST /api/auth/login` - Username + password → JWT cookie
- ✅ `POST /api/auth/logout` - Clear session
- ✅ `GET /api/auth/me` - Get current user
- ✅ `POST /api/auth/register` - Create user (admin only)
- ✅ Login page at `/admin/login`
- ✅ Photographer dashboard at `liam.hensler.photography/manage`
- ✅ Photographer dashboard at `adrian.hensler.photography/manage`
- ✅ Updated Caddyfile (remove port 4100, add /manage routes)
- ✅ User isolation enforced in all API endpoints
- ✅ Permission matrix implemented (see ARCHITECTURE.md)

**Success Criteria**:
- Adrian can log in and access `/admin` (sees all images from both users)
- Liam can log in and access `/manage` (sees only his images)
- Photographers cannot access each other's images
- Port 4100 removed, all access through standard HTTPS ports
- Session management works correctly (24-hour expiry)

**Estimated Effort**: 18-22 hours
- Authentication: 8-10 hours
- Admin migration: 3 hours
- Photographer dashboards: 5-6 hours
- Testing & bug fixes: 2-3 hours

---

### Sprint 5: AI Chatbot Assistant 📋 **PLANNED**

**Goal**: Build an AI assistant that helps photographers manage their galleries through natural conversation.

**Duration**: ~2-3 weeks
**Status**: 📋 Planned (after Sprint 4 complete)

**Motivation**:
Create an experience similar to Claude Code CLI but within the photographer dashboard:
- Photographers can ask questions about their images
- AI assistant suggests improvements (tags, titles, descriptions)
- Natural language search ("Show me landscapes from October")
- Conversational image management ("Publish all my sunset photos")

**Architecture**:

**Backend** (`api/routes/chat.py`):
```python
@router.post("/api/chat/message")
async def chat_message(
    message: str,
    current_user: User = Depends(get_current_user)
):
    # 1. Load conversation history from database
    conversation = get_conversation(current_user.id)

    # 2. Build system prompt with user isolation
    system_prompt = f"""
    You are a photography assistant for {current_user.display_name}.
    You can only access images belonging to user_id={current_user.id}.
    You cannot delete images, access admin functions, or see other photographers' work.
    Always confirm before making changes.
    """

    # 3. Call Claude API with tool functions
    response = anthropic.messages.create(
        model="claude-3-5-sonnet-20241022",
        system=system_prompt,
        messages=conversation + [{"role": "user", "content": message}],
        tools=[
            list_images_tool,
            get_image_details_tool,
            suggest_tags_tool,
            update_metadata_tool,
            publish_image_tool,
            find_similar_tool
        ],
        stream=True
    )

    # 4. Execute tool calls (with user_id verification)
    for chunk in response:
        if chunk.type == "tool_use":
            result = execute_tool(chunk.name, chunk.input, current_user.id)
            # Return result to Claude for final response

    # 5. Save message to database
    save_message(current_user.id, message, response)

    # 6. Stream response to frontend
    return StreamingResponse(response)
```

**Tool Functions**:

1. **list_images(filters: dict)**
   - Search gallery with natural language filters
   - Examples:
     - "Show me unpublished images"
     - "Find all landscapes from October 2024"
     - "Which images have no tags?"
   - Returns: List of image IDs + metadata

2. **get_image_details(image_id: int)**
   - Get full metadata for a specific image
   - Shows: Title, description, tags, EXIF, published status
   - Returns: Complete image record

3. **suggest_tags(image_id: int)**
   - AI-powered tag suggestions based on existing metadata
   - Analyzes: Current tags, description, EXIF data
   - Returns: List of recommended tags

4. **update_metadata(image_id: int, changes: dict)**
   - Edit image metadata (title, description, tags, location)
   - Requires confirmation before executing
   - Verifies image ownership
   - Returns: Updated image record

5. **publish_image(image_id: int, published: bool)**
   - Toggle published status
   - Requires confirmation
   - Returns: Success/failure status

6. **find_similar(image_id: int)**
   - Find images with similar tags or metadata
   - Useful for organizing related photos
   - Returns: List of similar image IDs + similarity scores

**Guardrails & Safety**:

1. **User Isolation**:
   - System prompt explicitly restricts to authenticated user_id
   - All tool functions verify `image.user_id == current_user.id` before executing
   - Cannot access images belonging to other photographers
   - Cannot access admin functions (user management, global stats)

2. **Confirmation Requirements**:
   - State-changing actions require explicit confirmation
   - Examples:
     - "I'm about to publish image #42. Confirm?"
     - "I'll update the title to 'Mountain Sunset'. Proceed?"
   - User must respond "yes" or "confirm" before action executes

3. **Rate Limiting**:
   - Maximum 20 messages per hour per user
   - Prevents abuse and controls API costs
   - Error message if limit exceeded: "You've reached your message limit. Please try again in X minutes."

4. **Function Restrictions**:
   - Cannot call DELETE endpoints (safety measure)
   - Cannot create new users
   - Cannot modify other users' data
   - Cannot access global analytics (admin only)

5. **Error Handling**:
   - If tool function fails, AI explains what went wrong
   - No stack traces exposed to user
   - Structured error responses

**Frontend** (Chat Widget):

**UI Design**:
- Persistent widget in `/manage` dashboard (bottom-right corner)
- Click to expand into full chat panel
- Conversation history preserved per session
- Typing indicator while AI is responding
- Suggested prompts for new users:
  - "Show me my unpublished images"
  - "Find landscapes from last month"
  - "Suggest tags for image #42"
  - "Which images should I feature?"

**JavaScript** (`/manage` page):
```javascript
// Chat widget
const chatWidget = {
    open: false,
    messages: [],
    async sendMessage(text) {
        this.messages.push({role: 'user', content: text});

        // Stream response from backend
        const response = await fetch('/api/chat/message', {
            method: 'POST',
            body: JSON.stringify({message: text}),
            headers: {'Content-Type': 'application/json'}
        });

        const reader = response.body.getReader();
        let aiMessage = {role: 'assistant', content: ''};
        this.messages.push(aiMessage);

        // Stream chunks
        while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            const chunk = new TextDecoder().decode(value);
            aiMessage.content += chunk;
            this.renderMessages();
        }
    }
};
```

**Database Tables** (Conversation History):

```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_message_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    role TEXT NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    tool_calls TEXT,  -- JSON array of tool invocations
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);
```

**Example Interactions**:

**User**: "Show me my unpublished images"
**AI**: "I found 12 unpublished images in your gallery. Here are the most recent ones:
- Image #45: Mountain Sunset (uploaded 2 days ago)
- Image #44: Forest Path (uploaded 3 days ago)
- Image #43: City Lights (uploaded 1 week ago)
Would you like me to show you the full list or help you publish some?"

**User**: "Suggest tags for image 45"
**AI**: "Based on the current title 'Mountain Sunset' and description, I suggest these tags:
- landscape
- mountains
- sunset
- golden-hour
- dramatic
- nature
- wilderness
Should I add these tags to the image?"

**User**: "Yes, and publish it"
**AI**: "I'll add those 7 tags and publish image #45. Confirm?"
**User**: "Confirm"
**AI**: "Done! Image #45 'Mountain Sunset' is now published with updated tags. It will appear on your public portfolio at adrian.hensler.photography."

**Deliverables**:
- ✅ `POST /api/chat/message` endpoint with streaming support
- ✅ Tool function implementations (6 functions)
- ✅ User isolation and permission checks
- ✅ Rate limiting (20 messages/hour)
- ✅ Confirmation flow for state changes
- ✅ Chat widget UI in `/manage` dashboard
- ✅ Database tables for conversation history
- ✅ Comprehensive testing with various prompts

**Success Criteria**:
- Photographers can ask questions and get helpful responses
- Tool functions execute correctly with user isolation enforced
- Confirmation required before making changes
- Rate limiting prevents abuse
- Conversation history persists across sessions
- Error handling is graceful and informative

**Estimated Effort**: 20-25 hours
- Backend API + tool functions: 8-10 hours
- Frontend chat widget: 5-6 hours
- Guardrails + security: 3-4 hours
- Testing + refinement: 4-5 hours

---

### Sprint 6: Analytics Dashboard 📋 **PLANNED**

**Goal**: Track image views, clicks, and provide insights to photographers.

**Duration**: ~1-2 weeks
**Status**: 📋 Planned (after Sprint 5)

**Features**:
- Track image views and clicks (insert into `image_events` table)
- Popular images report (most viewed/clicked in last 30 days)
- Geographic visitor distribution (if available from IP address)
- Time-series charts (views over time, daily/weekly/monthly)
- Tag popularity analysis (which tags drive the most views)
- Export analytics data to CSV
- Admin sees global analytics, photographers see only their own

**Technical Approach**:
- JavaScript tracking code on public portfolio pages
- Beacon API for reliable event tracking
- Daily aggregation queries for performance
- Chart.js for data visualization
- Redis caching for frequently accessed metrics (optional)

**Deliverables**:
- ✅ Analytics tracking script on public sites
- ✅ `POST /api/events/track` endpoint
- ✅ Analytics dashboard at `/manage/analytics`
- ✅ Report generation (top 10 images, trends, etc.)
- ✅ CSV export functionality
- ✅ Admin global analytics at `/admin/analytics`

**Estimated Effort**: 12-15 hours

---

### Sprint 7: Static Site Generator 📋 **PLANNED**

**Goal**: Generate SEO-friendly static photo detail pages.

**Duration**: ~2 weeks
**Status**: 📋 Planned

**Features**:
- Pre-render individual photo pages at `/photo/{slug}`
- Server-side generated HTML with full metadata
- Open Graph meta tags for social media sharing
- Structured data (JSON-LD) for search engines
- Pagination for gallery grids
- Sitemap generation
- Export static JSON API for frontend consumption

**Technical Approach**:
- Jinja2 templates for photo detail pages
- Build script generates static HTML files
- Caddy serves static files with fallback to API
- Regenerate on publish/unpublish events

**Estimated Effort**: 15-18 hours

---

### Sprint 8+: Future Enhancements 💡 **IDEAS**

**E-Commerce Integration**:
- Print ordering (sizes, framing options)
- Stripe payment integration
- Order management dashboard
- Shipping tracking
- Customer communication

**Advanced Search**:
- Full-text search across titles/descriptions/tags
- EXIF-based filtering (camera model, focal length, aperture ranges)
- Date range queries
- GPS-based location search

**Bulk Operations**:
- Batch tag editing
- Bulk publish/unpublish with filters
- Export metadata to CSV/JSON
- Import from Lightroom/Adobe Bridge

**Collections & Albums**:
- Create curated collections
- Drag-and-drop ordering
- Featured collections on homepage
- Public/private collections

**Social Sharing**:
- One-click sharing to Instagram, Twitter, Facebook
- Auto-generate social media captions
- Track social media engagement

**API for Third-Party Apps**:
- REST API with API keys
- OAuth integration
- Mobile app support
- Webhook notifications

---

## Technology Evolution

### Current Stack (Sprint 3)
- **Backend**: FastAPI, SQLite, Pillow, piexif, Anthropic Claude API
- **Frontend**: Vanilla HTML/CSS/JavaScript, Jinja2 templates
- **Infrastructure**: Docker Compose, Caddy, Restic backups

### Planned Additions (Sprint 4-5)
- **Authentication**: JWT tokens, bcrypt, python-jose, passlib
- **AI**: Enhanced Claude integration for chatbot

### Future Considerations (Sprint 6+)
- **Caching**: Redis for analytics and frequently accessed data
- **Metrics**: Prometheus + Grafana for monitoring
- **Database**: Migrate to PostgreSQL if scaling beyond single server
- **Storage**: CDN integration (Cloudflare, AWS CloudFront)
- **Payments**: Stripe for e-commerce

---

## Success Metrics

### User Experience
- **Upload Success Rate**: >95% (with graceful degradation for errors)
- **AI Analysis Quality**: Manual review confirms 80%+ accuracy
- **Page Load Time**: <2 seconds for gallery pages
- **Mobile Responsiveness**: Works flawlessly on all device sizes

### Technical Quality
- **Uptime**: >99.5% (production environment)
- **Error Rate**: <1% of API requests fail
- **Database Performance**: Queries <100ms average
- **Image Optimization**: WebP variants 25-35% smaller than JPEG

### Security & Privacy
- **Authentication**: 100% of admin/manage routes protected
- **User Isolation**: Zero cross-user data leaks
- **HTTPS**: 100% of traffic encrypted
- **Rate Limiting**: Prevents abuse and API cost overruns

---

## Risk Management

### Technical Risks

**Risk**: SQLite performance degradation with large image counts
- **Mitigation**: Monitor query performance, add indexes, migrate to PostgreSQL if needed
- **Trigger**: >10,000 images or >100ms average query time

**Risk**: Claude API rate limits or cost overruns
- **Mitigation**: Implement caching, rate limiting, fallback to basic metadata
- **Trigger**: Monthly cost >$X or rate limit errors

**Risk**: Storage space exhaustion
- **Mitigation**: Monitor disk usage, implement cleanup for deleted images, consider object storage (S3)
- **Trigger**: <10GB free space

### Security Risks

**Risk**: Authentication bypass or session hijacking
- **Mitigation**: httpOnly cookies, secure JWT signing, regular security audits
- **Response**: Immediate patching, forced re-authentication for all users

**Risk**: User data leak between photographers
- **Mitigation**: Comprehensive testing of user isolation, database-level filtering
- **Response**: Incident response plan, user notification, bug bounty consideration

**Risk**: API abuse (DoS, scraping, excessive uploads)
- **Mitigation**: Rate limiting, CAPTCHA for public endpoints, monitoring
- **Response**: Block abusive IPs, implement stricter rate limits

---

## Release Strategy

### Version Numbering
- **Major** (X.0.0): Breaking changes, major feature additions
- **Minor** (x.Y.0): New features, backward-compatible
- **Patch** (x.y.Z): Bug fixes, security patches

### Release Cycle
- **Development**: Continuous integration in `/opt/dev/`
- **Testing**: Playwright tests + manual QA before merge
- **Staging**: Testing environment (currently port 8080)
- **Production**: Deploy to `/opt/prod/` after approval
- **Versioning**: Git tags for releases (e.g., `v2.1.0`)

### Rollback Plan
- Git revert to previous tagged release
- Database backups via Restic (restore within 15 minutes)
- Docker image rollback if needed

---

## Open Questions & Decisions Needed

### Sprint 4 Decisions
- ✅ Dashboard URL for photographers: **Decided - `/manage`**
- ✅ User creation process: **Decided - Admin-only, prepopulate Adrian and Liam**
- ✅ Chatbot implementation timeline: **Decided - Hold for Sprint 5, document and plan now**
- ✅ When to start Sprint 4: **Decided - After Sprint 3 complete**

### Sprint 5 Decisions (Future)
- [ ] Chatbot rate limiting: 20 messages/hour sufficient?
- [ ] Conversation retention: Keep forever or delete after 30 days?
- [ ] Tool function scope: Which additional functions to add?
- [ ] Confirmation UX: Modal popup or inline chat confirmation?

### Sprint 6+ Decisions (Future)
- [ ] Analytics privacy: Track IP addresses or anonymize?
- [ ] E-commerce scope: Prints only or digital downloads too?
- [ ] PostgreSQL migration trigger: What image count threshold?

---

## Feedback & Iteration

This roadmap is a living document. After each sprint:
1. **Retrospective**: What went well? What could be improved?
2. **User Feedback**: Test with Adrian and Liam, gather input
3. **Roadmap Update**: Adjust priorities based on learnings
4. **CHANGELOG Update**: Document what shipped

**Last Retrospective**: Sprint 3 (Error Handling & Logging)
- ✅ Structured errors dramatically improved debugging
- ✅ JSON logs enable AI-assisted diagnosis
- ✅ Graceful degradation prevents upload failures
- 🔄 Consider adding retry logic for transient Claude API failures
- 🔄 Add more context to logs (request_id for tracing)

---

**Document Owner**: Adrian Hensler
**Last Updated**: 2025-11-02
**Next Review**: After Sprint 4 completion
