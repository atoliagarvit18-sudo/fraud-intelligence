"""
app/normalizers/complaints.py

Converts a raw complaint/review dict scraped from a complaint website
into a standardized RawPost.

No database. No network calls. Normalization only.
"""

import hashlib
import re
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from app.models.raw_post import RawPost


# Date formats attempted in order when parsing raw date strings.
_DATE_FORMATS: list[str] = [
    "%B %d, %Y",      # January 5, 2024
    "%d %B %Y",       # 5 January 2024
    "%b %d, %Y",      # Jan 5, 2024
    "%Y-%m-%d",       # 2024-01-05
    "%d/%m/%Y",       # 05/01/2024
    "%m/%d/%Y",       # 01/05/2024
    "%d-%m-%Y",       # 05-01-2024
    "%d %b %Y",       # 05 Jan 2024
    "%Y-%m-%dT%H:%M:%S",     # 2024-01-05T10:30:00
    "%Y-%m-%dT%H:%M:%SZ",    # 2024-01-05T10:30:00Z
]


class ComplaintsNormalizer:
    """
    Converts a raw complaint/review dict (extracted by Selenium) into a RawPost.

    Input dict keys (all optional except text or title):
        title     (str)  — headline of the complaint
        text      (str)  — full body text
        url       (str)  — direct link to the complaint page
        date      (str)  — raw date string as found on the page
        author    (str)  — reviewer name, if visible
        location  (str)  — geographic location, if mentioned
        site_name (str)  — name of the source site (e.g. "complaintsboard")
        page_url  (str)  — URL of the listing page where this was found

    Usage:
        normalizer = ComplaintsNormalizer()
        post = normalizer.normalize(raw_dict)
    """

    def normalize(self, raw: dict) -> RawPost | None:
        """
        Convert a scraped complaint dict into a RawPost.

        Returns:
            RawPost if the record has enough content, None otherwise.
        """
        try:
            title = self._clean(raw.get("title", "")) or None
            text  = self._clean(raw.get("text",  ""))

            # Require at least a title or body text
            if not text and not title:
                logger.debug(
                    "ComplaintsNormalizer: skipping record — no text or title."
                )
                return None

            # Use title as text body when body is absent (headline-only scrape)
            if not text:
                text = title or ""

            url       = raw.get("url")  or None
            site_name = raw.get("site_name", "unknown")
            page_url  = raw.get("page_url")

            source_id = self._make_source_id(site_name, url, text)
            timestamp = self._parse_date(raw.get("date", ""))

            post = RawPost(
                source="complaint_site",
                source_id=source_id,
                title=title,
                text=text,
                author=self._clean(raw.get("author", "")) or None,
                timestamp=timestamp,
                url=url,
                location=self._clean(raw.get("location", "")) or None,
                platform=site_name,
                language=None,
                metadata=self._build_metadata(raw, site_name, page_url),
            )

            logger.debug(
                "ComplaintsNormalizer: normalized complaint from '{}' — id={}.",
                site_name,
                source_id,
            )
            return post

        except Exception as e:
            logger.warning("ComplaintsNormalizer.normalize: failed — {}", e)
            return None

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _make_source_id(
        self,
        site_name: str,
        url: Optional[str],
        text: str,
    ) -> str:
        """
        Generate a stable source_id.
        Prefer hashing the URL (most stable).
        Fall back to hashing site_name + first 200 chars of text.
        """
        if url:
            key = f"{site_name}:{url}"
        else:
            key = f"{site_name}:{text[:200]}"
        return hashlib.md5(key.encode("utf-8")).hexdigest()

    def _parse_date(self, date_str: str) -> datetime:
        """
        Try every format in _DATE_FORMATS.
        Returns utcnow() if nothing matches.
        """
        cleaned = date_str.strip() if date_str else ""

        if not cleaned:
            return datetime.now(tz=timezone.utc)

        # Strip common noise like "Posted:", "Date:", "Reviewed on"
        cleaned = re.sub(
            r"^(posted|date|reviewed on|on|submitted)[:\s]+",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(cleaned, fmt).replace(tzinfo=timezone.utc)
            except (ValueError, AttributeError):
                continue

        logger.debug(
            "ComplaintsNormalizer: could not parse date '{}', using utcnow.", cleaned
        )
        return datetime.now(tz=timezone.utc)

    def _build_metadata(
        self,
        raw: dict,
        site_name: str,
        page_url: Optional[str],
    ) -> dict:
        return {
            "site_name":    site_name,
            "raw_date":     raw.get("date"),
            "page_url":     page_url,
            "rating":       raw.get("rating"),     # star rating if scraped
            "category":     raw.get("category"),   # complaint category if available
            "tags":         raw.get("tags", []),    # any scraped tags/labels
            "reply_count":  raw.get("reply_count"),
            "helpful_votes": raw.get("helpful_votes"),
        }

    @staticmethod
    def _clean(value: str) -> str:
        """Strip whitespace and collapse internal spaces."""
        return re.sub(r"\s+", " ", value).strip()
