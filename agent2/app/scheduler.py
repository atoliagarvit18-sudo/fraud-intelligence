"""
app/scheduler.py

Central scheduler for Agent 2.
Runs all collection and analysis jobs on configurable intervals using APScheduler.

Job groups
----------
Collection jobs (independent, run in parallel threads):
    - telegram_job   → TelegramCollector.collect_once()
    - reddit_job     → RedditCollector.collect_once()
    - complaints_job → ComplaintsCollector.collect_once()

Analysis pipeline (sequential, runs after collectors produce data):
    - analysis_job   → preprocess → classify → embed → cluster → threat engine

Each job retries up to JOB_MAX_RETRIES times on failure before logging and giving up.
"""

import asyncio
import sys
from datetime import datetime, timezone
from functools import wraps
from typing import Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from app.config.constants import (
    INTERVAL_ANALYSIS_SECONDS,
    INTERVAL_COMPLAINTS_SECONDS,
    INTERVAL_REDDIT_SECONDS,
    INTERVAL_TELEGRAM_SECONDS,
    JOB_MAX_RETRIES,
    RAW_POSTS,
)
from app.database.mongo import get_collection

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
    level="INFO",
    colorize=True,
)
logger.add(
    "logs/scheduler.log",
    rotation="50 MB",
    retention="14 days",
    compression="gz",
    level="DEBUG",
    enqueue=True,   # thread-safe async logging
)


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------

def with_retry(max_retries: int = JOB_MAX_RETRIES):
    """
    Decorator that retries a sync or async callable up to `max_retries` times.
    Logs each failure. Swallows the exception after the final attempt so the
    scheduler loop continues uninterrupted.
    """
    def decorator(fn: Callable):
        if asyncio.iscoroutinefunction(fn):
            @wraps(fn)
            async def async_wrapper(*args, **kwargs):
                for attempt in range(1, max_retries + 1):
                    try:
                        return await fn(*args, **kwargs)
                    except Exception as e:
                        logger.warning(
                            "Job '{}' failed (attempt {}/{}): {}",
                            fn.__name__, attempt, max_retries, e,
                        )
                        if attempt < max_retries:
                            await asyncio.sleep(5 * attempt)   # back-off
                logger.error(
                    "Job '{}' exhausted all {} retries — skipping this run.",
                    fn.__name__, max_retries,
                )
            return async_wrapper
        else:
            @wraps(fn)
            def sync_wrapper(*args, **kwargs):
                for attempt in range(1, max_retries + 1):
                    try:
                        return fn(*args, **kwargs)
                    except Exception as e:
                        logger.warning(
                            "Job '{}' failed (attempt {}/{}): {}",
                            fn.__name__, attempt, max_retries, e,
                        )
                        if attempt < max_retries:
                            import time
                            time.sleep(5 * attempt)
                logger.error(
                    "Job '{}' exhausted all {} retries — skipping this run.",
                    fn.__name__, max_retries,
                )
            return sync_wrapper
    return decorator


# ---------------------------------------------------------------------------
# Collection jobs
# ---------------------------------------------------------------------------

@with_retry()
async def telegram_job() -> None:
    """Fetch new messages from all configured Telegram channels."""
    from app.collectors.telegram import TelegramCollector

    logger.info("[telegram_job] starting.")
    collector = TelegramCollector()
    await collector.connect()
    count = await collector.collect_once()
    await collector.disconnect()
    logger.info("[telegram_job] done. Stored {} post(s).", count)


@with_retry()
def reddit_job() -> None:
    """Collect new posts from configured subreddits using the best available strategy."""
    from app.collectors.reddit import RedditCollector

    logger.info("[reddit_job] starting.")
    collector = RedditCollector()
    count = collector.collect_once()
    logger.info("[reddit_job] done. Stored {} post(s).", count)


@with_retry()
def complaints_job() -> None:
    """Scrape configured complaint websites for one pagination sweep."""
    from app.collectors.complaints import ComplaintsCollector

    logger.info("[complaints_job] starting.")
    collector = ComplaintsCollector()
    count = collector.collect_once()
    logger.info("[complaints_job] done. Stored {} post(s).", count)


