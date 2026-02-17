"""LinkedIn Playlist Pipeline: Generates LinkedIn-ready images from YouTube playlists."""

from __future__ import annotations

import datetime
import time
from pathlib import Path
from typing import Any, Callable, Optional

import structlog

from paperbanana.agents.caption_writer import CaptionWriterAgent
from paperbanana.agents.critic import CriticAgent
from paperbanana.agents.playlist_planner import PlaylistPlannerAgent
from paperbanana.agents.stylist import StylistAgent
from paperbanana.agents.visualizer import VisualizerAgent
from paperbanana.core.config import Settings
from paperbanana.core.types import (
    DiagramType,
    IterationRecord,
    LinkedInFormat,
    PlaylistGenerationOutput,
    RunMetadata,
)
from paperbanana.core.utils import ensure_dir, generate_run_id, load_image, save_image, save_json
from paperbanana.guidelines.linkedin import DEFAULT_LINKEDIN_GUIDELINES
from paperbanana.providers.registry import ProviderRegistry
from paperbanana.youtube.scraper import YouTubeScraper
from paperbanana.youtube.types import PlaylistData

logger = structlog.get_logger()


class LinkedInPlaylistPipeline:
    """Orchestrates LinkedIn image generation from YouTube playlists.

    Pipeline stages:
    1. Scrape: YouTubeScraper fetches playlist metadata
    2. Plan: PlaylistPlannerAgent analyzes content, chooses visual format
    3. Style: StylistAgent refines for LinkedIn aesthetics
    4. Generate: VisualizerAgent creates the image
    5. Critique: CriticAgent evaluates (iterative with step 4)
    6. Caption: CaptionWriterAgent generates LinkedIn text
    """

    def __init__(
        self,
        settings: Optional[Settings] = None,
        on_progress: Optional[Callable[[str, str], None]] = None,
    ):
        """Initialize the pipeline.

        Args:
            settings: Configuration settings. If None, loads from env/defaults.
            on_progress: Optional callback(phase, message) for progress updates.
        """
        self.settings = settings or Settings()
        self.run_id = generate_run_id()
        self._on_progress = on_progress
        self._playlist_url = ""

        # Initialize providers
        self._vlm = ProviderRegistry.create_vlm(self.settings)
        self._image_gen = ProviderRegistry.create_image_gen(self.settings)

        # Initialize agents
        prompt_dir = self._find_prompt_dir()
        self.playlist_planner = PlaylistPlannerAgent(self._vlm, prompt_dir=prompt_dir)
        self.stylist = StylistAgent(
            self._vlm, guidelines=DEFAULT_LINKEDIN_GUIDELINES, prompt_dir=prompt_dir
        )
        self.visualizer = VisualizerAgent(
            self._image_gen,
            self._vlm,
            prompt_dir=prompt_dir,
            output_dir=str(self._run_dir),
        )
        self.critic = CriticAgent(self._vlm, prompt_dir=prompt_dir)
        self.caption_writer = CaptionWriterAgent(self._vlm, prompt_dir=prompt_dir)

        logger.info(
            "LinkedIn pipeline initialized",
            run_id=self.run_id,
            vlm=getattr(self._vlm, "name", "custom"),
            image_gen=getattr(self._image_gen, "name", "custom"),
        )

    @property
    def _run_dir(self) -> Path:
        return ensure_dir(Path(self.settings.output_dir) / self.run_id)

    def _find_prompt_dir(self) -> str:
        candidates = [
            Path("prompts"),
            Path(__file__).parent.parent.parent / "prompts",
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return "prompts"

    def _progress(self, phase: str, message: str) -> None:
        """Report progress to the callback if set."""
        logger.info(f"[{phase}] {message}")
        if self._on_progress:
            self._on_progress(phase, message)

    async def scrape_playlist(self, url: str) -> PlaylistData:
        """Scrape a YouTube playlist.

        Args:
            url: YouTube playlist URL.

        Returns:
            PlaylistData with video metadata.
        """
        api_key = self.settings.youtube_api_key
        if not api_key:
            raise ValueError(
                "YOUTUBE_API_KEY is required. Get one at https://console.cloud.google.com"
            )

        self._progress("scraping", "Fetching playlist metadata from YouTube...")
        self._playlist_url = url
        scraper = YouTubeScraper(api_key)
        playlist_data = await scraper.scrape_playlist(url)
        self._progress(
            "scraping",
            f"Found {playlist_data.video_count} videos in '{playlist_data.title}'",
        )
        return playlist_data

    async def generate(
        self,
        playlist_data: PlaylistData,
        linkedin_format: LinkedInFormat = LinkedInFormat.LANDSCAPE,
        generate_caption: bool = True,
        custom_instructions: str = "",
    ) -> PlaylistGenerationOutput:
        """Run the full LinkedIn image generation pipeline.

        Args:
            playlist_data: Scraped playlist data.
            linkedin_format: Image format (landscape or square).
            generate_caption: Whether to generate a LinkedIn caption.
            custom_instructions: Optional user instructions for image style/content.

        Returns:
            PlaylistGenerationOutput with image path, caption, and metadata.
        """
        total_start = time.perf_counter()
        playlist_summary = playlist_data.summary()

        # ── Stage 1: Plan ─────────────────────────────────────
        self._progress("planning", "Analyzing playlist content and choosing visual format...")
        planning_start = time.perf_counter()
        description = await self.playlist_planner.run(
            playlist_data=playlist_data,
            linkedin_format=linkedin_format,
            custom_instructions=custom_instructions,
        )
        planning_seconds = time.perf_counter() - planning_start
        self._progress("planning", "Visual format and layout planned")

        # ── Stage 2: Style ────────────────────────────────────
        self._progress("generating", "Applying LinkedIn styling...")
        styling_start = time.perf_counter()
        optimized_description = await self.stylist.run(
            description=description,
            guidelines=DEFAULT_LINKEDIN_GUIDELINES,
            source_context=playlist_summary,
            caption=playlist_data.title,
            diagram_type=DiagramType.LINKEDIN_PLAYLIST,
        )
        styling_seconds = time.perf_counter() - styling_start

        # Save planning outputs
        save_json(
            {
                "playlist_summary": playlist_summary,
                "initial_description": description,
                "optimized_description": optimized_description,
            },
            self._run_dir / "planning.json",
        )

        # ── Stage 3: Generate + Critique (iterative) ─────────
        current_description = optimized_description
        iterations: list[IterationRecord] = []
        iteration_timings: list[dict[str, Any]] = []
        max_iterations = min(self.settings.refinement_iterations, 3)

        for i in range(max_iterations):
            self._progress(
                "generating" if i == 0 else "refining",
                f"Generating image (iteration {i + 1}/{max_iterations})...",
            )

            # Generate image
            visualizer_start = time.perf_counter()
            image_path = await self.visualizer.run(
                description=current_description,
                diagram_type=DiagramType.LINKEDIN_PLAYLIST,
                iteration=i + 1,
                width=linkedin_format.width,
                height=linkedin_format.height,
            )
            visualizer_seconds = time.perf_counter() - visualizer_start

            # Critique
            self._progress(
                "refining",
                f"Evaluating image quality (iteration {i + 1}/{max_iterations})...",
            )
            critic_start = time.perf_counter()
            critique = await self.critic.run(
                image_path=image_path,
                description=current_description,
                source_context=playlist_summary,
                caption=playlist_data.title,
                diagram_type=DiagramType.LINKEDIN_PLAYLIST,
            )
            critic_seconds = time.perf_counter() - critic_start

            iteration_record = IterationRecord(
                iteration=i + 1,
                description=current_description,
                image_path=image_path,
                critique=critique,
            )
            iterations.append(iteration_record)
            iteration_timings.append(
                {
                    "iteration": i + 1,
                    "visualizer_seconds": visualizer_seconds,
                    "critic_seconds": critic_seconds,
                }
            )

            if critique.needs_revision and critique.revised_description:
                self._progress("refining", f"Revision needed: {critique.summary}")
                current_description = critique.revised_description
            else:
                self._progress("refining", f"Image {i + 1} approved by critic")

        # ── Stage 4: Caption ──────────────────────────────────
        caption_data: dict[str, Any] = {"caption": "", "description": "", "hashtags": []}
        if generate_caption:
            self._progress("captioning", "Generating LinkedIn article...")
            caption_data = await self.caption_writer.run(
                playlist_data=playlist_data,
                image_description=current_description,
                playlist_url=self._playlist_url,
            )

        # ── Finalize ──────────────────────────────────────────
        self._progress("complete", "Generation complete!")

        final_image = iterations[-1].image_path
        output_format = getattr(self.settings, "output_format", "png").lower()
        ext = "jpg" if output_format == "jpeg" else output_format
        final_output_path = str(self._run_dir / f"final_output.{ext}")

        img = load_image(final_image)
        save_image(img, final_output_path, format=output_format)

        total_seconds = time.perf_counter() - total_start

        metadata = RunMetadata(
            run_id=self.run_id,
            timestamp=datetime.datetime.now().isoformat(),
            vlm_provider=getattr(self._vlm, "name", "custom"),
            vlm_model=getattr(self._vlm, "model_name", "custom"),
            image_provider=getattr(self._image_gen, "name", "custom"),
            image_model=getattr(self._image_gen, "model_name", "custom"),
            refinement_iterations=len(iterations),
            config_snapshot=self.settings.model_dump(
                exclude={"google_api_key", "youtube_api_key"}
            ),
        )
        metadata_dict = metadata.model_dump()
        metadata_dict["timing"] = {
            "total_seconds": total_seconds,
            "planning_seconds": planning_seconds,
            "styling_seconds": styling_seconds,
            "iterations": iteration_timings,
        }
        metadata_dict["playlist"] = {
            "playlist_id": playlist_data.playlist_id,
            "title": playlist_data.title,
            "video_count": playlist_data.video_count,
            "total_duration": playlist_data.total_duration_seconds,
        }

        save_json(metadata_dict, self._run_dir / "metadata.json")

        output = PlaylistGenerationOutput(
            image_path=final_output_path,
            caption=caption_data.get("caption", ""),
            description=caption_data.get("description", ""),
            hashtags=caption_data.get("hashtags", []),
            iterations=iterations,
            metadata=metadata_dict,
        )

        logger.info(
            "LinkedIn generation complete",
            run_id=self.run_id,
            output=final_output_path,
            total_iterations=len(iterations),
            total_seconds=round(total_seconds, 1),
        )

        return output
