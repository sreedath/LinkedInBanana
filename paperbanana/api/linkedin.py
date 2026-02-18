"""LinkedIn API integration: OAuth, posting, and scheduling."""

from __future__ import annotations

import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
import structlog

logger = structlog.get_logger()

DB_PATH = Path("data/scheduler.db")


def _get_db() -> sqlite3.Connection:
    """Get a SQLite connection, creating tables if needed."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS oauth_tokens (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            access_token TEXT NOT NULL,
            expires_at REAL NOT NULL,
            refresh_token TEXT,
            linkedin_id TEXT,
            name TEXT,
            updated_at REAL NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS scheduled_posts (
            id TEXT PRIMARY KEY,
            caption TEXT NOT NULL,
            image_path TEXT,
            scheduled_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            linkedin_post_id TEXT,
            error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            google_api_key TEXT NOT NULL DEFAULT '',
            youtube_api_key TEXT NOT NULL DEFAULT '',
            updated_at REAL NOT NULL
        )"""
    )
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# API key storage
# ---------------------------------------------------------------------------

def get_stored_api_keys() -> dict:
    """Return stored API keys, or empty strings if not set."""
    conn = _get_db()
    row = conn.execute("SELECT * FROM api_keys WHERE id = 1").fetchone()
    conn.close()
    if not row:
        return {"google_api_key": "", "youtube_api_key": ""}
    return {
        "google_api_key": row["google_api_key"],
        "youtube_api_key": row["youtube_api_key"],
    }


def save_api_keys(google_api_key: str, youtube_api_key: str) -> dict:
    """Save API keys to the database."""
    now = time.time()
    conn = _get_db()
    conn.execute(
        """INSERT OR REPLACE INTO api_keys
           (id, google_api_key, youtube_api_key, updated_at)
           VALUES (1, ?, ?, ?)""",
        (google_api_key, youtube_api_key, now),
    )
    conn.commit()
    conn.close()
    return {"google_api_key": google_api_key, "youtube_api_key": youtube_api_key}


# ---------------------------------------------------------------------------
# OAuth helpers
# ---------------------------------------------------------------------------

def get_auth_url(client_id: str, redirect_uri: str, state: str | None = None) -> str:
    """Build the LinkedIn OAuth 2.0 authorization URL."""
    state = state or uuid.uuid4().hex
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "openid profile email w_member_social",
        "state": state,
    }
    qs = "&".join(f"{k}={httpx.URL('', params={k: v}).params[k]}" for k, v in params.items())
    return f"https://www.linkedin.com/oauth/v2/authorization?{qs}"


def is_email_allowed(email: str) -> bool:
    """Check if an email is in the allowed list. If no list is configured, allow all."""
    import os

    allowed_csv = os.environ.get("LINKEDIN_ALLOWED_EMAILS", "")
    if not allowed_csv.strip():
        return True  # No whitelist configured = allow all
    allowed = [e.strip().lower() for e in allowed_csv.split(",") if e.strip()]
    return email.strip().lower() in allowed


