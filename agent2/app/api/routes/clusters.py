"""
app/api/routes/clusters.py

GET /clusters — paginated cluster listing with optional severity filter.
"""

from fastapi import APIRouter, Depends
from loguru import logger

from app.api.dependencies import pagination, severity_filter
from app.api.schemas import ClusterItem, ClustersResponse
from app.config.constants import CLUSTERS
from app.database.mongo import get_collection

router = APIRouter()


@router.get(
    "/clusters",
    response_model=ClustersResponse,
    summary="List detected fraud clusters",
    tags=["Intelligence"],
)
def get_clusters(
    paging:   dict = Depends(pagination),
    severity: str | None = Depends(severity_filter),
) -> ClustersResponse:
    """
    Returns paginated fraud campaign clusters detected by the analysis pipeline.

    Query parameters:
    - **page** — page number (default: 1)
    - **limit** — items per page (default: 20, max: 500)
    - **severity** — filter by severity: `low`, `medium`, `high`, `critical`
    """
    col = get_collection(CLUSTERS)

    query: dict = {}
    if severity:
        query["severity"] = severity

    total = col.count_documents(query)

    cursor = (
        col.find(query, {"_id": 0})
        .sort("post_count", -1)     # highest-volume clusters first
        .skip(paging["skip"])
        .limit(paging["limit"])
    )

    items = []
    for doc in cursor:
        try:
            items.append(ClusterItem(**doc))
        except Exception as e:
            logger.warning("GET /clusters: skipping malformed doc — {}", e)

    logger.debug(
        "GET /clusters: page={} limit={} severity={} → {} items (total {}).",
        paging["page"], paging["limit"], severity, len(items), total,
    )

    return ClustersResponse(
        total = total,
        page  = paging["page"],
        limit = paging["limit"],
        items = items,
    )
