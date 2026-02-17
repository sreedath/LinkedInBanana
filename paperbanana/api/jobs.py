"""In-memory job queue for tracking generation jobs."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Job:
    """A generation job with status tracking."""

    job_id: str
    playlist_url: str
    format: str = "landscape"
    generate_caption: bool = True
    custom_instructions: str = ""
    status: str = "queued"  # queued, scraping, planning, generating, refining, captioning, complete, error
    playlist_info: Optional[dict[str, Any]] = None
    phase: str = ""
    message: str = ""
    progress: float = 0.0
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    _subscribers: list[asyncio.Queue] = field(default_factory=list, repr=False)

    def update(self, status: str, phase: str = "", message: str = "", progress: float = 0.0):
        """Update job status and notify subscribers."""
        self.status = status
        self.phase = phase
        self.message = message
        self.progress = progress
        event = {
            "status": status,
            "phase": phase,
            "message": message,
            "progress": progress,
        }
        for q in self._subscribers:
            q.put_nowait(event)

    def complete(self, result: dict[str, Any]):
        """Mark job as complete with results."""
        self.status = "complete"
        self.phase = "complete"
        self.message = "Generation complete"
        self.progress = 1.0
        self.result = result
        event = {
            "status": "complete",
            "phase": "complete",
            "message": "Generation complete",
            "progress": 1.0,
            "result": result,
        }
        for q in self._subscribers:
            q.put_nowait(event)

    def fail(self, error: str):
        """Mark job as failed."""
        self.status = "error"
        self.error = error
        event = {"status": "error", "error": error}
        for q in self._subscribers:
            q.put_nowait(event)

    def subscribe(self) -> asyncio.Queue:
        """Subscribe to job status updates via an async queue."""
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        """Unsubscribe from job updates."""
        if q in self._subscribers:
            self._subscribers.remove(q)


class JobStore:
    """In-memory store for generation jobs."""

    def __init__(self):
        self._jobs: dict[str, Job] = {}

    def create(self, playlist_url: str, format: str = "landscape", generate_caption: bool = True, custom_instructions: str = "") -> Job:
        job_id = str(uuid.uuid4())[:8]
        job = Job(
            job_id=job_id,
            playlist_url=playlist_url,
            format=format,
            generate_caption=generate_caption,
            custom_instructions=custom_instructions,
        )
        self._jobs[job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def list_all(self) -> list[Job]:
        return list(self._jobs.values())