async def exchange_code(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict:
    """Exchange an authorization code for access + refresh tokens.

    Returns token data and profile info WITHOUT persisting.
    Call persist_token() after email validation passes.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        token_data = resp.json()

    access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", 3600)
    refresh_token = token_data.get("refresh_token")

    # Fetch profile to get LinkedIn ID and email
    async with httpx.AsyncClient() as client:
        profile_resp = await client.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        profile_resp.raise_for_status()
        profile = profile_resp.json()

    linkedin_id = profile.get("sub", "")
    name = profile.get("name", "")
    email = profile.get("email", "")

    # Fetch organizations the user administers
    org_id = ""
    org_name = ""
    try:
        async with httpx.AsyncClient() as client:
            orgs_resp = await client.get(
                "https://api.linkedin.com/rest/organizationAcls?q=roleAssignee&role=ADMINISTRATOR",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "LinkedIn-Version": "202401",
                },
            )
            if orgs_resp.status_code == 200:
                orgs_data = orgs_resp.json()
                elements = orgs_data.get("elements", [])
                if elements:
                    # Use the first org; extract ID from URN like "urn:li:organization:12345"
                    org_urn = elements[0].get("organization", "")
                    if org_urn:
                        org_id = org_urn.split(":")[-1]
                        # Fetch org name
                        org_detail_resp = await client.get(
                            f"https://api.linkedin.com/rest/organizations/{org_id}",
                            headers={
                                "Authorization": f"Bearer {access_token}",
                                "LinkedIn-Version": "202401",
                            },
                        )
                        if org_detail_resp.status_code == 200:
                            org_name = org_detail_resp.json().get("localizedName", "")
                logger.info("Fetched org info", org_id=org_id, org_name=org_name)
    except Exception as e:
        logger.warning("Could not fetch organizations", error=str(e))

    return {
        "access_token": access_token,
        "expires_in": expires_in,
        "refresh_token": refresh_token,
        "linkedin_id": linkedin_id,
        "name": name,
        "email": email,
        "org_id": org_id,
        "org_name": org_name,
    }


def persist_token(token_data: dict) -> None:
    """Persist OAuth token data to the database after email check passes."""
    now = time.time()
    conn = _get_db()

    # Add columns if they don't exist yet
    for col, default in [("email", "''"), ("org_id", "''"), ("org_name", "''")]:
        try:
            conn.execute(f"ALTER TABLE oauth_tokens ADD COLUMN {col} TEXT DEFAULT {default}")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

    conn.execute(
        """INSERT OR REPLACE INTO oauth_tokens
           (id, access_token, expires_at, refresh_token, linkedin_id, name, email, org_id, org_name, updated_at)
           VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            token_data["access_token"],
            now + token_data["expires_in"],
            token_data.get("refresh_token"),
            token_data["linkedin_id"],
            token_data["name"],
            token_data.get("email", ""),
            token_data.get("org_id", ""),
            token_data.get("org_name", ""),
            now,
        ),
    )
    conn.commit()
    conn.close()


def get_stored_token() -> Optional[dict]:
    """Return the stored OAuth token if it exists and is not expired."""
    conn = _get_db()
    row = conn.execute("SELECT * FROM oauth_tokens WHERE id = 1").fetchone()
    conn.close()
    if not row:
        return None
    if row["expires_at"] < time.time():
        return None
    result = {
        "access_token": row["access_token"],
        "linkedin_id": row["linkedin_id"],
        "name": row["name"],
    }
    # Include org info if columns exist
    try:
        result["org_id"] = row["org_id"] or ""
        result["org_name"] = row["org_name"] or ""
    except (IndexError, KeyError):
        result["org_id"] = ""
        result["org_name"] = ""
    return result


def get_auth_status() -> dict:
    """Return current authentication status."""
    token = get_stored_token()
    if token:
        return {
            "authenticated": True,
            "name": token["name"],
            "linkedin_id": token["linkedin_id"],
            "org_id": token.get("org_id", ""),
            "org_name": token.get("org_name", ""),
        }
    return {"authenticated": False}


# ---------------------------------------------------------------------------
# Posting
# ---------------------------------------------------------------------------

async def upload_image_to_linkedin(access_token: str, linkedin_id: str, image_path: str, org_id: str = "") -> str:
    """Upload an image to LinkedIn and return the image URN."""
    owner_urn = f"urn:li:organization:{org_id}" if org_id else f"urn:li:person:{linkedin_id}"

    async with httpx.AsyncClient() as client:
        # Step 1: Initialize upload
        init_resp = await client.post(
            "https://api.linkedin.com/rest/images?action=initializeUpload",
            json={
                "initializeUploadRequest": {
                    "owner": owner_urn,
                }
            },
            headers={
                "Authorization": f"Bearer {access_token}",
                "LinkedIn-Version": "202401",
                "Content-Type": "application/json",
            },
        )
        init_resp.raise_for_status()
        init_data = init_resp.json()["value"]
        upload_url = init_data["uploadUrl"]
        image_urn = init_data["image"]

        # Step 2: Upload the binary
        image_bytes = Path(image_path).read_bytes()
        upload_resp = await client.put(
            upload_url,
            content=image_bytes,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/octet-stream",
            },
            timeout=60.0,
        )
        upload_resp.raise_for_status()

    return image_urn


