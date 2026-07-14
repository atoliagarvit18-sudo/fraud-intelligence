"""
app/services/clustering.py

Groups processed posts into fraud campaigns using DBSCAN on cosine similarity.
Each cluster represents a potential coordinated fraud campaign.

No database writes. Returns cluster labels and metadata only.
"""

import numpy as np
from loguru import logger
from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_similarity


# ---------------------------------------------------------------------------
# DBSCAN defaults — tune these for your dataset size and density
# ---------------------------------------------------------------------------

# Maximum cosine distance to consider two posts "neighbours".
# eps=0.2 means posts must be at least 80% similar to cluster together.
DEFAULT_EPS         = 0.20
DEFAULT_MIN_SAMPLES = 2     # minimum posts to form a cluster (low for hackathon)


class ClusteringService:
    """
    Clusters post embeddings using DBSCAN with cosine similarity.

    DBSCAN is chosen because:
    - Does not require knowing the number of clusters upfront.
    - Labels outlier posts as noise (-1) instead of forcing them into a cluster.
    - Works well with high-dimensional dense vectors.

    Usage:
        clusterer = ClusteringService()
        result = clusterer.cluster(processed_posts)
    """

    def __init__(
        self,
        eps: float = DEFAULT_EPS,
        min_samples: int = DEFAULT_MIN_SAMPLES,
    ) -> None:
        self.eps = eps
        self.min_samples = min_samples

    def cluster(self, processed_posts: list[dict]) -> list[dict]:
        """
        Assign cluster IDs to processed posts based on embedding similarity.

        Args:
            processed_posts: List of dicts, each must have:
                - "raw_post_id" (str)
                - "embedding"   (list[float] | None)

        Returns:
            The same list with a "cluster_id" field added to each item.
            Posts without embeddings or labelled as noise get cluster_id = -1.
        """
        if not processed_posts:
            return processed_posts

        # Separate posts that have valid embeddings
        valid   = [(i, p) for i, p in enumerate(processed_posts) if p.get("embedding")]
        invalid = [(i, p) for i, p in enumerate(processed_posts) if not p.get("embedding")]

        # Mark posts with no embedding as noise immediately
        for _, post in invalid:
            post["cluster_id"] = -1

        if len(valid) < self.min_samples:
            logger.warning(
                "ClusteringService: only {} valid embeddings — too few to cluster.",
                len(valid),
            )
            for _, post in valid:
                post["cluster_id"] = -1
            return processed_posts

        indices   = [i for i, _ in valid]
        posts_sub = [p for _, p in valid]
        matrix    = np.array([p["embedding"] for p in posts_sub], dtype=np.float32)

        # Convert cosine similarity → distance matrix for DBSCAN
        # similarity ∈ [-1,1], distance = 1 - similarity ∈ [0, 2]
        similarity_matrix = cosine_similarity(matrix)
        distance_matrix   = 1.0 - similarity_matrix
        np.clip(distance_matrix, 0.0, 2.0, out=distance_matrix)

        labels = DBSCAN(
            eps=self.eps,
            min_samples=self.min_samples,
            metric="precomputed",
        ).fit_predict(distance_matrix)

        # Write cluster labels back to the original list positions
        for original_idx, label in zip(indices, labels):
            processed_posts[original_idx]["cluster_id"] = int(label)

        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        n_noise    = list(labels).count(-1)

        logger.info(
            "ClusteringService: {} posts → {} cluster(s), {} noise post(s).",
            len(valid), n_clusters, n_noise,
        )

        return processed_posts

    def build_cluster_summaries(self, processed_posts: list[dict]) -> list[dict]:
        """
        Aggregate clustered posts into campaign-level cluster documents.

        Returns a list of cluster dicts ready for insertion into the
        `clusters` collection.
        """
        from collections import defaultdict
        from datetime import datetime, timezone

        groups: dict[int, list[dict]] = defaultdict(list)
        for post in processed_posts:
            cid = post.get("cluster_id", -1)
            if cid != -1:
                groups[cid].append(post)

        summaries = []
        for cluster_id, posts in groups.items():
            scam_types = [p.get("scam_type", "other") for p in posts]
            # Majority vote on scam type
            dominant_scam_type = max(set(scam_types), key=scam_types.count)

            confidences = [p.get("confidence", 0.0) for p in posts if p.get("confidence")]
            avg_confidence = round(sum(confidences) / len(confidences), 4) if confidences else 0.0

            sources    = list({p.get("source") for p in posts if p.get("source")})
            platforms  = list({p.get("platform") for p in posts if p.get("platform")})
            post_ids   = [p.get("raw_post_id") for p in posts]
            timestamps = [p.get("timestamp") for p in posts if p.get("timestamp")]

            summaries.append({
                "cluster_id":        cluster_id,
                "scam_type":         dominant_scam_type,
                "avg_confidence":    avg_confidence,
                "post_count":        len(posts),
                "sources":           sources,
                "platforms":         platforms,
                "raw_post_ids":      post_ids,
                "earliest_post":     min(timestamps) if timestamps else None,
                "latest_post":       max(timestamps) if timestamps else None,
                "created_at":        datetime.now(tz=timezone.utc),
                "status":            "active",
            })

        logger.info(
            "ClusteringService: built {} cluster summaries.", len(summaries)
        )
        return summaries
