"""
app/api/schemas.py

Pydantic request and response models for all API endpoints.
No business logic. No database access.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class StatusResponse(BaseModel):
    status: str
    message: str


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str                         # "ok" | "degraded"
    version: str
    timestamp: datetime
    database: str                       # "connected" | "error"
    uptime_seconds: float


# ---------------------------------------------------------------------------
# GET /stats
# ---------------------------------------------------------------------------

class CollectionStats(BaseModel):
    raw_posts:       int
    processed_posts: int
    clusters:        int
    events:          int


class StatsResponse(BaseModel):
    collections: CollectionStats
    events_by_severity: dict[str, int]
    top_scam_types:     list[dict[str, Any]]
    timestamp:          datetime


# ---------------------------------------------------------------------------
# GET /posts
# ---------------------------------------------------------------------------

class PostItem(BaseModel):
    source_id:    str
    source:       str
    title:        Optional[str]
    text:         str
    author:       Optional[str]
    timestamp:    datetime
    url:          Optional[str]
    platform:     Optional[str]
    language:     Optional[str]
    collected_at: Optional[datetime]


class PostsResponse(BaseModel):
    total:  int
    page:   int
    limit:  int
    items:  list[PostItem]


# ---------------------------------------------------------------------------
# GET /clusters
# ---------------------------------------------------------------------------

class ClusterItem(BaseModel):
    cluster_id:           int
    scam_type:            str
    severity:             Optional[str]
    post_count:           int
    avg_confidence:       float
    campaign_score:       Optional[float]
    weighted_confidence:  Optional[float]
    sources:              list[str]
    platforms:            list[str]
    is_multi_source:      Optional[bool]
    earliest_post:        Optional[datetime]
    latest_post:          Optional[datetime]
    status:               Optional[str]
    created_at:           Optional[datetime]


class ClustersResponse(BaseModel):
    total:  int
    page:   int
    limit:  int
    items:  list[ClusterItem]


# ---------------------------------------------------------------------------
# GET /events
# ---------------------------------------------------------------------------

class EventItem(BaseModel):
    event_type:           str
    severity:             str
    cluster_id:           int
    scam_type:            str
    campaign_score:       float
    weighted_confidence:  float
    post_count:           int
    sources:              list[str]
    platforms:            list[str]
    is_multi_source:      bool
    earliest_post:        Optional[datetime]
    latest_post:          Optional[datetime]
    occurred_at:          datetime
    status:               str


class EventsResponse(BaseModel):
    total:  int
    page:   int
    limit:  int
    items:  list[EventItem]


# ---------------------------------------------------------------------------
# POST /collect
# ---------------------------------------------------------------------------

class CollectRequest(BaseModel):
    source: str = Field(
        ...,
        description="One of: 'telegram', 'reddit', 'complaints'",
        examples=["reddit"],
    )


class CollectResponse(BaseModel):
    source:   str
    inserted: int
    message:  str


# ---------------------------------------------------------------------------
# POST /classify
# ---------------------------------------------------------------------------

class ClassifyRequest(BaseModel):
    text:     str  = Field(..., min_length=10, description="Raw post text to classify")
    source:   str  = Field(default="", description="Origin source label")
    platform: str  = Field(default="", description="Sub-platform or channel name")


class EntityResult(BaseModel):
    platforms: list[str] = []
    amounts:   list[str] = []
    locations: list[str] = []
    names:     list[str] = []


class ClassifyResponse(BaseModel):
    is_fraud:   bool
    scam_type:  str
    confidence: float
    summary:    str
    entities:   EntityResult
    error:      Optional[str] = None


# ---------------------------------------------------------------------------
# POST /cluster
# ---------------------------------------------------------------------------

class ClusterRequest(BaseModel):
    batch_size: int = Field(
        default=200,
        ge=1,
        le=1000,
        description="Number of unprocessed posts to pull for this clustering run",
    )


class ClusterResponse(BaseModel):
    posts_processed:   int
    clusters_found:    int
    events_generated:  int
    message:           str


# ---------------------------------------------------------------------------
# POST /run
# ---------------------------------------------------------------------------

class RunResponse(BaseModel):
    source:    str
    job:       str
    status:    str                  # "started" | "completed" | "error"
    message:   str
    result:    Optional[dict[str, Any]] = None
