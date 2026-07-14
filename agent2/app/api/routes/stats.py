"""
app/api/routes/stats.py

GET /stats — aggregated intelligence dashboard statistics.
"""

from datetime import datetime, timezone

from fastapi import APIRouter
from loguru import logger

from app.api.schemas import CollectionStats, StatsResponse
from app.config.constants import CLUSTERS, EVENTS, PROCESSED_POSTS, RAW_POSTS
from app.database.mongo import get_collection

router = APIRouter()


@router.get(
    "/stats",
    response_model=StatsResponse,
    summary="Dashboard statistics",
    tags=["Intelligence"],
)
def get_stats() -> StatsResponse:
    """
    Returns:
    - Document counts per collection
    - Event breakdown by severity
    - Top 5 scam types by frequency
    """
    # ---- Collection counts ------------------------------------------------
    raw_col       = get_collection(RAW_POSTS)
    processed_col = get_collection(PROCESSED_POSTS)
    clusters_col  = get_collection(CLUSTERS)
    events_col    = get_collection(EVENTS)

    counts = CollectionStats(
        raw_posts       = raw_col.count_documents({}),
        processed_posts = processed_col.count_documents({}),
        clusters        = clusters_col.count_documents({}),
        events          = events_col.count_documents({}),
    )

    # ---- Events by severity -----------------------------------------------
    severity_pipeline = [
        {"$group": {"_id": "$severity", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    events_by_severity: dict[str, int] = {
        doc["_id"]: doc["count"]
        for doc in events_col.aggregate(severity_pipeline)
        if doc.get("_id")
    }

    # ---- Top scam types ---------------------------------------------------
    scam_pipeline = [
        {"$group": {"_id": "$scam_type", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 5},
    ]
    top_scam_types = [
        {"scam_type": doc["_id"], "count": doc["count"]}
        for doc in clusters_col.aggregate(scam_pipeline)
        if doc.get("_id")
    ]

    logger.debug("GET /stats: returned successfully.")

    return StatsResponse(
        collections        = counts,
        events_by_severity = events_by_severity,
        top_scam_types     = top_scam_types,
        timestamp          = datetime.now(tz=timezone.utc),
    )
