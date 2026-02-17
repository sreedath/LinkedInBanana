"""CaptionWriterAgent: Generates LinkedIn articles for playlist images."""

from __future__ import annotations

import json

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

        template = self.load_prompt("linkedin_playlist")
        prompt = self.format_prompt(
            template,
            playlist_summary=playlist_summary,
            image_description=image_description,
            playlist_url=playlist_url,
        )

        logger.info("Running caption writer", playlist_title=playlist_data.title)

        response = await self.vlm.generate(
            prompt=prompt,
            temperature=0.7,
            max_tokens=4096,
            response_format="json",
        )

        result = self._parse_response(response)
        logger.info(
            "Caption generated",
            caption_length=len(result.get("caption", "")),
        )
        return result

    def _parse_response(self, response: str) -> dict[str, str | list[str]]:
        """Parse the VLM response into caption data."""
        try:
            data = json.loads(response)
            caption = data.get("caption", "")
            description = data.get("description", "")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse caption response", error=str(e))
            caption = response.strip()
            description = ""

        # Clean up: replace literal \n with actual newlines
        caption = caption.replace("\\n", "\n")
        # Remove any other escaped special chars that would look wrong in LinkedIn
        caption = caption.replace("\\t", " ")

        return {
            "caption": caption,
            "description": description,
            "hashtags": [],
        }
