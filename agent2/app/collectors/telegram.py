"""
app/collectors/telegram.py

Handles Telegram authentication using Telethon.
Creates and reuses a session file so login is only needed once.

This module authenticates the user AND runs the message-collection loop.
It does NOT perform NLP, classification, or direct MongoDB writes.
"""

import asyncio
from pathlib import Path

from loguru import logger
from telethon import TelegramClient
from telethon.errors import (
    ApiIdInvalidError,
    AuthKeyError,
    FloodWaitError,
    PhoneCodeInvalidError,
    RPCError,
    SessionPasswordNeededError,
)
from telethon.tl.types import MessageService

from app.config.constants import METADATA, POLL_INTERVAL_SECONDS, TELEGRAM_CHANNELS
from app.config.settings import settings
from app.database.mongo import get_collection
from app.normalizers.telegram import TelegramNormalizer
from app.services.storage import StorageService

# ------------------------------------------------------------------
# Session Configuration
# ------------------------------------------------------------------

SESSION_DIR = Path("sessions")
SESSION_DIR.mkdir(exist_ok=True)

SESSION_NAME = str(SESSION_DIR / "telegram")


class TelegramCollector:
    """
    Handles Telegram authentication.

    Example
    -------
    >>> collector = TelegramCollector()
    >>> await collector.connect()
    """

    def __init__(self):

        if (
            settings.TELEGRAM_API_ID == 0
            or not settings.TELEGRAM_API_HASH
        ):
            raise ValueError(
                "TELEGRAM_API_ID and TELEGRAM_API_HASH "
                "must be defined inside .env"
            )

        self.client = TelegramClient(
            SESSION_NAME,
            settings.TELEGRAM_API_ID,
            settings.TELEGRAM_API_HASH,
        )

    async def connect(self):
        """
        Authenticate the Telegram client.

        First run:
            - asks for phone number
            - asks for OTP
            - asks for 2FA password (if enabled)

        Later runs:
            - reuses telegram.session automatically.
        """

        try:

            logger.info("Connecting to Telegram...")

            await self.client.connect()

            # Existing session
            if await self.client.is_user_authorized():

                from telethon.tl.types import User

                me = await self.client.get_me()

                if isinstance(me, User):
                    logger.success(
                        "Already logged in as {} (@{})",
                        me.first_name or "",
                        me.username or "No Username",
                    )
                else:
                    logger.success("Telegram session already active.")

                return

            # ------------------------
            # First Login
            # ------------------------

            phone = input(
                "Enter Telegram phone number (e.g. +919509083063): "
            ).strip().replace(" ", "").replace("-", "")

            # Automatically format phone number if '+' prefix or country code was omitted
            if not phone.startswith("+"):
                if len(phone) == 10 and phone.isdigit():
                    phone = "+91" + phone
                    logger.info("Automatically formatted phone number to: {}", phone)
                elif len(phone) > 10 and phone.isdigit():
                    phone = "+" + phone
                    logger.info("Automatically formatted phone number to: {}", phone)
                else:
                    logger.warning("Phone number '{}' does not start with '+'. Ensure international format (e.g., +91xxxxxxxxx).", phone)

            logger.info("Sending OTP to {}...", phone)

            await self.client.send_code_request(phone)

            try:

                otp = input("Enter OTP: ").strip()

                await self.client.sign_in(phone, otp)

            except SessionPasswordNeededError:

                logger.info("Two-Factor Authentication detected.")

                password = input(
                    "Enter your Telegram 2FA password: "
                ).strip()

                await self.client.sign_in(password=password)

            from telethon.tl.types import User

            me = await self.client.get_me()

            if not isinstance(me, User):
                raise RuntimeError("Unable to retrieve Telegram user.")

            logger.success(
                "Login successful!"
            )

            logger.success(
                "Logged in as {} (@{})",
                me.first_name,
                me.username if me.username else "No Username",
            )

            logger.info(
                "Session saved to: {}.session",
                SESSION_NAME,
            )

        except ApiIdInvalidError:

            logger.error(
                "Invalid TELEGRAM_API_ID or TELEGRAM_API_HASH."
            )
            raise

        except PhoneCodeInvalidError:

            logger.error("Invalid OTP entered.")
            raise

        except AuthKeyError:

            logger.error(
                "Session file is corrupted. "
                "Delete the sessions folder and login again."
            )
            raise

        except Exception as e:

            logger.exception(e)
            raise

    async def disconnect(self) -> None:
        """
        Disconnect Telegram client.
        """
        if self.client.is_connected():
            res = self.client.disconnect()
            if hasattr(res, "__await__"):
                await res  # type: ignore
            logger.info("Telegram client disconnected.")

    # -----------------------------------------------------------------------
    # Collection loop
    # -----------------------------------------------------------------------

    async def collect_once(self) -> int:
        """
        One sweep: fetch new messages from every configured channel,
        normalise them, and persist via StorageService.

        Returns the total number of newly stored posts across all channels.
        """
        if not self.client.is_connected():
            await self.connect()

        normalizer = TelegramNormalizer()
        storage    = StorageService()
        total_stored = 0

        for channel in TELEGRAM_CHANNELS:
            try:
                last_id = self._get_checkpoint(channel)
                logger.info("Collecting '{}' (since message id={}).", channel, last_id)

                posts = []
                newest_id = last_id

                async for message in self.client.iter_messages(
                    channel,
                    min_id=last_id,       # fetch only messages newer than checkpoint
                    reverse=True,         # oldest-first so checkpoint advances correctly
                ):
                    # Skip Telegram service messages (joins, pins, calls, …)
                    if isinstance(message, MessageService):
                        continue

                    post = normalizer.normalize(message, channel_name=channel)
                    if post is None:
                        continue

                    posts.append(post)
                    newest_id = max(newest_id, message.id)

                if posts:
                    result = storage.store(posts)
                    total_stored += result["inserted"]
                    logger.info(
                        "'{}': stored={}, duplicates={}, failed={}.",
                        channel,
                        result["inserted"],
                        result["duplicates"],
                        result["failed"],
                    )

                # Advance checkpoint only when messages were fetched
                if newest_id > last_id:
                    self._update_checkpoint(channel, newest_id)

            except FloodWaitError as e:
                logger.warning(
                    "FloodWait on '{}': sleeping {}s.", channel, e.seconds
                )
                await asyncio.sleep(e.seconds)

            except RPCError as e:
                logger.error("RPCError on '{}': {} — skipping channel.", channel, e)

            except Exception as e:
                logger.error("Unexpected error on '{}': {} — skipping channel.", channel, e)

        logger.info("collect_once complete. Total stored: {}.", total_stored)
        return total_stored

    async def run(self) -> None:
        """
        Continuous polling loop.
        Calls collect_once() then sleeps for POLL_INTERVAL_SECONDS, forever.
        """
        logger.info(
            "Starting Telegram polling loop (interval={}s).", POLL_INTERVAL_SECONDS
        )
        while True:
            try:
                await self.collect_once()
            except Exception as e:
                logger.error("collect_once raised an unexpected error: {}", e)

            logger.debug("Sleeping {}s before next sweep.", POLL_INTERVAL_SECONDS)
            await asyncio.sleep(POLL_INTERVAL_SECONDS)

    # -----------------------------------------------------------------------
    # Checkpoint helpers  (read / write last processed message id per channel)
    # -----------------------------------------------------------------------

    def _get_checkpoint(self, channel: str) -> int:
        """
        Return the last processed message id for a channel.
        Returns 0 if no checkpoint exists yet (fetch all available messages).
        """
        col = get_collection(METADATA)
        doc = col.find_one({"key": f"telegram_checkpoint_{channel}"})
        return doc["last_message_id"] if doc else 0

    def _update_checkpoint(self, channel: str, last_message_id: int) -> None:
        """
        Persist the last processed message id for a channel to MongoDB metadata.
        Uses upsert so it works on both first write and subsequent updates.
        """
        col = get_collection(METADATA)
        col.update_one(
            {"key": f"telegram_checkpoint_{channel}"},
            {"$set": {"last_message_id": last_message_id}},
            upsert=True,
        )
        logger.debug(
            "Checkpoint updated: channel='{}', last_message_id={}.",
            channel,
            last_message_id,
        )