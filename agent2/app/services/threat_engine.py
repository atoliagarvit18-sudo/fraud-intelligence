"""
app/services/threat_engine.py

Calculates threat severity, campaign score, and overall confidence for a cluster.
Generates structured event documents when thresholds are crossed.

Reads from MongoDB via get_collection().
Writes processed_posts, clusters, and events to MongoDB.

No AI. No NLP. Pure scoring logic.
"""

from datetime import datetime, timezone

from loguru import logger
from pymongo.errors import PyMongoError

from app.config.constants import CLUSTERS, EVENTS, PROCESSED_POSTS
from app.database.mongo import get_collection

# ---------------------------------------------------------------------------
# Severity thresholds
# ---------------------------------------------------------------------------

# Minimum cluster size to generate a MEDIUM event
MEDIUM_THRESHOLD = 3

# Minimum cluster size to generate a HIGH event
HIGH_THRESHOLD = 10

# Minimum avg confidence to promote severity one level
CONFIDENCE_BOOST_MIN = 0.75

# Multi-source clusters get a score boost
MULTI_SOURCE_BONUS = 0.10


class ThreatEngine:
    """
    Calculates threat scores and persists processed results to MongoDB.

    Pipeline:
        1. save_processed_posts()   → writes to processed_posts collection
        2. save_clusters()          → writes cluster summaries to clusters collection
        3. generate_events()        → writes threat events to events collection

    Usage:
        engine = ThreatEngine()
        engine.save_processed_posts(processed_posts)
        engine.save_clusters(cluster_summaries)
        engine.generate_events(cluster_summaries)
    """

    # -----------------------------------------------------------------------
    # Persistence
    # -----------------------------------------------------------------------

    def save_processed_posts(self, processed_posts: list[dict]) -> int:
        """
        Insert processed post documents into the processed_posts collection.
        Skips duplicates silently.

        Returns the number of documents inserted.
        """
        if not processed_posts:
            return 0

        col = get_collection(PROCESSED_POSTS)
        inserted = 0

        try:
            result = col.insert_many(processed_posts, ordered=False)
            inserted = len(result.inserted_ids)
        except PyMongoError as e:
            # Partial inserts due to duplicates are acceptable
            inserted = getattr(e, "details", {}).get("nInserted", 0)
            logger.warning(
                "ThreatEngine.save_processed_posts: partial insert — {} saved.", inserted
            )

        logger.info("ThreatEngine: saved {} processed posts.", inserted)
        return inserted

    def save_clusters(self, cluster_summaries: list[dict]) -> int:
        """
        Upsert cluster documents into the clusters collection.
        Uses cluster_id as the unique key.

        Returns the number of upserts performed.
        """
        if not cluster_summaries:
            return 0

        col = get_collection(CLUSTERS)
        upserted = 0

        for cluster in cluster_summaries:
            try:
                scored = self._score_cluster(cluster)
                col.update_one(
                    {"cluster_id": cluster["cluster_id"]},
                    {"$set": {**cluster, **scored}},
                    upsert=True,
                )
                upserted += 1
            except PyMongoError as e:
                logger.error(
                    "ThreatEngine.save_clusters: failed for cluster_id={} — {}",
                    cluster.get("cluster_id"), e,
                )

        logger.info("ThreatEngine: upserted {} clusters.", upserted)
        return upserted

    def generate_events(self, cluster_summaries: list[dict]) -> int:
        """
        For each cluster that crosses a severity threshold,
        write an event document to the events collection.

        Returns the number of events generated.
        """
        if not cluster_summaries:
            return 0

        col = get_collection(EVENTS)
        generated = 0

        for cluster in cluster_summaries:
            scored   = self._score_cluster(cluster)
            severity = scored["severity"]

            if severity == "low":
                continue    # low-severity clusters don't warrant an event

            event = self._build_event(cluster, scored)

            try:
                col.insert_one(event)
                generated += 1
                logger.info(
                    "ThreatEngine: event generated — cluster_id={} severity={}",
                    cluster["cluster_id"], severity,
                )
            except PyMongoError as e:
                logger.error(
                    "ThreatEngine.generate_events: failed for cluster_id={} — {}",
                    cluster.get("cluster_id"), e,
                )

        logger.info("ThreatEngine: {} event(s) generated.", generated)
        return generated

    # -----------------------------------------------------------------------
    # Scoring
    # -----------------------------------------------------------------------

    def _score_cluster(self, cluster: dict) -> dict:
        """
        Calculate severity, campaign_score, and weighted_confidence
        for a cluster document.

        Returns a dict to be merged into the cluster before saving.
        """
        post_count      = cluster.get("post_count", 0)
        avg_confidence  = cluster.get("avg_confidence", 0.0)
        sources         = cluster.get("sources", [])
        is_multi_source = len(sources) > 1

        # Base campaign score: normalised post count (capped at 1.0)
        campaign_score = min(post_count / 20.0, 1.0)

        # Multi-source bonus: coordinated fraud across platforms is more severe
        if is_multi_source:
            campaign_score = min(campaign_score + MULTI_SOURCE_BONUS, 1.0)

        # Weighted confidence: blend model confidence with campaign breadth
        weighted_confidence = round(
            (avg_confidence * 0.6) + (campaign_score * 0.4), 4
        )

        # Severity ladder
        severity = self._calculate_severity(post_count, avg_confidence, is_multi_source)

        return {
            "campaign_score":       round(campaign_score, 4),
            "weighted_confidence":  weighted_confidence,
            "severity":             severity,
            "is_multi_source":      is_multi_source,
            "scored_at":            datetime.now(tz=timezone.utc),
        }

    def _calculate_severity(
        self,
        post_count: int,
        avg_confidence: float,
        is_multi_source: bool,
    ) -> str:
        """
        Map post count + confidence + multi-source flag to a severity label.

        Returns one of: "low" | "medium" | "high" | "critical"
        """
        if post_count >= HIGH_THRESHOLD:
            base = "high"
        elif post_count >= MEDIUM_THRESHOLD:
            base = "medium"
        else:
            base = "low"

        # Promote severity one level when confidence is high
        if avg_confidence >= CONFIDENCE_BOOST_MIN:
            if base == "low":
                base = "medium"
            elif base == "medium":
                base = "high"
            elif base == "high":
                base = "critical"

        # Multi-source + high severity → critical
        if is_multi_source and base == "high":
            base = "critical"

        return base

    # -----------------------------------------------------------------------
    # Event builder
    # -----------------------------------------------------------------------

    def _build_event(self, cluster: dict, scored: dict) -> dict:
        return {
            "event_type":           "fraud_campaign_detected",
            "severity":             scored["severity"],
            "cluster_id":           cluster["cluster_id"],
            "scam_type":            cluster.get("scam_type", "other"),
            "campaign_score":       scored["campaign_score"],
            "weighted_confidence":  scored["weighted_confidence"],
            "post_count":           cluster.get("post_count", 0),
            "sources":              cluster.get("sources", []),
            "platforms":            cluster.get("platforms", []),
            "is_multi_source":      scored["is_multi_source"],
            "earliest_post":        cluster.get("earliest_post"),
            "latest_post":          cluster.get("latest_post"),
            "occurred_at":          datetime.now(tz=timezone.utc),
            "status":               "open",
        }
