"""FastAPI server for LinkedInBanana."""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from paperbanana.api.routes import router

# Resolve frontend build directory
_FRONTEND_DIR = Path(os.environ.get("FRONTEND_DIR", "frontend/out"))


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="LinkedInBanana",
        description="Generate LinkedIn-ready images from YouTube playlists",
        version="0.1.0",
    )

    # CORS middleware for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(router)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    # Serve frontend static files if the build directory exists
    frontend_dir = _FRONTEND_DIR
    if frontend_dir.exists():
        # Mount _next static assets
        next_dir = frontend_dir / "_next"
        if next_dir.exists():
            app.mount("/_next", StaticFiles(directory=str(next_dir)), name="next-static")

        @app.get("/generate{path:path}")
        async def serve_generate(request: Request):
            """Serve the generate page for SPA routing."""
            page = frontend_dir / "generate" / "index.html"
            if page.exists():
                return FileResponse(str(page), media_type="text/html")
            # Fallback to root index
            return FileResponse(str(frontend_dir / "index.html"), media_type="text/html")

        @app.get("/favicon.ico")
        async def serve_favicon():
            favicon = frontend_dir / "favicon.ico"
            if favicon.exists():
                return FileResponse(str(favicon))
            return HTMLResponse("", status_code=204)

        @app.get("/")
        async def serve_index():
            """Serve the frontend index page."""
            return FileResponse(str(frontend_dir / "index.html"), media_type="text/html")

        # Mount remaining static files (CSS, images, etc.) as catch-all
        app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")

    return app


app = create_app()


def main():
    """Run the server."""
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(
        "paperbanana.api.server:app",
        host="0.0.0.0",
        port=port,
        reload=True,
    )


if __name__ == "__main__":
    main()
