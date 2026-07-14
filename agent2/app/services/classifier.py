"""
app/services/classifier.py

Classifies cleaned post text using the Groq API (llama-3.3-70b-versatile).
Extracts: scam type, confidence, summary, and named entities.

No database. Only classification logic.
"""

import json
from typing import Optional

from groq import Groq
from loguru import logger

from app.config.settings import settings

# ---------------------------------------------------------------------------
# Groq model to use
# ---------------------------------------------------------------------------

_MODEL = "llama-3.3-70b-versatile"

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are a financial fraud intelligence analyst.
Your job is to analyze text from social media and complaint sites and determine whether it describes a fraud or scam.

Always respond with a single valid JSON object. No markdown. No explanation outside the JSON.

JSON schema:
{
  "is_fraud": true | false,
  "scam_type": "<one of: investment_scam | phishing | romance_scam | fake_broker | ponzi | crypto_fraud | identity_theft | job_scam | loan_fraud | other | not_fraud>",
  "confidence": <float 0.0 to 1.0>,
  "summary": "<1-2 sentence summary of what the post describes>",
  "entities": {
    "platforms": ["<app/website names mentioned>"],
    "amounts":   ["<monetary amounts mentioned>"],
    "locations": ["<geographic locations mentioned>"],
    "names":     ["<person or company names mentioned>"]
  }
}"""

_USER_PROMPT_TEMPLATE = """Analyze the following post and return the JSON classification.

Source: {source}
Platform: {platform}

Text:
{text}"""


class PostClassifier:
    """
    Classifies a post using Groq LLM.

    Usage:
        classifier = PostClassifier()
        result = classifier.classify(clean_text, source="reddit", platform="Scams")
    """

    def __init__(self) -> None:
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set in .env")
        self.client = Groq(api_key=settings.GROQ_API_KEY)

    def classify(
        self,
        clean_text: str,
        source: str = "",
        platform: str = "",
    ) -> dict:
        """
        Classify a cleaned post text.

        Returns:
            {
                "is_fraud":   bool,
                "scam_type":  str,
                "confidence": float,
                "summary":    str,
                "entities":   dict,
                "error":      str | None,   # set only on failure
            }
        """
        if not clean_text or len(clean_text.strip()) < 10:
            logger.debug("PostClassifier: skipping — text too short.")
            return self._empty_result(error="text too short")

        try:
            prompt = _USER_PROMPT_TEMPLATE.format(
                source=source or "unknown",
                platform=platform or "unknown",
                text=clean_text[:3000],    # Groq has token limits
            )

            response = self.client.chat.completions.create(
                model=_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                temperature=0.1,     # low temp for deterministic classification
                max_tokens=512,
            )

            content = response.choices[0].message.content

            if content is None:
                raise RuntimeError("Groq returned an empty response.")

            raw = content.strip()
            result = self._parse_response(raw)

            logger.debug(
                "PostClassifier: is_fraud={} scam_type={} confidence={}",
                result["is_fraud"], result["scam_type"], result["confidence"],
            )
            return result

        except Exception as e:
            logger.error("PostClassifier.classify failed: {}", e)
            return self._empty_result(error=str(e))

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    def _parse_response(self, raw: str) -> dict:
        """Parse Groq JSON response, with fallback for malformed output."""
        try:
            data = json.loads(raw)
            return {
                "is_fraud":   bool(data.get("is_fraud", False)),
                "scam_type":  str(data.get("scam_type", "other")),
                "confidence": float(data.get("confidence", 0.0)),
                "summary":    str(data.get("summary", "")),
                "entities":   data.get("entities", {}),
                "error":      None,
            }
        except json.JSONDecodeError:
            logger.warning("PostClassifier: could not parse JSON response: {}", raw[:200])
            return self._empty_result(error="invalid json from llm")

    def _empty_result(self, error: Optional[str] = None) -> dict:
        return {
            "is_fraud":   False,
            "scam_type":  "other",
            "confidence": 0.0,
            "summary":    "",
            "entities":   {},
            "error":      error,
        }
