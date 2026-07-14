"""
app/api/routes/posts.py

GET /posts — paginated raw post listing with optional source filter.
"""

from fastapi import APIRouter, Depends
from loguru import logger

from app.api.dependencies import pagination, source_filter
from app.api.schemas import PostItem, PostsResponse
from app.config.constants import RAW_POSTS
from app.database.mongo import get_collection

router = APIRouter()


@router.get(
    "/posts",
    response_model=PostsResponse,
    summary="List collected raw posts",
    tags=["Intelligence"],
)
def get_posts(
    paging: dict = Depends(pagination),
    source: str | None = Depends(source_filter),
) -> PostsResponse:
    """
    Returns paginated raw posts collected from all sources.

    Query parameters:
    - **page** — page number (default: 1)
    - **limit** — items per page (default: 20, max: 500)
    - **source** — filter by source: `telegram`, `reddit`, `complaint_site`
    """
    col = get_collection(RAW_POSTS)

    query: dict = {}
    if source:
        query["source"] = source

    total = col.count_documents(query)

    cursor = (
        col.find(query, {"_id": 0})
        .sort("collected_at", -1)
        .skip(paging["skip"])
        .limit(paging["limit"])
    )

    items = []
    for doc in cursor:
        try:
            items.append(PostItem(**doc))
        except Exception as e:
            logger.warning("GET /posts: skipping malformed doc — {}", e)

    logger.debug(
        "GET /posts: page={} limit={} source={} → {} items (total {}).",
        paging["page"], paging["limit"], source, len(items), total,
    )

    return PostsResponse(
        total = total,
        page  = paging["page"],
        limit = paging["limit"],
        items = items,
    )
