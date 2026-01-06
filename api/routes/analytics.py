"""
Analytics routes for Hensler Photography API

Provides engagement metrics for photographers to track image performance.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from api.routes.auth import get_current_user_for_subdomain, User
from api.database import get_db_connection
from api.logging_config import get_logger
from datetime import datetime, timedelta
import json
from typing import List, Dict, Any, Optional

# Initialize logger
logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


async def _verify_user_access(current_user: User, user_id: int):
    """Verify user can access analytics for given user_id"""
    if current_user.role == "admin":
        return  # Admins can see all analytics

    if current_user.id != user_id:
        raise HTTPException(403, "Not authorized to view these analytics")


def calc_trend(current_value: int, previous_value: int) -> float:
    """Calculate percentage change between two values."""
    if previous_value == 0:
        return 0 if current_value == 0 else 100
    return round(((current_value - previous_value) / previous_value) * 100, 1)


def get_subdomain_filter(subdomain: Optional[str]) -> str:
    """
    Get SQL WHERE clause for filtering events by user and subdomain.

    Filters both image-specific events (by user_id) and site-level events (by referrer subdomain).
    """
    return (
        "((i.user_id = ? AND e.image_id IS NOT NULL) OR (e.image_id IS NULL AND e.referrer LIKE ?))"
    )


def get_photographer_filter(include_photographer: bool = True, photographer_only: bool = False) -> str:
    """
    Get SQL WHERE clause for filtering photographer's own activity.

    Args:
        include_photographer: If True, include photographer's activity. If False, exclude it.
        photographer_only: If True, only show photographer's activity (overrides include_photographer).

    Returns:
        SQL WHERE clause fragment (e.g., "AND e.is_photographer = 0")
    """
    if photographer_only:
        return "AND e.is_photographer = 1"
    elif not include_photographer:
        return "AND e.is_photographer = 0"
    else:
        return ""  # Include both photographer and visitor activity


@router.get("/overview")
async def get_analytics_overview(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    include_photographer: bool = Query(True, description="Include photographer's own activity"),
    photographer_only: bool = Query(False, description="Show only photographer's activity"),
    current_user: User = Depends(get_current_user_for_subdomain),
):
    """
    Get engagement-focused analytics for the photographer dashboard.

    Returns aggregate metrics tied directly to image interactions:
    - Impressions (image_impression events)
    - Engaged viewers (distinct sessions that triggered image events)
    - Gallery clicks (gallery_click events)
    - Lightbox views (lightbox_open events)
    - CTR (clicks / impressions) and view-through rate (views / clicks)
    - Average lightbox dwell time (from lightbox_close metadata)
    - Trends for key metrics vs. previous period

    Filtering:
    - include_photographer=True: Include both visitor and photographer activity (default)
    - include_photographer=False: Exclude photographer's activity (visitors only)
    - photographer_only=True: Show only photographer's activity
    """
    user_id = current_user.id
    subdomain = current_user.subdomain or ""
    subdomain_pattern = f"%{subdomain}.hensler.photography%"
    since = datetime.now() - timedelta(days=days)
    prev_since = since - timedelta(days=days)  # Previous period for comparison
    photographer_filter = get_photographer_filter(include_photographer, photographer_only)

    try:
        async with get_db_connection() as db:
            # Current period metrics
            cursor = await db.execute(
                f"""
                SELECT
                    COUNT(CASE WHEN e.event_type = 'image_impression' THEN 1 END) as impressions,
                    COUNT(CASE WHEN e.event_type = 'gallery_click' THEN 1 END) as clicks,
                    COUNT(CASE WHEN e.event_type = 'lightbox_open' THEN 1 END) as views,
                    COUNT(DISTINCT CASE WHEN e.event_type IN ('image_impression','gallery_click','lightbox_open') THEN e.session_id END) as viewers
                FROM image_events e
                LEFT JOIN images i ON e.image_id = i.id
                WHERE i.user_id = ? AND e.timestamp >= ? {photographer_filter}
                """,
                (user_id, since),
            )

            current = await cursor.fetchone()

            cursor = await db.execute(
                f"""
                SELECT
                    COUNT(CASE WHEN e.event_type = 'image_impression' THEN 1 END) as impressions,
                    COUNT(CASE WHEN e.event_type = 'gallery_click' THEN 1 END) as clicks,
                    COUNT(CASE WHEN e.event_type = 'lightbox_open' THEN 1 END) as views,
                    COUNT(DISTINCT CASE WHEN e.event_type IN ('image_impression','gallery_click','lightbox_open') THEN e.session_id END) as viewers
                FROM image_events e
                LEFT JOIN images i ON e.image_id = i.id
                WHERE i.user_id = ? AND e.timestamp >= ? AND e.timestamp < ? {photographer_filter}
                """,
                (user_id, prev_since, since),
            )

            previous = await cursor.fetchone()

            impressions = current[0] or 0
            clicks = current[1] or 0
            views = current[2] or 0
            viewers = current[3] or 0

            prev_impressions = previous[0] or 0
            prev_clicks = previous[1] or 0
            prev_views = previous[2] or 0
            prev_viewers = previous[3] or 0

            ctr = (clicks / impressions) if impressions > 0 else 0
            view_rate = (views / clicks) if clicks > 0 else 0

            # Average lightbox dwell time
            cursor = await db.execute(
                f"""
                SELECT e.metadata
                FROM image_events e
                LEFT JOIN images i ON e.image_id = i.id
                WHERE i.user_id = ?
                AND e.timestamp >= ?
                AND e.event_type = 'lightbox_close'
                {photographer_filter}
                """,
                (user_id, since),
            )
            duration_rows = await cursor.fetchall()

            durations = []
            for row in duration_rows:
                if not row[0]:
                    continue
                try:
                    metadata = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    duration = metadata.get("duration") if isinstance(metadata, dict) else None
                    if isinstance(duration, (int, float)) and duration >= 0:
                        durations.append(duration)
                except Exception:
                    continue

            avg_duration = round(sum(durations) / len(durations), 1) if durations else 0

            logger.info(
                f"Analytics overview generated for user {user_id}",
                extra={
                    "context": {
                        "user_id": user_id,
                        "days": days,
                        "impressions": impressions,
                        "viewers": viewers,
                    }
                },
            )

            return {
                "impressions": impressions,
                "impressions_trend": calc_trend(impressions, prev_impressions),
                "clicks": clicks,
                "clicks_trend": calc_trend(clicks, prev_clicks),
                "views": views,
                "views_trend": calc_trend(views, prev_views),
                "viewers": viewers,
                "visitors": viewers,  # Alias for dashboard compatibility
                "viewers_trend": calc_trend(viewers, prev_viewers),
                "visitors_trend": calc_trend(viewers, prev_viewers),  # Alias for dashboard
                "ctr": round(ctr, 3),
                "click_rate": round(ctr, 3),  # Alias for dashboard compatibility
                "view_rate": round(view_rate, 3),
                "avg_duration": avg_duration,
                "period_days": days,
            }

    except Exception as e:
        logger.error(f"Failed to get analytics overview: {str(e)}", exc_info=e)
        raise HTTPException(500, "Failed to retrieve analytics data")


@router.get("/highlights")
async def get_analytics_highlights(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    current_user: User = Depends(get_current_user_for_subdomain),
):
    """
    Provide a concise, fact-based performance summary.

    Combines overview metrics with standout images, leading category, and
    session skew to keep insights grounded in collected data.
    """
    user_id = current_user.id
    subdomain = current_user.subdomain or ""
    subdomain_pattern = f"%{subdomain}.hensler.photography%"
    since = datetime.now() - timedelta(days=days)
    prev_since = since - timedelta(days=days)

    try:
        async with get_db_connection() as db:
            # Current period overview
            cursor = await db.execute(
                """
                SELECT
                    COUNT(CASE WHEN e.event_type = 'image_impression' THEN 1 END) as impressions,
                    COUNT(CASE WHEN e.event_type = 'gallery_click' THEN 1 END) as clicks,
                    COUNT(CASE WHEN e.event_type = 'lightbox_open' THEN 1 END) as views,
                    COUNT(DISTINCT CASE WHEN e.event_type IN ('image_impression','gallery_click','lightbox_open') THEN e.session_id END) as viewers
                FROM image_events e
                LEFT JOIN images i ON e.image_id = i.id
                WHERE i.user_id = ?
                AND e.timestamp >= ?
                """,
                (user_id, since),
            )

            current = await cursor.fetchone()

            # Previous period for trend context
            cursor = await db.execute(
                """
                SELECT
                    COUNT(CASE WHEN e.event_type = 'image_impression' THEN 1 END) as impressions,
                    COUNT(CASE WHEN e.event_type = 'gallery_click' THEN 1 END) as clicks,
                    COUNT(CASE WHEN e.event_type = 'lightbox_open' THEN 1 END) as views,
                    COUNT(DISTINCT CASE WHEN e.event_type IN ('image_impression','gallery_click','lightbox_open') THEN e.session_id END) as viewers
                FROM image_events e
                LEFT JOIN images i ON e.image_id = i.id
                WHERE i.user_id = ?
                AND e.timestamp >= ? AND e.timestamp < ?
                """,
                (user_id, prev_since, since),
            )

            previous = await cursor.fetchone()

            impressions = current[0] or 0
            clicks = current[1] or 0
            views = current[2] or 0
            viewers = current[3] or 0

            prev_impressions = previous[0] or 0
            prev_clicks = previous[1] or 0
            prev_views = previous[2] or 0
            prev_viewers = previous[3] or 0

            click_rate = (clicks / impressions) if impressions > 0 else 0
            view_rate = (views / clicks) if clicks > 0 else 0

            # Average lightbox dwell time
            cursor = await db.execute(
                """
                SELECT e.metadata
                FROM image_events e
                LEFT JOIN images i ON e.image_id = i.id
                WHERE i.user_id = ?
                AND e.timestamp >= ?
                AND e.event_type = 'lightbox_close'
                """,
                (user_id, since),
            )
            duration_rows = await cursor.fetchall()

            durations = []
            for row in duration_rows:
                if not row[0]:
                    continue
                try:
                    metadata = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                    duration = metadata.get("duration") if isinstance(metadata, dict) else None
                    if isinstance(duration, (int, float)) and duration >= 0:
                        durations.append(duration)
                except Exception:
                    continue

            avg_duration = round(sum(durations) / len(durations), 1) if durations else 0

            overview = {
                "impressions": impressions,
                "impressions_trend": calc_trend(impressions, prev_impressions),
                "viewers": viewers,
                "viewers_trend": calc_trend(viewers, prev_viewers),
                "clicks": clicks,
                "clicks_trend": calc_trend(clicks, prev_clicks),
                "views": views,
                "views_trend": calc_trend(views, prev_views),
                "ctr": round(click_rate, 3),
                "view_rate": round(view_rate, 3),
                "avg_duration": avg_duration,
                "period_days": days,
            }

            logger.info(
                f"Highlights overview calculated for user {user_id}",
                extra={
                    "context": {
                        "user_id": user_id,
                        "days": days,
                        "impressions": impressions,
                        "viewers": viewers,
                        "clicks": clicks,
                    }
                },
            )

            # Top images by clicks to spotlight what people chose to open
            cursor = await db.execute(
                """
                SELECT
                    i.id,
                    i.title,
                    i.category,
                    i.filename,
                    iv.filename as thumbnail_filename,
                    COUNT(CASE WHEN e.event_type = 'image_impression' THEN 1 END) as impressions,
                    COUNT(CASE WHEN e.event_type = 'gallery_click' THEN 1 END) as clicks,
                    COUNT(CASE WHEN e.event_type = 'lightbox_open' THEN 1 END) as views
                FROM images i
                LEFT JOIN image_events e ON i.id = e.image_id AND e.timestamp >= ?
                LEFT JOIN image_variants iv ON i.id = iv.image_id AND iv.format = 'webp' AND iv.size = 'thumbnail'
                WHERE i.user_id = ?
                AND i.published = 1
                GROUP BY i.id
                ORDER BY clicks DESC
                LIMIT 3
                """,
                (since, user_id),
            )

            image_rows = await cursor.fetchall()
            top_images = []
            for row in image_rows:
                impressions = row[5]
                clicks = row[6]
                views = row[7]

                ctr = (clicks / impressions) if impressions > 0 else 0
                view_rate = (views / clicks) if clicks > 0 else 0

                thumbnail_file = row[4] or row[3]

                top_images.append(
                    {
                        "id": row[0],
                        "title": row[1] or "Untitled",
                        "category": row[2],
                        "thumbnail_url": f"/assets/gallery/{thumbnail_file}",
                        "analytics": {
                            "impressions": impressions,
                            "clicks": clicks,
                            "views": views,
                            "ctr": round(ctr, 3),
                            "view_rate": round(view_rate, 3),
                        },
                    }
                )

            # Leading category by impressions with engagement context
            cursor = await db.execute(
                """
                SELECT
                    i.category,
                    COUNT(CASE WHEN e.event_type = 'image_impression' THEN 1 END) as impressions,
                    COUNT(CASE WHEN e.event_type = 'gallery_click' THEN 1 END) as clicks,
                    COUNT(CASE WHEN e.event_type = 'lightbox_open' THEN 1 END) as views
                FROM images i
                LEFT JOIN image_events e ON i.id = e.image_id AND e.timestamp >= ?
                WHERE i.user_id = ?
                AND i.published = 1
                AND i.category IS NOT NULL
                GROUP BY i.category
                ORDER BY impressions DESC
                LIMIT 1
                """,
                (since, user_id),
            )

            category_row = await cursor.fetchone()
            leading_category = None
            if category_row:
                cat_impressions = category_row[1]
                cat_clicks = category_row[2]
                cat_views = category_row[3]

                cat_ctr = (cat_clicks / cat_impressions) if cat_impressions > 0 else 0
                cat_view_rate = (cat_views / cat_clicks) if cat_clicks > 0 else 0

                leading_category = {
                    "category": category_row[0],
                    "impressions": cat_impressions,
                    "clicks": cat_clicks,
                    "views": cat_views,
                    "ctr": round(cat_ctr, 3),
                    "view_rate": round(cat_view_rate, 3),
                }

            # Identify whether a single session is skewing data
            cursor = await db.execute(
                """
                SELECT COUNT(*) FROM image_events e
                LEFT JOIN images i ON e.image_id = i.id
                WHERE i.user_id = ?
                AND e.timestamp >= ?
                AND e.event_type IN ('image_impression', 'gallery_click', 'lightbox_open')
                """,
                (user_id, since),
            )
            total_events = (await cursor.fetchone())[0] or 0

            session_skew = None
            if total_events > 0:
                cursor = await db.execute(
                    """
                    SELECT COALESCE(session_id, 'unknown'), COUNT(*) as count
                    FROM image_events e
                    LEFT JOIN images i ON e.image_id = i.id
                    WHERE i.user_id = ?
                    AND e.timestamp >= ?
                    AND e.event_type IN ('image_impression', 'gallery_click', 'lightbox_open')
                    GROUP BY session_id
                    ORDER BY count DESC
                    LIMIT 1
                    """,
                    (user_id, since),
                )

                top_session = await cursor.fetchone()
                top_count = top_session[1] if top_session else 0

                session_skew = {
                    "top_session_share": round(top_count / total_events, 3) if total_events else 0,
                    "total_events": total_events,
                }

            insights = []
            if impressions > 0:
                insights.append(
                    f"{impressions} impressions in the last {days} days ({overview['impressions_trend']}% vs prior) with a {round(click_rate * 100, 1)}% CTR and {round(view_rate * 100, 1)}% view-through."
                )

            if top_images:
                hero = top_images[0]
                insights.append(
                    f"Top image: '{hero['title']}' earned {hero['analytics']['impressions']} impressions, {hero['analytics']['clicks']} clicks, and {hero['analytics']['views']} lightbox views."
                )

            if leading_category:
                insights.append(
                    f"Leading theme: {leading_category['category']} with {leading_category['impressions']} impressions, {round(leading_category['ctr'] * 100, 1)}% CTR, and {round(leading_category['view_rate'] * 100, 1)}% view-through."
                )

            if session_skew and session_skew["top_session_share"] >= 0.5:
                insights.append(
                    f"Traffic is concentrated: your busiest session accounts for {round(session_skew['top_session_share'] * 100, 1)}% of events."
                )

            if avg_duration > 0:
                insights.append(
                    f"Average lightbox dwell time: {avg_duration}s before visitors close the image."
                )

            return {
                "period_days": days,
                "overview": overview,
                "top_images": top_images,
                "leading_category": leading_category,
                "session_skew": session_skew,
                "insights": insights,
            }

    except Exception as e:
        logger.error(f"Failed to build analytics highlights: {str(e)}", exc_info=e)
        raise HTTPException(500, "Failed to retrieve analytics highlights")


@router.get("/timeline")
async def get_analytics_timeline(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    metric: str = Query(
        "impressions", regex="^(impressions|clicks|views)$", description="Metric to chart"
    ),
    include_photographer: bool = Query(True, description="Include photographer's own activity"),
    photographer_only: bool = Query(False, description="Show only photographer's activity"),
    current_user: User = Depends(get_current_user_for_subdomain),
):
    """
    Get time-series analytics data for charts.

    Returns daily counts for specified metric (views, clicks, or lightbox_opens).

    Filtering:
    - include_photographer=True: Include both visitor and photographer activity (default)
    - include_photographer=False: Exclude photographer's activity (visitors only)
    - photographer_only=True: Show only photographer's activity
    """
    user_id = current_user.id
    subdomain = current_user.subdomain or ""
    subdomain_pattern = f"%{subdomain}.hensler.photography%"
    since = datetime.now() - timedelta(days=days)
    photographer_filter = get_photographer_filter(include_photographer, photographer_only)

    # Map metric to event type
    event_type_map = {
        "impressions": "image_impression",
        "clicks": "gallery_click",
        "views": "lightbox_open",
    }
    event_type = event_type_map[metric]

    try:
        async with get_db_connection() as db:
            cursor = await db.execute(
                f"""
                SELECT
                    DATE(e.timestamp) as date,
                    COUNT(*) as count
                FROM image_events e
                LEFT JOIN images i ON e.image_id = i.id
                WHERE i.user_id = ?
                AND e.event_type = ?
                AND e.timestamp >= ?
                {photographer_filter}
                GROUP BY DATE(e.timestamp)
                ORDER BY date ASC
            """,
                (user_id, event_type, since),
            )

            rows = await cursor.fetchall()

            # Fill in missing days with zero counts
            timeline = []
            current_date = since.date()
            end_date = datetime.now().date()

            # Create lookup dict from query results
            data_by_date = {row[0]: row[1] for row in rows}

            while current_date <= end_date:
                date_str = current_date.isoformat()
                count = data_by_date.get(date_str, 0)
                timeline.append({"date": date_str, "count": count})
                current_date += timedelta(days=1)

            return {"metric": metric, "period_days": days, "data": timeline}

    except Exception as e:
        logger.error(f"Failed to get analytics timeline: {str(e)}", exc_info=e)
        raise HTTPException(500, "Failed to retrieve timeline data")


@router.get("/recent-engagement")
async def get_recent_engagement(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    limit: int = Query(20, ge=1, le=100, description="Number of recent events to return"),
    offset: int = Query(0, ge=0, le=1000, description="Number of events to skip for pagination"),
    current_user: User = Depends(get_current_user_for_subdomain),
):
    """
    Return the most recent engagement events that involved an image click or lightbox view.

    Helps photographers see what visitors opened most recently without guessing.
    """

    user_id = current_user.id
    subdomain = current_user.subdomain or ""
    subdomain_pattern = f"%{subdomain}.hensler.photography%"
    since = datetime.now() - timedelta(days=days)

    try:
        async with get_db_connection() as db:
            fetch_limit = limit + 1  # Grab one extra to detect remaining pages

            cursor = await db.execute(
                """
                SELECT
                    e.event_type,
                    e.timestamp,
                    e.referrer,
                    e.session_id,
                    i.id,
                    i.title,
                    i.category,
                    i.filename,
                    iv.filename as thumbnail_filename
                FROM image_events e
                LEFT JOIN images i ON e.image_id = i.id
                LEFT JOIN image_variants iv ON i.id = iv.image_id AND iv.format = 'webp' AND iv.size = 'thumbnail'
                WHERE ((i.user_id = ? AND e.image_id IS NOT NULL) OR (e.image_id IS NULL AND e.referrer LIKE ?))
                AND e.timestamp >= ?
                AND e.event_type IN ('gallery_click', 'lightbox_open')
                ORDER BY e.timestamp DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, subdomain_pattern, since, fetch_limit, offset),
            )

            rows = await cursor.fetchall()

            events: List[Dict[str, Any]] = []
            for row in rows[:limit]:
                image_id = row[4]
                if image_id is None:
                    continue

                thumbnail_file = row[8] or row[7]

                events.append(
                    {
                        "event_type": row[0],
                        "timestamp": row[1],
                        "referrer": row[2] or "Direct / None",
                        "session_id": row[3],
                        "image": {
                            "id": image_id,
                            "title": row[5] or "Untitled",
                            "category": row[6],
                            "thumbnail_url": f"/assets/gallery/{thumbnail_file}",
                        },
                    }
                )

            has_more = len(rows) > limit

            return {"period_days": days, "events": events, "has_more": has_more}

    except Exception as e:
        logger.error(f"Failed to get recent engagement: {str(e)}", exc_info=e)
        raise HTTPException(500, "Failed to retrieve recent engagement")


