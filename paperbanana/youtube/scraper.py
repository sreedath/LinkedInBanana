"""YouTube playlist scraper using YouTube Data API v3."""

from __future__ import annotations

import re
from typing import Optional

import structlog

from paperbanana.youtube.types import PlaylistData, VideoInfo

logger = structlog.get_logger()


def _parse_duration(iso_duration: str) -> int:
    """Parse ISO 8601 duration (PT1H2M3S) to total seconds."""
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def _extract_playlist_id(url: str) -> Optional[str]:
    """Extract playlist ID from a YouTube URL."""
    if re.match(r"^PL[\w-]+$", url):
        return url
    match = re.search(r"[?&]list=([\w-]+)", url)
    if match:
        return match.group(1)
    return None


class YouTubeScraper:
    """Scrapes YouTube playlist metadata using Data API v3."""

    def __init__(self, api_key: str):
        self._api_key = api_key
        self._service = None

    def _get_service(self):
        if self._service is None:
            from googleapiclient.discovery import build

            self._service = build("youtube", "v3", developerKey=self._api_key)
        return self._service

    async def scrape_playlist(self, url: str) -> PlaylistData:
        """Scrape a YouTube playlist and return structured data.

        Args:
            url: YouTube playlist URL or playlist ID.

        Returns:
            PlaylistData with all video metadata.

        Raises:
            ValueError: If the URL is invalid or playlist not found.
        """
        import asyncio

        playlist_id = _extract_playlist_id(url)
        if not playlist_id:
            raise ValueError(f"Could not extract playlist ID from: {url}")

        logger.info("Scraping playlist", playlist_id=playlist_id)

        # googleapiclient is sync — run in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._extract, playlist_id)

    def _extract(self, playlist_id: str) -> PlaylistData:
        """Synchronous extraction using YouTube Data API."""
        service = self._get_service()

        # Fetch playlist metadata
        playlist_meta = self._fetch_playlist_metadata(service, playlist_id)

        # Fetch all video IDs from playlist
        video_ids = self._fetch_playlist_items(service, playlist_id)

        if not video_ids:
            raise ValueError(f"Playlist {playlist_id} has no videos or is private.")

        # Fetch video details in batches of 50
        videos = self._fetch_video_details(service, video_ids)

        playlist = PlaylistData(
            playlist_id=playlist_id,
            title=playlist_meta.get("title", ""),
            description=playlist_meta.get("description", ""),
            channel_title=playlist_meta.get("channelTitle", ""),
            video_count=len(videos),
            videos=videos,
        )

        logger.info(
            "Playlist scraped",
            playlist_id=playlist_id,
            video_count=len(videos),
            total_duration=playlist.total_duration_seconds,
        )

        return playlist

    def _fetch_playlist_metadata(self, service, playlist_id: str) -> dict:
        """Fetch playlist-level metadata."""
        response = (
            service.playlists()
            .list(part="snippet", id=playlist_id)
            .execute()
        )
        items = response.get("items", [])
        if not items:
            raise ValueError(f"Playlist not found: {playlist_id}")
        return items[0]["snippet"]

    def _fetch_playlist_items(self, service, playlist_id: str) -> list[str]:
        """Fetch all video IDs from a playlist, handling pagination."""
        video_ids: list[str] = []
        next_page_token = None

        while True:
            request = service.playlistItems().list(
                part="contentDetails",
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token,
            )
            response = request.execute()

            for item in response.get("items", []):
                vid_id = item["contentDetails"]["videoId"]
                video_ids.append(vid_id)

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        return video_ids

    def _fetch_video_details(self, service, video_ids: list[str]) -> list[VideoInfo]:
        """Fetch detailed info for videos in batches of 50."""
        videos: list[VideoInfo] = []

        for i in range(0, len(video_ids), 50):
            batch = video_ids[i : i + 50]
            response = (
                service.videos()
                .list(
                    part="snippet,contentDetails,statistics,topicDetails",
                    id=",".join(batch),
                )
                .execute()
            )

            for item in response.get("items", []):
                snippet = item.get("snippet", {})
                content = item.get("contentDetails", {})
                stats = item.get("statistics", {})
                topics = item.get("topicDetails", {})

                topic_cats = []
                for url in topics.get("topicCategories", []):
                    name = url.rsplit("/", 1)[-1].replace("_", " ")
                    topic_cats.append(name)

                videos.append(
                    VideoInfo(
                        video_id=item["id"],
                        title=snippet.get("title", ""),
                        description=snippet.get("description", ""),
                        duration_seconds=_parse_duration(
                            content.get("duration", "PT0S")
                        ),
                        view_count=int(stats.get("viewCount", 0)),
                        channel_title=snippet.get("channelTitle", ""),
                        published_at=snippet.get("publishedAt", ""),
                        tags=snippet.get("tags", []),
                        topic_categories=topic_cats,
                    )
                )

        return videos
