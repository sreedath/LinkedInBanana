"""PlaylistPlannerAgent: Analyzes playlist data and generates visual spec for LinkedIn image."""

from __future__ import annotations

import structlog

from paperbanana.agents.base import BaseAgent
from paperbanana.core.types import DiagramType, LinkedInFormat
from paperbanana.providers.base import VLMProvider
from paperbanana.youtube.types import PlaylistData

logger = structlog.get_logger()


class PlaylistPlannerAgent(BaseAgent):
    """Analyzes a YouTube playlist and generates a detailed visual description.

    Takes PlaylistData and returns a comprehensive description of what the
    LinkedIn summary image should look like, including chosen visual format,
    layout, color scheme, and content placement.
    """

    def __init__(self, vlm_provider: VLMProvider, prompt_dir: str = "prompts"):
        super().__init__(vlm_provider, prompt_dir)

    @property
    def agent_name(self) -> str:
        return "planner"

    async def run(
        self,
        playlist_data: PlaylistData,
        linkedin_format: LinkedInFormat = LinkedInFormat.LANDSCAPE,
        custom_instructions: str = "",
    ) -> str:
        """Analyze playlist and generate a visual description.

        Args:
            playlist_data: Structured data from YouTube scraper.
            linkedin_format: Target image format (landscape or square).
            custom_instructions: Optional user instructions for image style/content.

        Returns:
            Detailed visual description for the image.
        """
        playlist_summary = playlist_data.summary()

        format_name = (
            "Landscape" if linkedin_format == LinkedInFormat.LANDSCAPE else "Square"
        )

        template = self.load_prompt("linkedin_playlist")
        prompt = self.format_prompt(
            template,
            playlist_summary=playlist_summary,
            image_format=format_name,
            width=linkedin_format.width,
            height=linkedin_format.height,
            custom_instructions=custom_instructions or "None provided.",
        )

        logger.info(
            "Running playlist planner",
            playlist_title=playlist_data.title,
            video_count=playlist_data.video_count,
            format=format_name,
        )

        description = await self.vlm.generate(
            prompt=prompt,
            temperature=0.7,
            max_tokens=4096,
        )

        logger.info("Playlist planner generated description", length=len(description))
        return description