@router.get("/top-images")
async def get_top_images(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    limit: int = Query(10, ge=1, le=50, description="Number of top images to return"),
    metric: str = Query(
        "impressions", regex="^(impressions|clicks|views)$", description="Metric to rank by"
    ),
    current_user: User = Depends(get_current_user_for_subdomain),
):
    """
    Get top performing images ranked by engagement.

    Returns images with highest impressions, clicks, or lightbox views.
    Impressions = times image entered viewport (50% visible)
    Clicks = gallery grid clicks
    Views = lightbox opens (full-screen views)
    """
    user_id = current_user.id
    subdomain = current_user.subdomain or ""
    subdomain_pattern = f"%{subdomain}.hensler.photography%"
    since = datetime.now() - timedelta(days=days)

    # Map metric to event type
    event_type_map = {
        "impressions": "image_impression",
        "clicks": "gallery_click",
        "views": "lightbox_open",
    }
    event_type = event_type_map[metric]

    try:
        async with get_db_connection() as db:
            # Get top images with engagement metrics
            # Use thumbnail variant (400px WebP) instead of full-size original
            cursor = await db.execute(
                """
                SELECT
                    i.id,
                    i.title,
                    i.caption,
                    i.category,
                    i.filename,
                    iv.filename as thumbnail_filename,
                    COUNT(CASE WHEN e.event_type = 'image_impression' THEN 1 END) as impressions,
                    COUNT(CASE WHEN e.event_type = 'gallery_click' THEN 1 END) as clicks,
                    COUNT(CASE WHEN e.event_type = 'lightbox_open' THEN 1 END) as views
                FROM images i
                LEFT JOIN image_events e ON i.id = e.image_id AND e.timestamp >= ?
                LEFT JOIN image_variants iv ON i.id = iv.image_id
                    AND iv.format = 'webp'
                    AND iv.size = 'thumbnail'
                WHERE i.user_id = ?
                AND i.published = 1
                GROUP BY i.id
                ORDER BY COUNT(CASE WHEN e.event_type = ? THEN 1 END) DESC
                LIMIT ?
            """,
                (since, user_id, event_type, limit),
            )

            rows = await cursor.fetchall()

            # Get average view duration for each image (from lightbox_close events)
            top_images = []
            for row in rows:
                # Updated indices after adding thumbnail_filename column
                impressions = row[6]
                clicks = row[7]
                views = row[8]

                # Calculate CTR (clicks / impressions)
                ctr = (clicks / impressions) if impressions > 0 else 0

                # Calculate view rate (views / clicks)
                view_rate = (views / clicks) if clicks > 0 else 0

                # Get average duration from metadata
                duration_cursor = await db.execute(
                    """
                    SELECT metadata FROM image_events
                    WHERE image_id = ?
                    AND event_type = 'lightbox_close'
                    AND timestamp >= ?
                    AND metadata IS NOT NULL
                """,
                    (row[0], since),
                )

                duration_rows = await duration_cursor.fetchall()
                durations = []
                for dr in duration_rows:
                    try:
                        import json

                        meta = json.loads(dr[0])
                        if "duration" in meta:
                            durations.append(meta["duration"])
                    except (json.JSONDecodeError, TypeError, KeyError):
                        pass

                avg_duration = sum(durations) / len(durations) if durations else 0

                # Use thumbnail variant (400px WebP) if available, fallback to original
                thumbnail_file = row[5] or row[4]  # thumbnail_filename or original filename

                top_images.append(
                    {
                        "id": row[0],
                        "title": row[1] or "Untitled",
                        "caption": row[2],
                        "category": row[3],
                        "thumbnail_url": f"/assets/gallery/{thumbnail_file}",
                        "analytics": {
                            "impressions": impressions,
                            "clicks": clicks,
                            "views": views,
                            "ctr": round(ctr, 3),
                            "view_rate": round(view_rate, 3),
                            "avg_duration": round(avg_duration, 1),
                        },
                    }
                )

            return {"metric": metric, "period_days": days, "images": top_images}

    except Exception as e:
        logger.error(f"Failed to get top images: {str(e)}", exc_info=e)
        raise HTTPException(500, "Failed to retrieve top images")


