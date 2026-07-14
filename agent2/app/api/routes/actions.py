"""
app/api/routes/actions.py

Action endpoints:
  POST /collect   — trigger a collection sweep for one source
  POST /classify  — classify a single text on demand
  POST /cluster   — run one full analysis pipeline batch
  POST /run       — trigger any named job by source+job label
"""

import asyncio

from fastapi import APIRouter, BackgroundTasks, HTTPException
from loguru import logger

from app.api.schemas import (
    ClassifyRequest,
    ClassifyResponse,
    ClusterRequest,
    ClusterResponse,
    CollectRequest,
    CollectResponse,
    EntityResult,
    RunResponse,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# POST /collect
# ---------------------------------------------------------------------------

VALID_SOURCES = {"telegram", "reddit", "complaints"}


@router.post(
    "/collect",
    response_model=CollectResponse,
    summary="Trigger a collection sweep",
    tags=["Actions"],
)
async def collect(request: CollectRequest) -> CollectResponse:
    """
    Trigger an on-demand collection sweep for one source.

    - **telegram** — runs `TelegramCollector.collect_once()`
    - **reddit**   — runs `RedditCollector.collect_once()`
    - **complaints** — runs `ComplaintsCollector.collect_once()`
    """
    src = request.source.lower().strip()

    if src not in VALID_SOURCES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid source '{src}'. Must be one of: {', '.join(sorted(VALID_SOURCES))}",
        )

    logger.info("POST /collect: source='{}'", src)

    try:
        inserted = await _run_collector(src)
        return CollectResponse(
            source=src,
            inserted=inserted,
            message=f"Collection sweep for '{src}' completed. {inserted} new post(s) stored.",
        )
    except Exception as e:
        logger.error("POST /collect: source='{}' failed — {}", src, e)
        raise HTTPException(status_code=500, detail=str(e))


async def _run_collector(source: str) -> int:
    """Dispatch to the correct collector and return the inserted count."""
    loop = asyncio.get_event_loop()

    if source == "telegram":
        from app.collectors.telegram import TelegramCollector
        collector = TelegramCollector()
        await collector.connect()
        count = await collector.collect_once()
        await collector.disconnect()
        return count

    if source == "reddit":
        from app.collectors.reddit import RedditCollector
        collector = RedditCollector()
        return await loop.run_in_executor(None, collector.collect_once)

    if source == "complaints":
        from app.collectors.complaints import ComplaintsCollector
        collector = ComplaintsCollector()
        return await loop.run_in_executor(None, collector.collect_once)

    return 0


# ---------------------------------------------------------------------------
# POST /classify
# ---------------------------------------------------------------------------

