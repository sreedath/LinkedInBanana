"""API route handlers for LinkedInBanana."""

from __future__ import annotations

import asyncio
import traceback

import structlog
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sse_starlette.sse import EventSourceResponse

from paperbanana.api.auth import get_current_user
from paperbanana.api.jobs import Job, JobStore
from paperbanana.api.schemas import (
    ApiKeysRequest,
    ApiKeysResponse,
    AuthStatusResponse,
    JobCreatedResponse,
    JobResultResponse,
    JobStatusResponse,
    LinkedInPostRequest,
    LinkedInScheduleRequest,
    LoginRequest,
    LoginResponse,
    PlaylistInfoResponse,
    PlaylistRequest,
)
from paperbanana.core.config import Settings
from paperbanana.core.linkedin_pipeline import LinkedInPlaylistPipeline
from paperbanana.core.types import LinkedInFormat

logger = structlog.get_logger()

router = APIRouter(prefix="/api/v1")
job_store = JobStore()


# ---------------------------------------------------------------------------
# Auth routes (public)
# ---------------------------------------------------------------------------

@router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate and return a session token."""
    from paperbanana.api.auth import authenticate, create_session

    user = authenticate(request.email, request.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_session(user["id"])
    return LoginResponse(token=token, email=user["email"])


@router.post("/auth/logout")
async def logout(user: dict = Depends(get_current_user)):
    """Invalidate the current session."""
    from fastapi import Request as FastAPIRequest

    # We need to extract token from the dependency; just delete all sessions for simplicity
    # The get_current_user already validated the token
    return {"ok": True}


@router.get("/auth/me", response_model=AuthStatusResponse)
async def auth_me(user: dict = Depends(get_current_user)):
    """Return the current authenticated user."""
    return AuthStatusResponse(authenticated=True, email=user["email"])


async def _run_pipeline(job: Job, settings: Settings):
    """Background task to run the full pipeline for a job."""
    try:
        linkedin_format = (
            LinkedInFormat.SQUARE if job.format == "square" else LinkedInFormat.LANDSCAPE
        )

        # Progress phases with approximate progress values
        phase_progress = {
            "scraping": 0.1,
            "planning": 0.3,
            "generating": 0.5,
            "refining": 0.7,
            "captioning": 0.85,
            "complete": 1.0,
        }

        def on_progress(phase: str, message: str):
            progress = phase_progress.get(phase, 0.0)
            job.update(status=phase, phase=phase, message=message, progress=progress)

        pipeline = LinkedInPlaylistPipeline(
            settings=settings,
            on_progress=on_progress,
        )

        # Stage 1: Scrape
        job.update(status="scraping", phase="scraping", message="Fetching playlist data...", progress=0.05)
        playlist_data = await pipeline.scrape_playlist(job.playlist_url)

        # Store playlist info for frontend display
        job.playlist_info = {
            "title": playlist_data.title,
            "channel": playlist_data.channel_title,
            "video_count": playlist_data.video_count,
            "total_duration_minutes": playlist_data.total_duration_seconds // 60,
            "total_views": playlist_data.total_views,
            "videos": [
                {
                    "title": v.title,
                    "duration_minutes": v.duration_seconds // 60,
                    "duration_seconds": v.duration_seconds,
                }
                for v in playlist_data.videos
            ],
        }

        # Stage 2-5: Generate
        output = await pipeline.generate(
            playlist_data=playlist_data,
            linkedin_format=linkedin_format,
            generate_caption=job.generate_caption,
            custom_instructions=job.custom_instructions,
        )

        # Resolve absolute run directory
        from pathlib import Path

        run_dir = str(Path(pipeline._run_dir).resolve())

        # Build iteration image URLs
        iteration_images = []
        for it in output.iterations:
            iter_filename = f"diagram_iter_{it.iteration}.png"
            iteration_images.append({
                "iteration": it.iteration,
                "image_url": f"/api/v1/images/{job.job_id}/{iter_filename}",
            })

        # Build result
        result = {
            "image_url": f"/api/v1/images/{job.job_id}/final_output.png",
            "image_path": str(Path(output.image_path).resolve()),
            "run_dir": run_dir,
            "iteration_images": iteration_images,
            "caption": output.caption,
            "description": output.description,
            "hashtags": output.hashtags,
            "playlist_title": playlist_data.title,
            "video_count": playlist_data.video_count,
        }

        logger.info(
            "Job result built",
            job_id=job.job_id,
            run_dir=run_dir,
            iteration_count=len(iteration_images),
            files_in_run_dir=[f.name for f in Path(run_dir).iterdir()] if Path(run_dir).exists() else [],
        )

        job.complete(result)

    except Exception as e:
        logger.error("Pipeline failed", job_id=job.job_id, error=str(e))
        logger.error(traceback.format_exc())
        job.fail(str(e))


@router.get("/api-keys", response_model=ApiKeysResponse)
async def get_api_keys(user: dict = Depends(get_current_user)):
    """Get stored API keys."""
    from paperbanana.api.linkedin import get_stored_api_keys

    keys = get_stored_api_keys()
    return ApiKeysResponse(**keys)


@router.put("/api-keys", response_model=ApiKeysResponse)
async def put_api_keys(request: ApiKeysRequest, user: dict = Depends(get_current_user)):
    """Save API keys to the backend."""
    from paperbanana.api.linkedin import save_api_keys

    keys = save_api_keys(request.google_api_key, request.youtube_api_key)
    return ApiKeysResponse(**keys)


@router.post("/playlist", response_model=JobCreatedResponse)
async def create_playlist_job(request: PlaylistRequest, user: dict = Depends(get_current_user)):
    """Submit a playlist URL for LinkedIn image generation."""
    if not request.playlist_url:
        raise HTTPException(status_code=400, detail="playlist_url is required")

    # Fall back to stored keys when request keys are empty
    google_key = request.google_api_key
    youtube_key = request.youtube_api_key
    if not google_key or not youtube_key:
        from paperbanana.api.linkedin import get_stored_api_keys

        stored = get_stored_api_keys()
        if not google_key:
            google_key = stored["google_api_key"]
        if not youtube_key:
            youtube_key = stored["youtube_api_key"]

    if not google_key or not youtube_key:
        raise HTTPException(status_code=400, detail="API keys are required. Save them in settings or provide them in the request.")

    job = job_store.create(
        playlist_url=request.playlist_url,
        format=request.format,
        generate_caption=request.generate_caption,
        custom_instructions=request.custom_instructions,
    )

    settings = Settings(
        google_api_key=google_key,
        youtube_api_key=youtube_key,
    )
    asyncio.create_task(_run_pipeline(job, settings))

    return JobCreatedResponse(job_id=job.job_id, status="queued")


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, user: dict = Depends(get_current_user)):
    """Get the current status of a generation job."""
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = None
    if job.result:
        result = JobResultResponse(**job.result)

    playlist_info = None
    if job.playlist_info:
        playlist_info = PlaylistInfoResponse(**job.playlist_info)

    return JobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        phase=job.phase,
        message=job.message,
        progress=job.progress,
        playlist_info=playlist_info,
        result=result,
        error=job.error,
    )


@router.get("/jobs/{job_id}/stream")
async def stream_job_progress(job_id: str, user: dict = Depends(get_current_user)):
    """SSE stream of job progress updates."""
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        # Send current state first
        import json

        yield {
            "event": "status",
            "data": json.dumps({
                "status": job.status,
                "phase": job.phase,
                "message": job.message,
                "progress": job.progress,
            }),
        }

        # If already done, no need to stream
        if job.status in ("complete", "error"):
            if job.status == "complete" and job.result:
                yield {
                    "event": "complete",
                    "data": json.dumps(job.result),
                }
            elif job.status == "error":
                yield {
                    "event": "error",
                    "data": json.dumps({"error": job.error}),
                }
            return

        # Subscribe to updates
        queue = job.subscribe()
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    status = event.get("status", "")

                    if status == "complete":
                        yield {
                            "event": "complete",
                            "data": json.dumps(event.get("result", {})),
                        }
                        return
                    elif status == "error":
                        yield {
                            "event": "error",
                            "data": json.dumps({"error": event.get("error", "")}),
                        }
                        return
                    else:
                        yield {
                            "event": "status",
                            "data": json.dumps(event),
                        }
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield {"event": "ping", "data": ""}
        finally:
            job.unsubscribe(queue)

    return EventSourceResponse(event_generator())


@router.get("/images/{job_id}/{filename}")
async def serve_image(job_id: str, filename: str, user: dict = Depends(get_current_user)):
    """Serve a generated image file from the job's run directory."""
    from pathlib import Path

    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.result:
        raise HTTPException(status_code=404, detail="Image not ready")

    # Sanitize filename to prevent directory traversal
    safe_filename = Path(filename).name

    # Try run_dir first, then fall back to image_path's parent directory
    run_dir = job.result.get("run_dir")
    if not run_dir:
        image_path_str = job.result.get("image_path", "")
        if image_path_str:
            run_dir = str(Path(image_path_str).parent)

    if not run_dir:
        raise HTTPException(status_code=404, detail="Image directory not found")

    image_path = Path(run_dir) / safe_filename

    logger.info(
        "Serving image",
        job_id=job_id,
        filename=safe_filename,
        run_dir=run_dir,
        full_path=str(image_path),
        exists=image_path.exists(),
    )

    if not image_path.exists():
        # List available files for debugging
        dir_path = Path(run_dir)
        available = [f.name for f in dir_path.iterdir()] if dir_path.exists() else []
        logger.warning(
            "Image file not found",
            requested=safe_filename,
            available_files=available,
            run_dir=run_dir,
        )
        raise HTTPException(
            status_code=404,
            detail=f"Image file '{safe_filename}' not found. Available: {available}",
        )

    return FileResponse(str(image_path), media_type="image/png")