@router.get("/referrers")
async def get_referrer_breakdown(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    limit: int = Query(10, ge=1, le=50, description="Number of top referrers to return"),
    current_user: User = Depends(get_current_user_for_subdomain),
):
    """
    Get traffic source breakdown (referrers).

    Returns top referrer URLs and their counts.
    """
    user_id = current_user.id
    subdomain = current_user.subdomain or ""
    subdomain_pattern = f"%{subdomain}.hensler.photography%"
    since = datetime.now() - timedelta(days=days)

    try:
        async with get_db_connection() as db:
            cursor = await db.execute(
                """
                SELECT
                    CASE
                        WHEN e.referrer IS NULL OR e.referrer = '' THEN 'Direct / None'
                        ELSE e.referrer
                    END as referrer_group,
                    COUNT(*) as count
                FROM image_events e
                LEFT JOIN images i ON e.image_id = i.id
                WHERE ((i.user_id = ? AND e.image_id IS NOT NULL) OR (e.image_id IS NULL AND e.referrer LIKE ?))
                AND e.timestamp >= ?
                GROUP BY referrer_group
                ORDER BY count DESC
                LIMIT ?
            """,
                (user_id, subdomain_pattern, since, limit),
            )

            rows = await cursor.fetchall()

            # Calculate total for percentage
            total = sum(row[1] for row in rows)

            referrers = []
            for row in rows:
                count = row[1]
                percentage = (count / total * 100) if total > 0 else 0

                referrers.append(
                    {"referrer": row[0], "count": count, "percentage": round(percentage, 1)}
                )

            return {"period_days": days, "total_events": total, "referrers": referrers}

    except Exception as e:
        logger.error(f"Failed to get referrer breakdown: {str(e)}", exc_info=e)
        raise HTTPException(500, "Failed to retrieve referrer data")


