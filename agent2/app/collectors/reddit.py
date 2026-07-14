"""
app/collectors/reddit.py

Collects posts from Reddit using three strategies in priority order:
  1. PRAW  — when credentials are set in .env
  2. RSS   — lightweight, no credentials needed
  3. JSON  — public Reddit API, no credentials needed

Falls back automatically if a strategy fails or returns nothing.
Integrates with StorageService for persistence.
"""

import re
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote

import feedparser
import requests
from loguru import logger

from app.config.constants import (
    POLL_INTERVAL_SECONDS,
    REDDIT_KEYWORDS,
    REDDIT_LIMIT,
    REDDIT_SUBREDDITS,
)
from app.config.settings import settings
from app.models.raw_post import RawPost
from app.normalizers.reddit import RedditNormalizer
from app.services.storage import StorageService

# ---------------------------------------------------------------------------
# Module-level config (read from settings, never from os.getenv directly)
# ---------------------------------------------------------------------------

_USER_AGENT = settings.REDDIT_USER_AGENT or "fraud-intel-agent/1.0"

REQUEST_DELAY = 1.5   # seconds between requests
RETRY_DELAY   = 3     # seconds before retrying a failed request
MAX_RETRIES   = 2


# ---------------------------------------------------------------------------
# RedditCollector
# ---------------------------------------------------------------------------

