"""Subscription request/response schemas."""

from uuid import UUID

from pydantic import BaseModel, Field, computed_field
from soundify.models.enums import MusicSource
from soundify.utils.url import detect_source

from soundify_api.db.subscription import SubscriptionType
from soundify_api.schemas.jobs import YouTubeMusicUrl
from soundify_api.schemas.types import UTCDateTime


class SubscriptionCreate(BaseModel):
    """Request to create a subscription."""

    url: YouTubeMusicUrl
    max_items: int | None = Field(default=None, ge=1, le=10000)


class SubscriptionUpdate(BaseModel):
    """Request to update a subscription.

    Send ``max_items: null`` to remove a track limit so the whole playlist
    syncs; leave the field out to keep the current limit.
    """

    enabled: bool | None = None
    max_items: int | None = Field(default=None, ge=1, le=10000)


class SubscriptionResponse(BaseModel):
    """Subscription response."""

    id: UUID
    type: SubscriptionType
    url: str = Field(json_schema_extra={"format": "uri"})
    name: str
    enabled: bool
    max_items: int | None
    thumbnail_url: str | None = Field(default=None, json_schema_extra={"format": "uri"})
    created_at: UTCDateTime
    last_synced_at: UTCDateTime | None

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def source(self) -> MusicSource:
        """The service the subscribed playlist lives on, derived from its URL."""
        return detect_source(self.url) or MusicSource.YOUTUBE


class SubscriptionListResponse(BaseModel):
    """List of subscriptions response."""

    items: list[SubscriptionResponse]


class SyncResponse(BaseModel):
    """Response for sync operations."""

    job_ids: list[str]