@router.get("/category-performance")
async def get_category_performance(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    current_user: User = Depends(get_current_user_for_subdomain),
):
    """
    Get engagement metrics broken down by image category.

    Returns performance metrics for each category (nature, wildlife, portrait, etc.)
    """
    user_id = current_user.id
    subdomain = current_user.subdomain or ""
    subdomain_pattern = f"%{subdomain}.hensler.photography%"
    since = datetime.now() - timedelta(days=days)

    try:
        async with get_db_connection() as db:
            cursor = await db.execute(
                """
                SELECT
                    i.category,
                    COUNT(DISTINCT i.id) as image_count,
                    COUNT(CASE WHEN e.event_type = 'image_impression' THEN 1 END) as impressions,
                    COUNT(CASE WHEN e.event_type = 'gallery_click' THEN 1 END) as clicks,
                    COUNT(CASE WHEN e.event_type = 'lightbox_open' THEN 1 END) as views
                FROM images i
                LEFT JOIN image_events e ON i.id = e.image_id AND e.timestamp >= ?
                WHERE i.user_id = ?
                AND i.published = 1
                AND i.category IS NOT NULL
                GROUP BY i.category
                ORDER BY impressions DESC
            """,
                (since, user_id),
            )

            rows = await cursor.fetchall()

            categories = []
            for row in rows:
                impressions = row[2]
                clicks = row[3]
                views = row[4]

                # Calculate metrics
                ctr = (clicks / impressions) if impressions > 0 else 0
                view_rate = (views / clicks) if clicks > 0 else 0

                categories.append(
                    {
                        "category": row[0],
                        "image_count": row[1],
                        "impressions": impressions,
                        "clicks": clicks,
                        "views": views,
                        "ctr": round(ctr, 3),
                        "view_rate": round(view_rate, 3),
                    }
                )

            return {"period_days": days, "categories": categories}

    except Exception as e:
        logger.error(f"Failed to get category performance: {str(e)}", exc_info=e)
        raise HTTPException(500, "Failed to retrieve category data")