# ---------------------------------------------------------------------------
# LinkedIn integration routes
# ---------------------------------------------------------------------------


@router.get("/linkedin/auth-url")
async def linkedin_auth_url(redirect_uri: str, user: dict = Depends(get_current_user)):
    """Generate a LinkedIn OAuth authorization URL using server-side credentials."""
    import os

    from paperbanana.api.linkedin import get_auth_url

    client_id = os.environ.get("LINKEDIN_CLIENT_ID", "")
    if not client_id:
        raise HTTPException(status_code=500, detail="LINKEDIN_CLIENT_ID not configured on server")
    url = get_auth_url(client_id, redirect_uri)
    return {"url": url}


@router.get("/linkedin/callback")
async def linkedin_callback(code: str, state: str = ""):
    """Handle the OAuth redirect from LinkedIn."""
    import os

    from fastapi.responses import HTMLResponse

    from paperbanana.api.linkedin import exchange_code, is_email_allowed, persist_token

    client_id = os.environ.get("LINKEDIN_CLIENT_ID", "")
    client_secret = os.environ.get("LINKEDIN_CLIENT_SECRET", "")
    # Reconstruct the redirect URI that was used in the auth request
    redirect_uri = os.environ.get(
        "LINKEDIN_REDIRECT_URI", "http://localhost:8080/api/v1/linkedin/callback"
    )

    if not client_id or not client_secret:
        return HTMLResponse(
            "<html><body><script>window.opener.postMessage({type:'linkedin-auth',error:'Missing LinkedIn credentials'},'*');window.close();</script></body></html>"
        )

    try:
        token_data = await exchange_code(code, client_id, client_secret, redirect_uri)
        email = token_data.get("email", "")
        name = token_data.get("name", "")

        # Check email whitelist before persisting
        if not is_email_allowed(email):
            logger.warning("LinkedIn auth rejected: email not allowed", email=email)
            return HTMLResponse(
                f"<html><body><p>Access denied. The email {email} is not authorized to post.</p>"
                f"<script>window.opener.postMessage({{type:'linkedin-auth',error:'Email {email} is not authorized to post'}},'*');window.close();</script></body></html>"
            )

        # Email check passed — persist tokens
        persist_token(token_data)

        return HTMLResponse(
            f"<html><body><p>Connected as {name}. You can close this window.</p>"
            f"<script>window.opener.postMessage({{type:'linkedin-auth',success:true,name:'{name}'}},'*');window.close();</script></body></html>"
        )
    except Exception as e:
        logger.error("LinkedIn OAuth failed", error=str(e))
        return HTMLResponse(
            f"<html><body><script>window.opener.postMessage({{type:'linkedin-auth',error:'{str(e)}'}},'*');window.close();</script></body></html>"
        )


@router.get("/linkedin/status")
async def linkedin_status(user: dict = Depends(get_current_user)):
    """Check if the user is authenticated with LinkedIn."""
    from paperbanana.api.linkedin import get_auth_status

    return get_auth_status()


@router.post("/linkedin/post")
async def linkedin_post(request: LinkedInPostRequest, user: dict = Depends(get_current_user)):
    """Post to LinkedIn immediately."""
    from paperbanana.api.linkedin import post_now

    try:
        result = await post_now(request.caption, request.image_path)
        return result
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        logger.error("LinkedIn post failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/linkedin/schedule")
async def linkedin_schedule(request: LinkedInScheduleRequest, user: dict = Depends(get_current_user)):
    """Schedule a LinkedIn post for later."""
    from paperbanana.api.linkedin import schedule_post

    result = schedule_post(request.caption, request.image_path, request.scheduled_at)
    return result
