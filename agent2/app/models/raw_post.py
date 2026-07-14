"""
app/models/raw_post.py

Pydantic model for a raw post collected from Reddit, Telegram, or complaint websites.
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class RawPost(BaseModel):
    source: str = Field(description="Platform the post was collected from. E.g. 'reddit', 'telegram', 'consumer_complaints'")
    source_id: str = Field(description="Unique ID of the post on the source platform")
    title: Optional[str] = Field(default=None, description="Post title, if available (e.g. Reddit post title)")
    text: str = Field(description="Main body text of the post")
    author: Optional[str] = Field(default=None, description="Username or display name of the author")
    timestamp: datetime = Field(description="When the post was originally published")
    collected_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc), description="When this collector fetched the post")
    url: Optional[str] = Field(default=None, description="Direct URL to the original post")
    location: Optional[str] = Field(default=None, description="Geographic location mentioned or associated with the post")
    platform: Optional[str] = Field(default=None, description="Sub-platform or channel. E.g. subreddit name, Telegram channel name")
    language: Optional[str] = Field(default=None, description="Detected or declared language of the post. E.g. 'en', 'hi'")
    metadata: dict = Field(default_factory=dict, description="Any extra source-specific fields that don't fit the schema above")
