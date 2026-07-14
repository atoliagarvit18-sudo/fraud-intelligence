"""
app/api/routes/health.py

GET /health — liveness and readiness probe.
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter
from loguru import logger

from app.api.schemas import HealthResponse

router = APIRouter()

_START_TIME = time.monotonic()
_VERSION    = "2.0.0"


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"],
)
def health_check() -> HealthResponse:
    """
    Returns the current health status of Agent 2.
    Checks MongoDB connectivity as part of the response.
    """
    db_status = "connected"

    try:
        from app.database.mongo import client
        client.admin.command("ping")
    except Exception as e:
        logger.warning("Health check: DB ping failed — {}", e)
        db_status = "error"

    overall = "ok" if db_status == "connected" else "degraded"

    return HealthResponse(
        status=overall,
        version=_VERSION,
        timestamp=datetime.now(tz=timezone.utc),
        database=db_status,
        uptime_seconds=round(time.monotonic() - _START_TIME, 2),
    )
