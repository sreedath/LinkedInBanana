"""Request/response Pydantic schemas for the API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PlaylistRequest(BaseModel):
    """Request to generate a LinkedIn image from a playlist."""

    playlist_url: str = Field(description="YouTube playlist URL")
    format: str = Field(default="landscape", description="Image format: landscape or square")
    generate_caption: bool = Field(default=True, description="Whether to generate a LinkedIn caption")
    custom_instructions: str = Field(default="", description="Custom instructions for image generation")
    google_api_key: str = Field(default="", description="Google Gemini API key")
    youtube_api_key: str = Field(default="", description="YouTube Data API key")


class ApiKeysRequest(BaseModel):
    """Request to save API keys."""

    google_api_key: str = Field(default="", description="Google Gemini API key")
    youtube_api_key: str = Field(default="", description="YouTube Data API key")


class ApiKeysResponse(BaseModel):
    """Response with stored API keys."""

    google_api_key: str = ""
    youtube_api_key: str = ""


class JobCreatedResponse(BaseModel):
    """Response when a job is created."""

    job_id: str
    status: str = "queued"


class PlaylistInfoResponse(BaseModel):
    """Playlist metadata shown during progress."""

    title: str = ""
    channel: str = ""
    video_count: int = 0
    total_duration_minutes: int = 0
    total_views: int = 0
    videos: list[dict] = Field(default_factory=list)


class IterationImageResponse(BaseModel):
    """A single iteration image."""

    iteration: int
    image_url: str


class JobResultResponse(BaseModel):
    """Result data when a job completes."""

    image_url: str
    iteration_images: list[IterationImageResponse] = Field(default_factory=list)
    caption: str = ""
    description: str = ""
    hashtags: list[str] = Field(default_factory=list)
    playlist_title: str = ""
    video_count: int = 0


class JobStatusResponse(BaseModel):
    """Response for job status polling."""

    job_id: str
    status: str
    phase: str = ""
    message: str = ""
    progress: float = 0.0
    playlist_info: Optional[PlaylistInfoResponse] = None
    result: Optional[JobResultResponse] = None
    error: Optional[str] = None


class LinkedInPostRequest(BaseModel):
    """Request to post to LinkedIn immediately."""

    caption: str = Field(description="The post text")
    image_path: Optional[str] = Field(default=None, description="Path to image file to attach")


class LinkedInScheduleRequest(BaseModel):
    """Request to schedule a LinkedIn post."""

    caption: str = Field(description="The post text")
    image_path: Optional[str] = Field(default=None, description="Path to image file to attach")
    scheduled_at: str = Field(description="ISO 8601 datetime for when to publish")
