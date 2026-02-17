"""PaperBanana: Agentic framework for automated academic illustration generation."""

import sys

if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8", errors="replace")

__version__ = "0.1.0"

from paperbanana.core.pipeline import PaperBananaPipeline
from paperbanana.core.linkedin_pipeline import LinkedInPlaylistPipeline
from paperbanana.core.types import (
    DiagramType,
    GenerationInput,
    GenerationOutput,
    LinkedInFormat,
    PlaylistGenerationInput,
    PlaylistGenerationOutput,
)

__all__ = [
    "PaperBananaPipeline",
    "LinkedInPlaylistPipeline",
    "DiagramType",
    "GenerationInput",
    "GenerationOutput",
    "LinkedInFormat",
    "PlaylistGenerationInput",
    "PlaylistGenerationOutput",
]