async def create_linkedin_post(
    access_token: str,
    linkedin_id: str,
    text: str,
    image_urn: str | None = None,
    org_id: str = "",
) -> str:
    """Create a LinkedIn post. Returns the post URN."""
    owner_urn = f"urn:li:organization:{org_id}" if org_id else f"urn:li:person:{linkedin_id}"

    body: dict = {
        "author": owner_urn,
        "lifecycleState": "PUBLISHED",
        "visibility": "PUBLIC",
        "commentary": text,
        "distribution": {
            "feedDistribution": "MAIN_FEED",
        },
    }

    if image_urn:
        body["content"] = {
            "media": {
                "id": image_urn,
            }
        }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.linkedin.com/rest/posts",
            json=body,
            headers={
                "Authorization": f"Bearer {access_token}",
                "LinkedIn-Version": "202401",
                "Content-Type": "application/json",
            },
        )
        resp.raise_for_status()

    # LinkedIn returns the post ID in the x-restli-id header
    post_id = resp.headers.get("x-restli-id", "")
    return post_id


async def post_now(caption: str, image_path: str | None = None) -> dict:
    """Post immediately to LinkedIn using stored credentials.

    Posts to the organization page if org_id is stored, otherwise to personal profile.
    """
    token = get_stored_token()
    if not token:
        raise ValueError("Not authenticated with LinkedIn")

    access_token = token["access_token"]
    linkedin_id = token["linkedin_id"]
    org_id = token.get("org_id", "")

    image_urn = None
    if image_path and Path(image_path).exists():
        image_urn = await upload_image_to_linkedin(access_token, linkedin_id, image_path, org_id)

    post_id = await create_linkedin_post(access_token, linkedin_id, caption, image_urn, org_id)
    target = f"organization {org_id}" if org_id else "personal profile"
    logger.info("Posted to LinkedIn", target=target, post_id=post_id)
    return {"post_id": post_id, "status": "published"}


# ---------------------------------------------------------------------------
# Scheduling
# ---------------------------------------------------------------------------

def schedule_post(caption: str, image_path: str | None, scheduled_at: str) -> dict:
    """Save a post to be published later. scheduled_at is ISO 8601 format."""
    post_id = uuid.uuid4().hex[:12]
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_db()
    conn.execute(
        """INSERT INTO scheduled_posts
           (id, caption, image_path, scheduled_at, status, created_at, updated_at)
           VALUES (?, ?, ?, ?, 'pending', ?, ?)""",
        (post_id, caption, image_path, scheduled_at, now, now),
    )
    conn.commit()
    conn.close()
    return {"id": post_id, "scheduled_at": scheduled_at, "status": "pending"}


async def publish_due_posts() -> int:
    """Check for and publish any posts that are due. Returns count of published posts."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM scheduled_posts WHERE status = 'pending' AND scheduled_at <= ?",
        (now,),
    ).fetchall()
    conn.close()

    published = 0
    for row in rows:
        try:
            result = await post_now(row["caption"], row["image_path"])
            conn = _get_db()
            conn.execute(
                "UPDATE scheduled_posts SET status = 'published', linkedin_post_id = ?, updated_at = ? WHERE id = ?",
                (result["post_id"], datetime.now(timezone.utc).isoformat(), row["id"]),
            )
            conn.commit()
            conn.close()
            published += 1
            logger.info("Scheduled post published", post_id=row["id"])
        except Exception as e:
            conn = _get_db()
            conn.execute(
                "UPDATE scheduled_posts SET status = 'failed', error = ?, updated_at = ? WHERE id = ?",
                (str(e), datetime.now(timezone.utc).isoformat(), row["id"]),
            )
            conn.commit()
            conn.close()
            logger.error("Scheduled post failed", post_id=row["id"], error=str(e))

    return published
