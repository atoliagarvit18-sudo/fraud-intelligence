"""
app/repositories/raw_post_repository.py

MongoDB operations for the raw_posts collection.
No business logic — insert, query, count only.
"""

from loguru import logger
from pymongo.collection import Collection
from pymongo.errors import BulkWriteError, PyMongoError

from app.config.constants import RAW_POSTS
from app.database.mongo import get_collection
from app.models.raw_post import RawPost


class RawPostRepository:
    """
    Handles all MongoDB operations for the raw_posts collection.

    Usage:
        repo = RawPostRepository()
        repo.bulk_insert(posts)
        repo.count()
        repo.latest(limit=10)
    """

    def __init__(self) -> None:
        self.collection.create_index(
            [("source", 1), ("source_id", 1)],
            unique=True,
        )
        self.collection: Collection = get_collection(RAW_POSTS)

    # -----------------------------------------------------------------------
    # Write
    # -----------------------------------------------------------------------

    def bulk_insert(self, posts: list[RawPost]) -> int:
        """
        Insert a list of RawPost objects into MongoDB.

        Skips duplicates silently (ordered=False continues on duplicate key errors).
        Returns the number of documents actually inserted.
        """
        if not posts:
            logger.debug("RawPostRepository.bulk_insert: empty list, nothing to insert.")
            return 0

        documents = [post.model_dump() for post in posts]

        try:
            result = self.collection.insert_many(documents, ordered=False)
            inserted = len(result.inserted_ids)
            logger.info("RawPostRepository: inserted {} / {} posts.", inserted, len(posts))
            return inserted

        except BulkWriteError as e:
            # insert_many with ordered=False raises BulkWriteError even on partial success.
            # Extract how many were actually written.
            inserted = e.details.get("nInserted", 0)
            skipped = len(posts) - inserted
            logger.warning(
                "RawPostRepository: bulk write partial — {} inserted, {} skipped (likely duplicates).",
                inserted,
                skipped,
            )
            return inserted

        except PyMongoError as e:
            logger.error("RawPostRepository.bulk_insert failed: {}", e)
            raise

    # -----------------------------------------------------------------------
    # Read
    # -----------------------------------------------------------------------

    def find_existing_posts(self, posts: list[RawPost]) -> set[tuple[str, str]]:
        """
        Given a list of RawPost objects, return the (source, source_id) pairs
        that already exist in MongoDB.

        Use this before inserting to find which posts are genuinely new.
        """
        if not posts:
            return set()

        pairs = list({
            (p.source, p.source_id)
            for p in posts
        })

        query = [
            {"source": source, "source_id": source_id}
            for source, source_id in pairs
        ]

        try:
            cursor = self.collection.find(
                {"$or": pairs},
                {"source": 1, "source_id": 1, "_id": 0},
            )
            existing = {(doc["source"], doc["source_id"]) for doc in cursor}
            logger.debug(
                "RawPostRepository.find_existing_posts: {} / {} already in DB.",
                len(existing),
                len(posts),
            )
            return existing

        except PyMongoError as e:
            logger.error("RawPostRepository.find_existing_posts failed: {}", e)
            raise

    def count(self) -> int:
        """Return the total number of documents in raw_posts."""
        try:
            total = self.collection.count_documents({})
            logger.debug("RawPostRepository.count: {} documents.", total)
            return total

        except PyMongoError as e:
            logger.error("RawPostRepository.count failed: {}", e)
            raise

    def latest(self, limit: int = 10) -> list[RawPost]:
        limit = max(1, limit)
        """
        Return the most recent posts, newest first.
        Sorted by timestamp (original publish time) descending.
        """
        try:
            cursor = self.collection.find(
                {},
                {"_id": 0},
            ).sort("timestamp", -1).limit(limit)

            posts = [RawPost(**doc) for doc in cursor]
            logger.debug("RawPostRepository.latest: returned {} posts.", len(posts))
            return posts

        except PyMongoError as e:
            logger.error("RawPostRepository.latest failed: {}", e)
            raise
