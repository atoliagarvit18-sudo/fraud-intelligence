"""
app/normalizers/telegram.py

Converts a Telethon Message object into a RawPost.
No MongoDB. No network calls. Normalization only.
"""

from loguru import logger
from telethon.tl.types import Message

from app.models.raw_post import RawPost


class TelegramNormalizer:
    """
    Converts a raw Telethon Message into a standardized RawPost.

    Usage:
        normalizer = TelegramNormalizer()
        post = normalizer.normalize(message, channel_name="ScamAlertIndia")
    """

    def normalize(self, message: Message, channel_name: str) -> RawPost | None:
        """
        Map a Telethon Message object to a RawPost.

        Args:
            message:      A Telethon Message object from iter_messages().
            channel_name: The Telegram channel or group username/title.

        Returns:
            A RawPost instance ready to be passed to StorageService.
        """
        author = self._extract_author(message)
        text = (message.message or "").strip()

        if not text:
            logger.debug(
                "TelegramNormalizer: skipping empty message {}.", message.id
            )
            return None

        if message.date is None:
            logger.warning(
                "TelegramNormalizer: skipping message {} — no timestamp.", message.id
            )
            return None

        post = RawPost(
            source="telegram",
            source_id=str(message.id),
            title=None,
            text=text,
            author=author,
            timestamp=message.date,
            url=None,
            platform=channel_name,
            language=None,
            metadata=self._build_metadata(message),
        )

        logger.debug(
            "TelegramNormalizer: normalized message {} from '{}'.",
            message.id,
            channel_name,
        )

        return post

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _extract_author(self, message: Message) -> str | None:
        """Return the sender's username or display name, if available."""
        sender = getattr(message, "sender", None)
        if sender is None:
            return None

        # Prefer username (e.g. @scam_hunter), fall back to first name
        username = getattr(sender, "username", None)
        if username:
            return f"@{username}"

        first = getattr(sender, "first_name", None) or ""
        last  = getattr(sender, "last_name",  None) or ""
        full  = f"{first} {last}".strip()
        return full or None

    def _build_metadata(self, message: Message) -> dict:
        """Collect Telegram-specific fields that don't fit the RawPost schema."""
        replies = getattr(message, "replies", None)
        chat_id = getattr(message, "chat_id", None)

        return {
            "views":        getattr(message, "views",    None),
            "forwards":     getattr(message, "forwards", None),
            "reply_count":  getattr(replies, "replies",  None) if replies else None,
            "chat_id":      chat_id,
            "message_id":   message.id,
            "is_forwarded": message.fwd_from is not None,
            "has_media":    message.media is not None,
            "grouped_id":   getattr(message, "grouped_id", None),
        }
