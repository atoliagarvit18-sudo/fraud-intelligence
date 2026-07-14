"""
app/services/storage.py

Orchestrates saving collected posts to MongoDB.
Does NOT talk to MongoDB directly — delegates all DB work to RawPostRepository.
"""

from loguru import logger
from pydantic import ValidationError

from app.models.raw_post import RawPost
from app.repositories.raw_post_repository import RawPostRepository


class StorageService:
    """
    Sits between collectors and the repository.

    Responsibilities:
        1. Validate incoming RawPost objects.
        2. Remove duplicates already in MongoDB.
        3. Bulk-insert only new posts via the repository.
        4. Return a summary dict with inserted / duplicates / failed counts.

    Usage:
        service = StorageService()
        result = service.store(posts)
        # {"inserted": 42, "duplicates": 5, "failed": 1}
    """

    def __init__(self) -> None:
        self.repo = RawPostRepository()

    def store(self, posts: list[RawPost]) -> dict[str, int]:
        """
        Validate, deduplicate, and persist a list of RawPost objects.

        Returns:
            {
                "inserted":   number of posts written to MongoDB,
                "duplicates": number of posts already in MongoDB,
                "failed":     number of posts that failed Pydantic validation,
            }
        """
        if not posts:
            logger.debug("StorageService.save: received empty list.")
            return {"inserted": 0, "duplicates": 0, "failed": 0}

        logger.info("StorageService: received {} post(s) to save.", len(posts))

        # ------------------------------------------------------------------
        # Step 1 — Validate
        # ------------------------------------------------------------------
        valid: list[RawPost] = []
        failed = 0

        for post in posts:
            try:
                # Re-validate to catch any runtime corruption.
                # model_validate re-runs Pydantic validation on the existing object.
                RawPost.model_validate(post.model_dump())
                valid.append(post)
            except ValidationError as e:
                failed += 1
                logger.warning(
                    "StorageService: invalid post dropped (source={}, source_id={}): {}",
                    getattr(post, "source", "?"),
                    getattr(post, "source_id", "?"),
                    e,
                )

        if not valid:
            logger.warning("StorageService: no valid posts to insert after validation.")
            return {"inserted": 0, "duplicates": 0, "failed": failed}

        # ------------------------------------------------------------------
        # Step 2 — Deduplicate
        # ------------------------------------------------------------------
        existing = self.repo.find_existing_posts(valid)

        new_posts = [
            p for p in valid
            if (p.source, p.source_id) not in existing
        ]

        duplicates = len(valid) - len(new_posts)

        logger.info(
            "StorageService: {} new, {} duplicate(s), {} failed.",
            len(new_posts),
            duplicates,
            failed,
        )

        # ------------------------------------------------------------------
        # Step 3 — Insert
        # ------------------------------------------------------------------
        inserted = 0
        
        if new_posts:
            inserted = self.repo.bulk_insert(new_posts)

        return {"inserted": inserted, "duplicates": duplicates, "failed": failed}
