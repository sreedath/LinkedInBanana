"""Authentication: users, sessions, and FastAPI dependency."""

from __future__ import annotations

import hashlib
import os
import secrets
import sqlite3
import time
from pathlib import Path

import structlog
from fastapi import Depends, HTTPException, Request

logger = structlog.get_logger()

DB_PATH = Path("data/scheduler.db")


def _get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at REAL NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )"""
    )
    conn.commit()
    return conn


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), iterations=100_000
    ).hex()


def ensure_user(email: str, password: str) -> None:
    """Create or update user with the given email and password."""
    conn = _get_db()
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    salt = secrets.token_hex(16)
    pw_hash = _hash_password(password, salt)
    now = time.time()
    if row:
        conn.execute(
            "UPDATE users SET password_hash = ?, salt = ? WHERE id = ?",
            (pw_hash, salt, row["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO users (email, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
            (email, pw_hash, salt, now),
        )
    conn.commit()
    conn.close()


def authenticate(email: str, password: str) -> dict | None:
    """Verify email/password. Returns user dict or None."""
    conn = _get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if not row:
        return None
    if _hash_password(password, row["salt"]) != row["password_hash"]:
        return None
    return {"id": row["id"], "email": row["email"]}


def create_session(user_id: int, ttl_seconds: int = 30 * 24 * 3600) -> str:
    """Create a session token valid for ttl_seconds (default 30 days)."""
    token = secrets.token_hex(32)
    now = time.time()
    conn = _get_db()
    conn.execute(
        "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token, user_id, now, now + ttl_seconds),
    )
    conn.commit()
    conn.close()
    return token


def validate_session(token: str) -> dict | None:
    """Return user dict if the session token is valid, else None."""
    conn = _get_db()
    row = conn.execute(
        """SELECT s.*, u.email FROM sessions s
           JOIN users u ON u.id = s.user_id
           WHERE s.token = ?""",
        (token,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    if row["expires_at"] < time.time():
        return None
    return {"id": row["user_id"], "email": row["email"]}


def delete_session(token: str) -> None:
    conn = _get_db()
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_current_user(request: Request) -> dict:
    """FastAPI dependency: extract and validate the auth token.

    Checks Authorization header first, then falls back to ?token= query param
    (needed for EventSource/SSE and <img> tags which can't set headers).
    """
    token = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
    if not token:
        token = request.query_params.get("token", "")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = validate_session(token)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return user


# ---------------------------------------------------------------------------
# Seed the default user on import (from env vars)
# ---------------------------------------------------------------------------

def seed_default_user() -> None:
    """Create the default user from env vars if configured."""
    email = os.environ.get("AUTH_USER_EMAIL", "")
    password = os.environ.get("AUTH_USER_PASSWORD", "")
    if email and password:
        ensure_user(email, password)
        logger.info("Default user seeded", email=email)
    else:
        logger.warning(
            "AUTH_USER_EMAIL or AUTH_USER_PASSWORD not set — no default user will be created. "
            "Set these environment variables to enable login."
        )
