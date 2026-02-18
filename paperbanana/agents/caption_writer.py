"""CaptionWriterAgent: Generates LinkedIn articles for playlist images."""

from __future__ import annotations

import json
import re

import structlog

from paperbanana.agents.base import BaseAgent
from paperbanana.providers.base import VLMProvider
from paperbanana.youtube.types import PlaylistData

logger = structlog.get_logger()


class CaptionWriterAgent(BaseAgent):
    """Generates LinkedIn articles for playlist summary images.

    Takes playlist data and the image description, returns a structured
    LinkedIn article with proper formatting.
    """

    def __init__(self, vlm_provider: VLMProvider, prompt_dir: str = "prompts"):
        super().__init__(vlm_provider, prompt_dir)

    @property
    def agent_name(self) -> str:
        return "caption_writer"

    def _build_video_links(self, playlist_data: PlaylistData, max_videos: int = 10) -> str:
        """Build a formatted list of video links for the prompt.

        If the playlist has more videos than max_videos, select the top ones
        by view count while preserving original playlist order.
        """
        videos = playlist_data.videos
        if not videos:
            return "No individual video links available."

        if len(videos) > max_videos:
            # Select top videos by view count, then restore original order
            indexed = list(enumerate(videos))
            top_by_views = sorted(indexed, key=lambda x: x[1].view_count, reverse=True)[:max_videos]
            top_by_views.sort(key=lambda x: x[0])  # Restore playlist order
            selected = [v for _, v in top_by_views]
            truncated = True
        else:
            selected = videos
            truncated = False

        lines = []
        for v in selected:
            url = f"https://www.youtube.com/watch?v={v.video_id}"
            lines.append(f"- {v.title}: {url}")

        if truncated:
            lines.append(
                f"\n(Showing {len(selected)} of {len(videos)} videos. "
                "See the full playlist for all videos.)"
            )

        return "\n".join(lines)

    async def run(
        self,
        playlist_data: PlaylistData,
        image_description: str,
        playlist_url: str = "",
    ) -> dict[str, str | list[str]]:
        """Generate a LinkedIn article for the playlist image.

        Args:
            playlist_data: Structured data from YouTube scraper.
            image_description: The visual description used to generate the image.
            playlist_url: Original YouTube playlist URL for linking.

        Returns:
            Dict with keys: caption, description, hashtags.
        """
        playlist_summary = playlist_data.summary()
        video_links = self._build_video_links(playlist_data)

        template = self.load_prompt("linkedin_playlist")
        prompt = self.format_prompt(
            template,
            playlist_summary=playlist_summary,
            image_description=image_description,
            playlist_url=playlist_url,
            video_links=video_links,
        )

        logger.info("Running caption writer", playlist_title=playlist_data.title)

        response = await self.vlm.generate(
            prompt=prompt,
            temperature=0.7,
            max_tokens=8192,
            response_format="json",
        )

        result = self._parse_response(response)
        logger.info(
            "Caption generated",
            caption_length=len(result.get("caption", "")),
        )
        return result

    def _extract_text(self, value: object) -> str:
        """Recursively extract text from a value that may be a nested dict or list."""
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            # Try common keys first
            for key in ("caption", "text", "content", "body"):
                if key in value:
                    return self._extract_text(value[key])
            # Concatenate ALL values to avoid losing sections
            parts = [self._extract_text(v) for v in value.values()]
            return "\n\n".join(p for p in parts if p)
        if isinstance(value, list):
            parts = [self._extract_text(item) for item in value]
            return "\n\n".join(p for p in parts if p)
        return str(value) if value else ""

    def _parse_response(self, response: str) -> dict[str, str | list[str]]:
        """Parse the VLM response into caption data."""
        caption = ""
        description = ""

        # Strip markdown code fences if present
        text = response.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json) and last line (```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        try:
            data = json.loads(text)
            if isinstance(data, dict):
                caption = self._extract_text(data.get("caption", ""))
                description = self._extract_text(data.get("description", ""))
        except (json.JSONDecodeError, ValueError) as e:
            # Try extracting JSON between first { and last }
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end > start:
                try:
                    data = json.loads(text[start : end + 1])
                    if isinstance(data, dict):
                        caption = self._extract_text(data.get("caption", ""))
                        description = self._extract_text(data.get("description", ""))
                except (json.JSONDecodeError, ValueError):
                    pass

            if not caption:
                logger.warning("Failed to parse caption response", error=str(e))
                caption = text

        # Clean up: replace literal \n with actual newlines
        caption = caption.replace("\\n", "\n")
        caption = caption.replace("\\t", " ")

        # Strip residual leading/trailing quotes
        if len(caption) >= 2 and caption[0] == '"' and caption[-1] == '"':
            caption = caption[1:-1]

        # Final safety net: if caption still looks like JSON, extract text from it
        stripped = caption.strip()
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                nested = json.loads(stripped)
                extracted = self._extract_text(nested)
                if extracted and not extracted.startswith("{"):
                    caption = extracted
            except (json.JSONDecodeError, ValueError):
                pass

        # Normalize excessive blank lines (3+ newlines -> 2)
        caption = re.sub(r"\n{3,}", "\n\n", caption)

        return {
            "caption": caption.strip(),
            "description": description,
            "hashtags": [],
        }