# ---------------------------------------------------------------------------
# Analysis pipeline job
# ---------------------------------------------------------------------------

@with_retry()
def analysis_job() -> None:
    """
    Sequential analysis pipeline:
        1. Fetch unprocessed raw_posts from MongoDB
        2. Preprocess (clean, detect language)
        3. Classify with Groq (scam type, confidence, entities)
        4. Generate embeddings (all-MiniLM-L6-v2)
        5. Cluster with DBSCAN (cosine similarity)
        6. Score clusters and generate threat events
    """
    from app.services.classifier import PostClassifier
    from app.services.clustering import ClusteringService
    from app.services.embeddings import EmbeddingService
    from app.services.preprocessing import TextPreprocessor
    from app.services.threat_engine import ThreatEngine
    from app.models.raw_post import RawPost

    logger.info("[analysis_job] starting.")

    # ------------------------------------------------------------------
    # Step 0: Fetch unprocessed raw posts
    # ------------------------------------------------------------------
    raw_col       = get_collection(RAW_POSTS)
    processed_col = get_collection("processed_posts")

    already_processed_ids = set(
        processed_col.distinct("raw_post_id")
    )

    raw_cursor = raw_col.find(
        {"source_id": {"$nin": list(already_processed_ids)}},
        limit=200,              # cap batch size per run
    )
    raw_docs = list(raw_cursor)

    if not raw_docs:
        logger.info("[analysis_job] no new raw posts — nothing to do.")
        return

    logger.info("[analysis_job] processing {} raw post(s).", len(raw_docs))

    # ------------------------------------------------------------------
    # Step 1: Deserialise into RawPost objects
    # ------------------------------------------------------------------
    raw_posts: list[RawPost] = []
    for doc in raw_docs:
        try:
            doc.pop("_id", None)
            raw_posts.append(RawPost.model_validate(doc))
        except Exception as e:
            logger.warning("[analysis_job] skipping invalid raw doc: {}", e)

    if not raw_posts:
        logger.warning("[analysis_job] no valid raw posts after deserialisation.")
        return

    # ------------------------------------------------------------------
    # Step 2: Preprocess
    # ------------------------------------------------------------------
    preprocessor = TextPreprocessor()
    processed: list[dict] = []

    for post in raw_posts:
        try:
            processed.append(preprocessor.process(post))
        except Exception as e:
            logger.warning("[analysis_job] preprocessing failed for {}: {}", post.source_id, e)

    logger.info("[analysis_job] preprocessed {} posts.", len(processed))

    # ------------------------------------------------------------------
    # Step 3: Classify
    # ------------------------------------------------------------------
    classifier = PostClassifier()

    for doc in processed:
        try:
            result = classifier.classify(
                clean_text=doc.get("clean_text", ""),
                source=doc.get("source", ""),
                platform=doc.get("platform", ""),
            )
            doc.update(result)
        except Exception as e:
            logger.warning(
                "[analysis_job] classification failed for {}: {}",
                doc.get("raw_post_id"), e,
            )
            doc.update({"is_fraud": False, "scam_type": "other", "confidence": 0.0,
                        "summary": "", "entities": {}, "error": str(e)})

    fraud_count = sum(1 for d in processed if d.get("is_fraud"))
    logger.info("[analysis_job] classified. {} flagged as fraud.", fraud_count)

    # ------------------------------------------------------------------
    # Step 4: Embeddings
    # ------------------------------------------------------------------
    embedder = EmbeddingService()
    texts    = [d.get("clean_text", "") for d in processed]

    try:
        vectors = embedder.embed_many(texts)
        for doc, vector in zip(processed, vectors):
            doc["embedding"] = vector
    except Exception as e:
        logger.error("[analysis_job] embedding batch failed: {} — setting all to None.", e)
        for doc in processed:
            doc["embedding"] = None

    embedded_count = sum(1 for d in processed if d.get("embedding"))
    logger.info("[analysis_job] embedded {}/{} posts.", embedded_count, len(processed))

    # ------------------------------------------------------------------
    # Step 5: Cluster
    # ------------------------------------------------------------------
    clusterer = ClusteringService()
    try:
        processed = clusterer.cluster(processed)
        summaries = clusterer.build_cluster_summaries(processed)
    except Exception as e:
        logger.error("[analysis_job] clustering failed: {}", e)
        summaries = []

    cluster_count = len(summaries)
    logger.info("[analysis_job] found {} cluster(s).", cluster_count)

    # ------------------------------------------------------------------
    # Step 6: Persist + generate threat events
    # ------------------------------------------------------------------
    engine = ThreatEngine()

    # Strip embeddings before persisting to MongoDB (too large, not needed)
    for doc in processed:
        doc.pop("embedding", None)

    engine.save_processed_posts(processed)
    engine.save_clusters(summaries)
    events_generated = engine.generate_events(summaries)

    logger.info(
        "[analysis_job] done. posts={} clusters={} events={}.",
        len(processed), cluster_count, events_generated,
    )


