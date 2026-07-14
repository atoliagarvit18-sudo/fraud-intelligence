"""
app/normalizers/reddit.py

Converts a raw Reddit post dict (from PRAW, RSS, or JSON API)
into a standardized RawPost.

No database. No network calls. Normalization only.
"""

import re
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from app.models.raw_post import RawPost


class RedditNormalizer:
    """
    Converts Reddit post data from any collection strategy into a RawPost.

    Supports three input shapes:
        - PRAW submission object
        - RSS feedparser entry dict
        - Reddit public JSON child["data"] dict

    Usage:
        normalizer = RedditNormalizer()
        post = normalizer.from_praw(submission, subreddit_name="Scams")
        post = normalizer.from_rss(entry, subreddit_name="Scams")
        post = normalizer.from_json(data, subreddit_name="Scams")
    """

    # -----------------------------------------------------------------------
    # Public: PRAW submission
    # -----------------------------------------------------------------------

    def from_praw(self, submission, subreddit_name: str) -> RawPost | None:
        """
        Normalize a PRAW Submission object.

        Args:
            submission:     A praw.models.Submission instance.
            subreddit_name: The subreddit the post came from.

        Returns:
            RawPost or None if the post has no usable text.
        """
        try:
            text = (submission.selftext or "").strip()
            title = (submission.title or "").strip() or None

            # Link posts have empty selftext — use the title as text body
            if not text:
                text = title or ""

            if not text:
                logger.debug(
                    "RedditNormalizer.from_praw: skipping {} — no text.", submission.id
                )
                return None

            timestamp = datetime.fromtimestamp(
                submission.created_utc, tz=timezone.utc
            )

            return RawPost(
                source="reddit",
                source_id=str(submission.id),
                title=title,
                text=text,
                author=str(submission.author) if submission.author else None,
                timestamp=timestamp,
                url=f"https://reddit.com{submission.permalink}",
                platform=subreddit_name,
                language=None,
                metadata=self._praw_metadata(submission),
            )

        except Exception as e:
            logger.warning("RedditNormalizer.from_praw: failed — {}", e)
            return None

    # -----------------------------------------------------------------------
    # Public: RSS entry
    # -----------------------------------------------------------------------

    def from_rss(self, entry: dict, subreddit_name: str) -> RawPost | None:
        """
        Normalize a feedparser RSS entry dict.

        Args:
            entry:          A feedparser entry object (behaves like a dict).
            subreddit_name: The subreddit the feed came from.

        Returns:
            RawPost or None if the entry has no usable text.
        """
        try:
            raw_summary = entry.get("summary", "") or ""
            text  = self._strip_html(raw_summary).strip()
            title = (entry.get("title") or "").strip() or None

            if not text:
                text = title or ""

            if not text:
                logger.debug(
                    "RedditNormalizer.from_rss: skipping entry — no text."
                )
                return None

            source_id = entry.get("id") or entry.get("link") or ""
            if not source_id:
                logger.debug("RedditNormalizer.from_rss: skipping entry — no id/link.")
                return None

            published = entry.get("published_parsed")
            timestamp = (
                datetime(*published[:6], tzinfo=timezone.utc)
                if published
                else datetime.now(tz=timezone.utc)
            )

            return RawPost(
                source="reddit",
                source_id=source_id,
                title=title,
                text=text,
                author=entry.get("author") or None,
                timestamp=timestamp,
                url=entry.get("link") or None,
                platform=subreddit_name,
                language=None,
                metadata=self._rss_metadata(entry),
            )

        except Exception as e:
            logger.warning("RedditNormalizer.from_rss: failed — {}", e)
            return None

    # -----------------------------------------------------------------------
    # Public: Reddit public JSON API child["data"]
    # -----------------------------------------------------------------------

    def from_json(self, data: dict, subreddit_name: str) -> RawPost | None:
        """
        Normalize a Reddit JSON API post dict (child["data"]).

        Args:
            data:           The "data" field of a Reddit JSON listing child.
            subreddit_name: The subreddit the post came from.

        Returns:
            RawPost or None if the post has no usable text.
        """
        try:
            post_id = data.get("id", "").strip()
            if not post_id:
                logger.debug("RedditNormalizer.from_json: skipping — missing id.")
                return None

            text  = (data.get("selftext") or "").strip()
            title = (data.get("title") or "").strip() or None

            if not text:
                text = title or ""

            if not text:
                logger.debug(
                    "RedditNormalizer.from_json: skipping {} — no text.", post_id
                )
                return None

            created_utc = data.get("created_utc")
            if created_utc is None:
                logger.debug(
                    "RedditNormalizer.from_json: skipping {} — no timestamp.", post_id
                )
                return None

            timestamp = datetime.fromtimestamp(float(created_utc), tz=timezone.utc)
            permalink = data.get("permalink", "")

            return RawPost(
                source="reddit",
                source_id=post_id,
                title=title,
                text=text,
                author=data.get("author") or None,
                timestamp=timestamp,
                url=f"https://reddit.com{permalink}" if permalink else None,
                platform=subreddit_name,
                language=None,
                metadata=self._json_metadata(data),
            )

        except Exception as e:
            logger.warning("RedditNormalizer.from_json: failed — {}", e)
            return None

    # -----------------------------------------------------------------------
    # Metadata builders
    # -----------------------------------------------------------------------

    def _praw_metadata(self, submission) -> dict:
        return {
            "strategy":     "praw",
            "score":        getattr(submission, "score",             None),
            "upvote_ratio": getattr(submission, "upvote_ratio",      None),
            "num_comments": getattr(submission, "num_comments",      None),
            "flair":        getattr(submission, "link_flair_text",   None),
            "is_nsfw":      getattr(submission, "over_18",           None),
            "post_hint":    getattr(submission, "post_hint",         None),
            "subreddit_id": getattr(submission, "subreddit_id",      None),
        }

    def _rss_metadata(self, entry: dict) -> dict:
        tags = entry.get("tags", [])
        tag_labels = [t.get("term") for t in tags if t.get("term")]
        return {
            "strategy":  "rss",
            "tags":      tag_labels,
            "guid":      entry.get("id"),
            "feed_link": entry.get("link"),
        }

    def _json_metadata(self, data: dict) -> dict:
        return {
            "strategy":          "json",
            "score":             data.get("score"),
            "upvote_ratio":      data.get("upvote_ratio"),
            "num_comments":      data.get("num_comments"),
            "flair":             data.get("link_flair_text"),
            "is_nsfw":           data.get("over_18"),
            "post_hint":         data.get("post_hint"),
            "subreddit_id":      data.get("subreddit_id"),
            "domain":            data.get("domain"),
            "is_self":           data.get("is_self"),
        }

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _strip_html(text: str) -> str:
        """Remove HTML tags from a string."""
        return re.sub(r"<[^>]+>", " ", text)