class RedditCollector:
    """
    Collects Reddit posts related to fraud.

    Strategies (in order of priority):
        1. PRAW  — uses settings.REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET
        2. RSS   — r/{subreddit}/new.rss
        3. JSON  — r/{subreddit}/search.json

    Usage:
        collector = RedditCollector()
        collector.collect_once()   # one sweep, stores via StorageService
        collector.run()            # continuous polling loop
    """

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": _USER_AGENT})
        self.normalizer = RedditNormalizer()
        self.storage = StorageService()

    # -----------------------------------------------------------------------
    # Public: single sweep
    # -----------------------------------------------------------------------

    def collect_once(
        self,
        keywords: list[str]   = REDDIT_KEYWORDS,
        subreddits: list[str] = REDDIT_SUBREDDITS,
        limit: int            = REDDIT_LIMIT,
    ) -> int:
        """
        Fetch posts, store via StorageService, return inserted count.
        """
        logger.info(
            "RedditCollector.collect_once: {} keyword(s), {} subreddit(s), limit={}.",
            len(keywords), len(subreddits), limit,
        )

        posts = self._fetch_posts(keywords, subreddits, limit)

        if not posts:
            logger.warning("RedditCollector: no posts collected this sweep.")
            return 0

        result = self.storage.store(posts)
        logger.info(
            "RedditCollector: stored={}, duplicates={}, failed={}.",
            result["inserted"], result["duplicates"], result["failed"],
        )
        return result["inserted"]

    # -----------------------------------------------------------------------
    # Public: continuous loop
    # -----------------------------------------------------------------------

    def run(
        self,
        keywords: list[str]   = REDDIT_KEYWORDS,
        subreddits: list[str] = REDDIT_SUBREDDITS,
        limit: int            = REDDIT_LIMIT,
    ) -> None:
        """
        Poll Reddit continuously, sleeping POLL_INTERVAL_SECONDS between sweeps.
        """
        logger.info(
            "RedditCollector.run: starting loop (interval={}s).", POLL_INTERVAL_SECONDS
        )
        while True:
            try:
                self.collect_once(keywords, subreddits, limit)
            except Exception as e:
                logger.error("RedditCollector.run: unexpected error — {}", e)

            logger.debug("RedditCollector: sleeping {}s.", POLL_INTERVAL_SECONDS)
            time.sleep(POLL_INTERVAL_SECONDS)

    # -----------------------------------------------------------------------
    # Internal: strategy selector with automatic fallback
    # -----------------------------------------------------------------------

    def _fetch_posts(
        self,
        keywords: list[str],
        subreddits: list[str],
        limit: int,
    ) -> list[RawPost]:
        # Strategy 1: PRAW
        if settings.REDDIT_CLIENT_ID and settings.REDDIT_CLIENT_SECRET:
            logger.info("Reddit: trying PRAW strategy.")
            posts = self._fetch_via_praw(keywords, subreddits, limit)
            if posts:
                logger.success("Reddit: PRAW returned {} posts.", len(posts))
                return posts
            logger.warning("Reddit: PRAW returned nothing, falling back to RSS.")

        # Strategy 2: RSS
        logger.info("Reddit: trying RSS strategy.")
        posts = self._fetch_via_rss(subreddits, limit)
        if posts:
            logger.success("Reddit: RSS returned {} posts.", len(posts))
            return posts
        logger.warning("Reddit: RSS returned nothing, falling back to public JSON.")

        # Strategy 3: Public JSON
        logger.info("Reddit: trying public JSON strategy.")
        posts = self._fetch_via_json(keywords, subreddits, limit)
        if posts:
            logger.success("Reddit: JSON returned {} posts.", len(posts))
        else:
            logger.error("Reddit: all strategies exhausted, returning empty list.")

        return posts

    # -----------------------------------------------------------------------
    # Strategy 1: PRAW
    # -----------------------------------------------------------------------

    def _fetch_via_praw(
        self, keywords: list[str], subreddits: list[str], limit: int
    ) -> list[RawPost]:
        try:
            import praw
        except ImportError:
            logger.warning("PRAW not installed, skipping.")
            return []

        try:
            reddit = praw.Reddit(
                client_id=settings.REDDIT_CLIENT_ID,
                client_secret=settings.REDDIT_CLIENT_SECRET,
                user_agent=_USER_AGENT,
            )
            posts: list[RawPost] = []
            query = " OR ".join(f'"{kw}"' for kw in keywords)

            for sub_name in subreddits:
                try:
                    for submission in reddit.subreddit(sub_name).search(
                        query, limit=limit, sort="new"
                    ):
                        post = self.normalizer.from_praw(submission, sub_name)
                        if post:
                            posts.append(post)
                        time.sleep(REQUEST_DELAY)
                except Exception as e:
                    logger.warning("PRAW: error on r/{} — {}", sub_name, e)

            return posts
        except Exception as e:
            logger.error("PRAW: setup failed — {}", e)
            return []

    # -----------------------------------------------------------------------
    # Strategy 2: RSS
    # -----------------------------------------------------------------------

    def _fetch_via_rss(self, subreddits: list[str], limit: int) -> list[RawPost]:
        posts: list[RawPost] = []

        for sub_name in subreddits:
            url = f"https://www.reddit.com/r/{sub_name}/new.rss"
            feed = self._get_rss(url)
            if not feed:
                continue

            for entry in feed.entries[:limit]:
                try:
                    post = self.normalizer.from_rss(entry, sub_name)
                    if post:
                        posts.append(post)
                except Exception as e:
                    logger.warning("RSS: skipping entry — {}", e)

            time.sleep(REQUEST_DELAY)

        return posts

    def _get_rss(self, url: str) -> Optional[feedparser.FeedParserDict]:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                feed = feedparser.parse(url)
                if feed.bozo:
                    raise ValueError(feed.bozo_exception)
                if not feed.entries:
                    logger.warning("RSS: empty feed — {}", url)
                    return None
                return feed
            except Exception as e:
                logger.warning("RSS: attempt {}/{} failed — {}", attempt, MAX_RETRIES, e)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
        return None

    # -----------------------------------------------------------------------
    # Strategy 3: Public JSON
    # -----------------------------------------------------------------------

    def _fetch_via_json(
        self, keywords: list[str], subreddits: list[str], limit: int
    ) -> list[RawPost]:
        posts: list[RawPost] = []

        for sub_name in subreddits:
            for keyword in keywords:
                url = (
                    f"https://www.reddit.com/r/{sub_name}/search.json"
                    f"?q={quote(keyword)}&restrict_sr=1&sort=new&limit={limit}"
                )
                data = self._get_json(url)
                if not data:
                    continue

                for child in data.get("data", {}).get("children", []):
                    try:
                        post = self.normalizer.from_json(child["data"], sub_name)
                        if post:
                            posts.append(post)
                    except Exception as e:
                        logger.warning("JSON: skipping post — {}", e)

                time.sleep(REQUEST_DELAY)

        return posts

    def _get_json(self, url: str) -> Optional[dict]:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = self.session.get(url, timeout=10)
                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", RETRY_DELAY))
                    logger.warning("JSON: rate limited, waiting {}s.", wait)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except Exception as e:
                logger.warning("JSON: attempt {}/{} failed — {}", attempt, MAX_RETRIES, e)
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
        return None
