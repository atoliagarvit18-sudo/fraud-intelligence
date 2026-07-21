"""
app/services/preprocessing.py

Cleans raw post text before classification or embedding.
Operations: language detection, emoji removal, URL removal, whitespace normalisation.

No database. No AI. No network calls.
"""

import re
from typing import Optional

from loguru import logger

from app.models.raw_post import RawPost

# ---------------------------------------------------------------------------
# Compiled regex patterns (compiled once at import time for performance)
# ---------------------------------------------------------------------------

_URL_RE       = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_EMOJI_RE     = re.compile(
    "["
    "\U0001F600-\U0001F64F"   # emoticons
    "\U0001F300-\U0001F5FF"   # symbols & pictographs
    "\U0001F680-\U0001F6FF"   # transport & map
    "\U0001F1E0-\U0001F1FF"   # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001f926-\U0001f937"
    "\U00010000-\U0010ffff"
    "\u2640-\u2642"
    "\u2600-\u2B55"
    "\u200d\u23cf\u23e9\u231a\ufe0f\u3030"
    "]+",
    flags=re.UNICODE,
)
_WHITESPACE_RE = re.compile(r"\s+")
_SPECIAL_RE    = re.compile(r"[^\w\s.,!?;:()\-'\"]", re.UNICODE)


class TextPreprocessor:
    """
    Cleans and normalises raw text from collected posts.

    Usage:
        preprocessor = TextPreprocessor()
        result = preprocessor.process(post)
        # result: {"clean_text": str, "language": str, "original_length": int, ...}
    """

    def process(self, post: RawPost) -> dict:
        """
        Clean the text of a RawPost and detect its language.

        Returns a dict ready to be merged into a processed_post document:
            {
                "raw_post_id":      str,
                "original_text":    str,
                "clean_text":       str,
                "language":         str | None,
                "original_length":  int,
                "clean_length":     int,
                "had_urls":         bool,
                "had_emojis":       bool,
            }
        """
        original = post.text or ""
        original_length = len(original)

        had_urls   = bool(_URL_RE.search(original))
        had_emojis = bool(_EMOJI_RE.search(original))

        step1 = self._remove_urls(original)
        step2 = self._remove_emojis(step1)
        step3 = self._remove_special_chars(step2)
        clean = self._normalise_whitespace(step3)

        language = self._detect_language(clean) or post.language

        logger.debug(
            "TextPreprocessor: post={} | {} → {} chars | lang={}",
            post.source_id, original_length, len(clean), language,
        )

        return {
            "raw_post_id":     post.source_id,
            "original_text":   original,
            "clean_text":      clean,
            "language":        language,
            "original_length": original_length,
            "clean_length":    len(clean),
            "had_urls":        had_urls,
            "had_emojis":      had_emojis,
            "source":          post.source,
            "platform":        post.platform,
            "timestamp":       post.timestamp,
            "collected_at":    post.collected_at,
        }

    # -----------------------------------------------------------------------
    # Cleaning steps
    # -----------------------------------------------------------------------

    def _remove_urls(self, text: str) -> str:
        return _URL_RE.sub(" ", text)

    def _remove_emojis(self, text: str) -> str:
        return _EMOJI_RE.sub(" ", text)

    def _remove_special_chars(self, text: str) -> str:
        """Remove characters that are neither word chars nor common punctuation."""
        return _SPECIAL_RE.sub(" ", text)

    def _normalise_whitespace(self, text: str) -> str:
        return _WHITESPACE_RE.sub(" ", text).strip()

    # -----------------------------------------------------------------------
    # Language detection
    # -----------------------------------------------------------------------

    def _detect_language(self, text: str) -> Optional[str]:
        """
        Detect language using langdetect.
        Returns ISO 639-1 code (e.g. 'en', 'hi') or None on failure.
        langdetect is optional — returns None gracefully if not installed.
        """
        if not text or len(text) < 20:
            return None
        try:
            from langdetect import detect, LangDetectException  # pyright: ignore[reportMissingImports]
            return detect(text)
        except Exception:
            return None
