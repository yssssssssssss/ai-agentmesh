"""Auth routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from agentmesh.auth import (
    clear_session_cookie,
    create_password_hash,
    current_user_from_request,
    hash_session_token,
    issue_session,
    set_session_cookie,
    verify_password,
)
from agentmesh.models import LoginRequest, PasswordChangeRequest, StatusResponse, User, UserResponse, now_utc
from agentmesh.routes.deps import create_audit_event, current_user
from agentmesh.seed import ensure_seed_data
from agentmesh.store import store

router = APIRouter(prefix="/api/auth", tags=["auth"])


def revoke_user_sessions(user_id: str) -> int:
    revoked = 0
    now = now_utc()
    for session in store.auth_sessions:
        if session.user_id == user_id and session.revoked_at is None:
            session.revoked_at = now
            store.save_auth_session(session)
            revoked += 1
    return revoked


@router.post("/login", response_model=UserResponse)
def login(request: LoginRequest, response: Response) -> UserResponse:
    ensure_seed_data(store)
    user = store.get_user(request.user_id)
    credential = store.get_auth_credential(request.user_id)
    if (
        user is None
        or user.status != "active"
        or credential is None
        or not verify_password(request.password, credential.password_hash)
    ):
        raise HTTPException(status_code=401, detail="Invalid user id or password")
    _, token = issue_session(store, user)
    set_session_cookie(response, token)
    return UserResponse(user=user)


@router.post("/logout", response_model=StatusResponse)
def logout(request: Request, response: Response) -> StatusResponse:
    token = request.cookies.get("agentmesh_session")
    if token:
        session = store.get_auth_session_by_token_hash(hash_session_token(token))
        if session is not None and session.revoked_at is None:
            session.revoked_at = now_utc()
            store.save_auth_session(session)
    clear_session_cookie(response)
    return StatusResponse(status="ok")


@router.get("/me", response_model=UserResponse)
def auth_me(request: Request) -> UserResponse:
    ensure_seed_data(store)
    user = current_user_from_request(store, request)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return UserResponse(user=user)


@router.post("/password", response_model=StatusResponse)
def change_password(
    request: PasswordChangeRequest,
    response: Response,
    user: User = Depends(current_user),
) -> StatusResponse:
    credential = store.get_auth_credential(user.id)
    if credential is None or not verify_password(request.current_password, credential.password_hash):
        raise HTTPException(status_code=401, detail="Invalid current password")
    credential.password_hash = create_password_hash(request.new_password)
    credential.updated_at = now_utc()
    store.save_auth_credential(credential)
    revoked = revoke_user_sessions(user.id)
    clear_session_cookie(response)
    store.add_audit_event(
        create_audit_event(user.id, "change_password", "user", user.id, {"revoked_sessions": revoked})
    )
    return StatusResponse(status="ok")
