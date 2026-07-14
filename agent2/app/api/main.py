"""
app/api/main.py

FastAPI application factory for Agent 2.

Run with:
    uvicorn app.api.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.routes import actions, clusters, events, health, posts, stats

# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown hooks)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Agent 2 API starting up.")
    # Verify DB is reachable on startup (will raise on failure)
    from app.database.mongo import client
    client.admin.command("ping")
    logger.success("Startup: MongoDB reachable.")
    yield
    logger.info("Agent 2 API shutting down.")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    application = FastAPI(
        title       = "Agent 2 — Fraud Intelligence API",
        description = (
            "Public intelligence engine for the Fraud Campaign Intelligence Platform.\n\n"
            "Collects posts from Reddit, Telegram, and complaint sites, classifies them "
            "with Groq LLM, clusters them into campaigns, and generates threat events."
        ),
        version     = "2.0.0",
        docs_url    = "/docs",
        redoc_url   = "/redoc",
        lifespan    = lifespan,
    )

    # ---- CORS ---------------------------------------------------------------
    application.add_middleware(
        CORSMiddleware,
        allow_origins  = ["*"],     # tighten for production
        allow_methods  = ["*"],
        allow_headers  = ["*"],
    )

    # ---- Global exception handler -------------------------------------------
    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error("Unhandled exception on {}: {}", request.url.path, exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )

    # ---- Routers ------------------------------------------------------------
    application.include_router(health.router)
    application.include_router(stats.router)
    application.include_router(posts.router)
    application.include_router(clusters.router)
    application.include_router(events.router)
    application.include_router(actions.router)

    return application


app = create_app()
