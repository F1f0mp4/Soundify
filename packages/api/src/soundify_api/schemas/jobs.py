"""Job API schemas."""

from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, Field, WithJsonSchema
from soundify import is_supported_url

from soundify_api.domain.job import Job


def validate_youtube_music_url(url: str) -> str:
    """Validate that the URL is supported by soundify.

    Uses soundify's is_supported_url() as the source of truth to ensure
    the API accepts exactly what soundify can process.
    """
    url = url.strip()
    if not is_supported_url(url):
        raise ValueError(
            "Invalid URL. Expected a YouTube, YouTube Music, or Spotify URL "
            "(e.g., https://music.youtube.com/playlist?list=..., "
            "https://youtube.com/watch?v=..., or "
            "https://open.spotify.com/album/...)"
        )
    return url


YouTubeMusicUrl = Annotated[
    str,
    AfterValidator(validate_youtube_music_url),
    WithJsonSchema({"type": "string", "format": "uri"}),
]


class CreateJobRequest(BaseModel):
    """Request to create a new sync job."""

    url: YouTubeMusicUrl = Field(
        description=(
            "YouTube, YouTube Music, or Spotify playlist, album, or track URL. "
            "Spotify links are matched to YouTube Music for the audio."
        ),
        examples=[
            "https://music.youtube.com/playlist?list=OLAK5uy_...",
            "https://www.youtube.com/watch?v=VIDEO_ID",
            "https://open.spotify.com/album/1ATL5GLyefJaxhQzSPVrLX",
        ],
    )
    max_items: int | None = Field(
        default=None,
        ge=1,
        le=10000,
        description="Maximum number of tracks to download",
    )


class JobsResponse(BaseModel):
    """Response for listing jobs."""

    jobs: list[Job]


class JobCreatedResponse(BaseModel):
    """Response when a job is created."""

    id: str
    message: Literal["Job created"] = "Job created"


class ClearJobsResponse(BaseModel):
    """Response when jobs are cleared."""

    cleared: int


class CancelJobResponse(BaseModel):
    """Response when a job is cancelled."""

    message: Literal["Job cancelled"] = "Job cancelled"


# SSE Event schemas


class SnapshotEvent(BaseModel):
    """Initial snapshot of all jobs sent on SSE connection."""

    type: Literal["snapshot"] = "snapshot"
    jobs: list[Job]


class CreatedEvent(BaseModel):
    """Emitted when a new job is created."""

    type: Literal["created"] = "created"
    job: Job


class UpdatedEvent(BaseModel):
    """Emitted when a job's status or progress changes."""

    type: Literal["updated"] = "updated"
    job: Job


class DeletedEvent(BaseModel):
    """Emitted when a job is deleted."""

    type: Literal["deleted"] = "deleted"
    jobId: str


class ClearedEvent(BaseModel):
    """Emitted when finished jobs are cleared."""

    type: Literal["cleared"] = "cleared"
    count: int
