"""Data types for YouTube playlist scraping."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class VideoInfo(BaseModel):
    """Metadata for a single YouTube video."""

    video_id: str
    title: str
    description: str = ""
    duration_seconds: int = 0
    view_count: int = 0
    channel_title: str = ""
    published_at: str = ""
    tags: list[str] = Field(default_factory=list)
    topic_categories: list[str] = Field(default_factory=list)


class PlaylistData(BaseModel):
    """Structured data from a YouTube playlist."""

    playlist_id: str
    title: str
    description: str = ""
    channel_title: str = ""
    video_count: int = 0
    videos: list[VideoInfo] = Field(default_factory=list)

    @property
    def total_duration_seconds(self) -> int:
        return sum(v.duration_seconds for v in self.videos)

    @property
    def total_views(self) -> int:
        return sum(v.view_count for v in self.videos)

    @property
    def all_topics(self) -> list[str]:
        topics: list[str] = []
        seen: set[str] = set()
        for v in self.videos:
            for t in v.topic_categories:
                if t not in seen:
                    seen.add(t)
                    topics.append(t)
        return topics

    def summary(self) -> str:
        """Generate a text summary of the playlist for AI consumption."""
        hours = self.total_duration_seconds // 3600
        minutes = (self.total_duration_seconds % 3600) // 60

        lines = [
            f"# Playlist: {self.title}",
            f"**Channel**: {self.channel_title}",
            f"**Videos**: {self.video_count}",
            f"**Total Duration**: {hours}h {minutes}m",
            f"**Total Views**: {self.total_views:,}",
        ]

        if self.description:
            lines.append(f"\n**Description**: {self.description}")

        if self.all_topics:
            lines.append(f"\n**Topics**: {', '.join(self.all_topics)}")

        lines.append("\n## Videos\n")
        for i, v in enumerate(self.videos, 1):
            dur_m = v.duration_seconds // 60
            dur_s = v.duration_seconds % 60
            lines.append(f"{i}. **{v.title}** ({dur_m}:{dur_s:02d})")
            if v.description:
                # First line of description only
                first_line = v.description.split("\n")[0][:200]
                lines.append(f"   {first_line}")

        return "\n".join(lines)