@router.get("/scroll-depth")
async def get_scroll_depth(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    current_user: User = Depends(get_current_user_for_subdomain),
):
    """
    Get scroll depth distribution.

    Returns how many sessions reached each scroll milestone (25%, 50%, 75%, 100%).
    """
    user_id = current_user.id
    subdomain = current_user.subdomain or ""
    subdomain_pattern = f"%{subdomain}.hensler.photography%"
    since = datetime.now() - timedelta(days=days)

    try:
        async with get_db_connection() as db:
            cursor = await db.execute(
                """
                SELECT metadata FROM image_events e
                LEFT JOIN images i ON e.image_id = i.id
                WHERE ((i.user_id = ? AND e.image_id IS NOT NULL) OR (e.image_id IS NULL AND e.referrer LIKE ?))
                AND e.event_type = 'scroll_depth'
                AND e.timestamp >= ?
            """,
                (user_id, subdomain_pattern, since),
            )

            rows = await cursor.fetchall()

            # Parse metadata to extract depth values
            depth_counts = {25: 0, 50: 0, 75: 0, 100: 0}
            for row in rows:
                if row[0]:
                    try:
                        import json

                        meta = json.loads(row[0])
                        depth = meta.get("depth")
                        if depth in depth_counts:
                            depth_counts[depth] += 1
                    except (json.JSONDecodeError, TypeError, KeyError):
                        pass

            # Get total sessions for percentage calculation
            cursor = await db.execute(
                """
                SELECT COUNT(DISTINCT session_id) FROM image_events e
                LEFT JOIN images i ON e.image_id = i.id
                WHERE ((i.user_id = ? AND e.image_id IS NOT NULL) OR (e.image_id IS NULL AND e.referrer LIKE ?))
                AND e.timestamp >= ?
            """,
                (user_id, subdomain_pattern, since),
            )

            total_sessions = (await cursor.fetchone())[0]

            milestones = []
            for depth, count in sorted(depth_counts.items()):
                percentage = (count / total_sessions * 100) if total_sessions > 0 else 0
                milestones.append(
                    {"depth": depth, "sessions": count, "percentage": round(percentage, 1)}
                )

            return {"period_days": days, "total_sessions": total_sessions, "milestones": milestones}

    except Exception as e:
        logger.error(f"Failed to get scroll depth: {str(e)}", exc_info=e)
        raise HTTPException(500, "Failed to retrieve scroll depth data")


