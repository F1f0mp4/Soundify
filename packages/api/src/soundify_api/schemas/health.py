"""Health check schemas."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response model."""

    status: Literal["healthy"]
