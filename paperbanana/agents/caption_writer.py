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
                caption = data.get("caption", "")
                description = data.get("description", "")
        except (json.JSONDecodeError, ValueError) as e:
            # Try extracting JSON between first { and last }
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end > start:
                try:
                    data = json.loads(text[start : end + 1])
                    if isinstance(data, dict):
                        caption = data.get("caption", "")
                        description = data.get("description", "")
                except (json.JSONDecodeError, ValueError):
                    pass

            if not caption:
                logger.warning("Failed to parse caption response", error=str(e))
                caption = text

        # Clean up: replace literal \n with actual newlines
        caption = caption.replace("\\n", "\n")
        caption = caption.replace("\\t", " ")

        return {
            "caption": caption,
            "description": description,
            "hashtags": [],
        }