@router.post(
    "/classify",
    response_model=ClassifyResponse,
    summary="Classify a text on demand",
    tags=["Actions"],
)
async def classify_text(request: ClassifyRequest) -> ClassifyResponse:
    """
    Run the Groq classifier on a single text string.

    Returns scam type, confidence (0–1), a summary, and extracted entities.
    Useful for testing the classifier or ad-hoc triage of suspect text.
    """
    logger.info("POST /classify: text length={}", len(request.text))

    try:
        from app.services.classifier import PostClassifier
        loop = asyncio.get_event_loop()
        classifier = PostClassifier()

        result = await loop.run_in_executor(
            None,
            lambda: classifier.classify(
                clean_text=request.text,
                source=request.source,
                platform=request.platform,
            ),
        )

        if result.get("error") and not result.get("scam_type"):
            raise HTTPException(status_code=502, detail=result["error"])

        entities_raw = result.get("entities", {})

        return ClassifyResponse(
            is_fraud   = result.get("is_fraud",   False),
            scam_type  = result.get("scam_type",  "other"),
            confidence = result.get("confidence", 0.0),
            summary    = result.get("summary",    ""),
            entities   = EntityResult(
                platforms = entities_raw.get("platforms", []),
                amounts   = entities_raw.get("amounts",   []),
                locations = entities_raw.get("locations", []),
                names     = entities_raw.get("names",     []),
            ),
            error = result.get("error"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("POST /classify: failed — {}", e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# POST /cluster
# ---------------------------------------------------------------------------

@router.post(
    "/cluster",
    response_model=ClusterResponse,
    summary="Run the analysis pipeline",
    tags=["Actions"],
)
async def run_analysis_pipeline(request: ClusterRequest) -> ClusterResponse:
    """
    Run one full batch of the analysis pipeline synchronously:

    1. Fetch up to `batch_size` unprocessed raw posts from MongoDB
    2. Preprocess → Classify (Groq) → Embed → DBSCAN cluster → Score → Events
    3. Persist all results to MongoDB

    Returns a summary of what was produced.
    """
    logger.info("POST /cluster: batch_size={}", request.batch_size)

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: _run_pipeline(request.batch_size),
        )
        return ClusterResponse(**result)

    except Exception as e:
        logger.error("POST /cluster: pipeline failed — {}", e)
        raise HTTPException(status_code=500, detail=str(e))


def _run_pipeline(batch_size: int) -> dict:
    """Inline analysis pipeline — mirrors scheduler.analysis_job."""
    from app.config.constants import RAW_POSTS
    from app.database.mongo import get_collection
    from app.models.raw_post import RawPost
    from app.services.classifier import PostClassifier
    from app.services.clustering import ClusteringService
    from app.services.embeddings import EmbeddingService
    from app.services.preprocessing import TextPreprocessor
    from app.services.threat_engine import ThreatEngine

    raw_col       = get_collection(RAW_POSTS)
    processed_col = get_collection("processed_posts")

    done_ids = set(processed_col.distinct("raw_post_id"))
    raw_docs = list(
        raw_col.find({"source_id": {"$nin": list(done_ids)}}, limit=batch_size)
    )

    if not raw_docs:
        return {
            "posts_processed":  0,
            "clusters_found":   0,
            "events_generated": 0,
            "message":          "No new posts to process.",
        }

    raw_posts = []
    for doc in raw_docs:
        try:
            doc.pop("_id", None)
            raw_posts.append(RawPost.model_validate(doc))
        except Exception as e:
            logger.warning("POST /cluster: invalid raw doc skipped — {}", e)

    preprocessor = TextPreprocessor()
    classifier   = PostClassifier()
    embedder     = EmbeddingService()
    clusterer    = ClusteringService()
    engine       = ThreatEngine()

    # Preprocess
    processed = [preprocessor.process(p) for p in raw_posts]

    # Classify
    for doc in processed:
        res = classifier.classify(
            clean_text=doc.get("clean_text", ""),
            source=doc.get("source", ""),
            platform=doc.get("platform", ""),
        )
        doc.update(res)

    # Embed
    vectors = embedder.embed_many([d.get("clean_text", "") for d in processed])
    for doc, vec in zip(processed, vectors):
        doc["embedding"] = vec

    # Cluster
    processed   = clusterer.cluster(processed)
    summaries   = clusterer.build_cluster_summaries(processed)

    # Strip embeddings before persistence
    for doc in processed:
        doc.pop("embedding", None)

    engine.save_processed_posts(processed)
    engine.save_clusters(summaries)
    events = engine.generate_events(summaries)

    return {
        "posts_processed":  len(processed),
        "clusters_found":   len(summaries),
        "events_generated": events,
        "message": (
            f"Pipeline complete: {len(processed)} posts processed, "
            f"{len(summaries)} cluster(s) found, {events} event(s) generated."
        ),
    }


# ---------------------------------------------------------------------------
# POST /run
# ---------------------------------------------------------------------------

_JOB_MAP = {
    ("telegram",   "collect"):  ("telegram_job",   "async"),
    ("reddit",     "collect"):  ("reddit_job",      "sync"),
    ("complaints", "collect"):  ("complaints_job",  "sync"),
    ("analysis",   "pipeline"): ("analysis_job",    "sync"),
}

VALID_RUN_SOURCES = {"telegram", "reddit", "complaints", "analysis"}
VALID_RUN_JOBS    = {"collect", "pipeline"}


@router.post(
    "/run",
    response_model=RunResponse,
    summary="Trigger a named background job",
    tags=["Actions"],
)
async def run_job(
    source: str,
    job:    str,
    background_tasks: BackgroundTasks,
) -> RunResponse:
    """
    Trigger a named job in the background.

    | source      | job       | Action                               |
    |-------------|-----------|--------------------------------------|
    | telegram    | collect   | Run Telegram collect_once()          |
    | reddit      | collect   | Run Reddit collect_once()            |
    | complaints  | collect   | Run Complaint scraper collect_once() |
    | analysis    | pipeline  | Run full analysis pipeline           |

    The job is queued as a background task and the response returns immediately.
    """
    src = source.lower().strip()
    jb  = job.lower().strip()

    if src not in VALID_RUN_SOURCES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid source '{src}'. Valid: {', '.join(sorted(VALID_RUN_SOURCES))}",
        )
    if jb not in VALID_RUN_JOBS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid job '{jb}'. Valid: {', '.join(sorted(VALID_RUN_JOBS))}",
        )

    key = (src, jb)
    if key not in _JOB_MAP:
        raise HTTPException(
            status_code=422,
            detail=f"Combination source='{src}' job='{jb}' is not supported.",
        )

    job_name, mode = _JOB_MAP[key]
    logger.info("POST /run: queuing '{}' ({})", job_name, mode)

    # Queue the task in the background so the HTTP response returns immediately
    if src == "analysis" and jb == "pipeline":
        background_tasks.add_task(_run_pipeline, 200)
    else:
        background_tasks.add_task(_background_collect, src)

    return RunResponse(
        source  = src,
        job     = jb,
        status  = "started",
        message = f"Job '{job_name}' has been queued as a background task.",
        result  = None,
    )


async def _background_collect(source: str) -> None:
    try:
        count = await _run_collector(source)
        logger.info("Background collect '{}': {} post(s) stored.", source, count)
    except Exception as e:
        logger.error("Background collect '{}' failed: {}", source, e)