# ---------------------------------------------------------------------------
# Scheduler bootstrap
# ---------------------------------------------------------------------------

class PipelineScheduler:
    """
    Object-oriented wrapper around AsyncIOScheduler that manages collection
    and analysis jobs.
    """

    def __init__(self) -> None:
        self.scheduler = build_scheduler()

    def start(self) -> None:
        self.scheduler.start()
        logger.success(
            "PipelineScheduler started. {} job(s) registered.",
            len(self.scheduler.get_jobs()),
        )

    def shutdown(self, wait: bool = True) -> None:
        self.scheduler.shutdown(wait=wait)
        logger.info("PipelineScheduler shut down.")

    def get_jobs(self):
        return self.scheduler.get_jobs()


def build_scheduler() -> AsyncIOScheduler:
    """
    Create and configure the APScheduler instance with all jobs registered.

    Returns the scheduler (not yet started).
    """
    scheduler = AsyncIOScheduler(timezone="UTC")

    # ---- Collection jobs --------------------------------------------------
    scheduler.add_job(
        telegram_job,
        trigger=IntervalTrigger(seconds=INTERVAL_TELEGRAM_SECONDS),
        id="telegram_job",
        name="Telegram Collector",
        replace_existing=True,
        max_instances=1,         # prevent overlap if a run takes longer than interval
        misfire_grace_time=30,
    )

    scheduler.add_job(
        reddit_job,
        trigger=IntervalTrigger(seconds=INTERVAL_REDDIT_SECONDS),
        id="reddit_job",
        name="Reddit Collector",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=60,
    )

    scheduler.add_job(
        complaints_job,
        trigger=IntervalTrigger(seconds=INTERVAL_COMPLAINTS_SECONDS),
        id="complaints_job",
        name="Complaint Sites Collector",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=120,
    )

    # ---- Analysis pipeline ------------------------------------------------
    scheduler.add_job(
        analysis_job,
        trigger=IntervalTrigger(seconds=INTERVAL_ANALYSIS_SECONDS),
        id="analysis_job",
        name="Analysis Pipeline",
        replace_existing=True,
        max_instances=1,
        misfire_grace_time=60,
    )

    return scheduler


async def main() -> None:
    """
    Entry point for the scheduler process.
    Starts the scheduler and blocks forever.
    Handles KeyboardInterrupt and SIGTERM gracefully.
    """
    logger.info("=" * 60)
    logger.info("Agent 2 Scheduler starting at {}.", datetime.now(tz=timezone.utc))
    logger.info(
        "Intervals: Telegram={}s Reddit={}s Complaints={}s Analysis={}s",
        INTERVAL_TELEGRAM_SECONDS,
        INTERVAL_REDDIT_SECONDS,
        INTERVAL_COMPLAINTS_SECONDS,
        INTERVAL_ANALYSIS_SECONDS,
    )
    logger.info("=" * 60)

    scheduler = build_scheduler()
    scheduler.start()

    logger.success("Scheduler started. {} job(s) registered.", len(scheduler.get_jobs()))
    for job in scheduler.get_jobs():
        logger.info("  ↳ [{}] next run: {}", job.name, job.next_run_time)

    try:
        # Keep the event loop alive indefinitely
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutdown signal received.")
    finally:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped cleanly.")


if __name__ == "__main__":
    asyncio.run(main())
