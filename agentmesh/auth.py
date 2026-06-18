from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import timedelta

from fastapi import HTTPException, Request, Response, status

from agentmesh.models import AuthSession, User, now_utc
from agentmesh.store import SQLiteStore

SESSION_COOKIE_NAME = "agentmesh_session"
SESSION_TTL = timedelta(hours=12)
PASSWORD_ITERATIONS = 120_000


def create_password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = password_hash.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    expected = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        int(iterations),
    ).hex()
    return hmac.compare_digest(expected, digest_hex)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_session(repository: SQLiteStore, user: User) -> tuple[AuthSession, str]:
    token = secrets.token_urlsafe(32)
    session = AuthSession(
        user_id=user.id,
        token_hash=hash_session_token(token),
        expires_at=now_utc() + SESSION_TTL,
    )
    repository.save_auth_session(session)
    return session, token


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        secure=os.getenv("AGENTMESH_COOKIE_SECURE") == "1",
        samesite="lax",
        max_age=int(SESSION_TTL.total_seconds()),
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME)


def current_user_from_request(repository: SQLiteStore, request: Request) -> User | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    authorization = request.headers.get("authorization")
    if not token and authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    if not token:
        return None

    session = repository.get_auth_session_by_token_hash(hash_session_token(token))
    if session is None or session.revoked_at is not None or session.expires_at <= now_utc():
        return None
    user = repository.get_user(session.user_id)
    if user is None or user.status != "active":
        return None
    return user


def require_current_user(repository: SQLiteStore, request: Request) -> User:
    user = current_user_from_request(repository, request)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user