@router.get("/image/{image_id}")
async def get_image_analytics(
    image_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    current_user: User = Depends(get_current_user_for_subdomain),
):
    """
    Get detailed analytics for a specific image.

    Returns engagement metrics and timeline for single image.
    """
    user_id = current_user.id
    subdomain = current_user.subdomain or ""
    subdomain_pattern = f"%{subdomain}.hensler.photography%"
    since = datetime.now() - timedelta(days=days)

    try:
        async with get_db_connection() as db:
            # Verify image ownership
            cursor = await db.execute("SELECT user_id FROM images WHERE id = ?", (image_id,))
            row = await cursor.fetchone()

            if not row:
                raise HTTPException(404, "Image not found")

            if row[0] != user_id and current_user.role != "admin":
                raise HTTPException(403, "Not authorized to view this image's analytics")

            # Get aggregate metrics
            cursor = await db.execute(
                """
                SELECT
                    COUNT(CASE WHEN event_type = 'image_impression' THEN 1 END) as impressions,
                    COUNT(CASE WHEN event_type = 'gallery_click' THEN 1 END) as clicks,
                    COUNT(CASE WHEN event_type = 'lightbox_open' THEN 1 END) as views,
                    COUNT(DISTINCT CASE WHEN event_type IN ('image_impression','gallery_click','lightbox_open') THEN session_id END) as unique_visitors,
                    MIN(timestamp) as first_view,
                    MAX(timestamp) as last_view
                FROM image_events
                WHERE image_id = ?
                AND timestamp >= ?
            """,
                (image_id, since),
            )

            metrics = await cursor.fetchone()

            impressions = metrics[0] or 0
            clicks = metrics[1] or 0
            views = metrics[2] or 0
            click_rate = (clicks / impressions) if impressions > 0 else 0

            return {
                "image_id": image_id,
                "period_days": days,
                "impressions": impressions,
                "clicks": clicks,
                "views": views,
                "unique_visitors": metrics[3] or 0,
                "ctr": round(click_rate, 3),
                "view_rate": round((views / clicks), 3) if clicks > 0 else 0,
                "first_view": metrics[4],
                "last_view": metrics[5],
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get image analytics: {str(e)}", exc_info=e)
        raise HTTPException(500, "Failed to retrieve image analytics")
