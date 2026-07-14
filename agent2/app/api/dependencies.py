"""
app/api/dependencies.py

Shared FastAPI dependency functions.
Inject these into route handlers with Depends().
"""

from typing import Annotated

from fastapi import Query


def pagination(
    page:  Annotated[int, Query(ge=1,   description="Page number (1-based)")] = 1,
    limit: Annotated[int, Query(ge=1, le=500, description="Items per page")] = 20,
) -> dict[str, int]:
    """Return skip/limit for MongoDB queries."""
    return {
        "page":  page,
        "limit": limit,
        "skip":  (page - 1) * limit,
    }


def source_filter(
    source: Annotated[
        str | None,
        Query(description="Filter by source: telegram | reddit | complaint_site"),
    ] = None,
) -> str | None:
    return source


def severity_filter(
    severity: Annotated[
        str | None,
        Query(description="Filter by severity: low | medium | high | critical"),
    ] = None,
) -> str | None:
    return severity
