"""Inbox routes."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException

from agentmesh.models import InboxItem, InboxUpdateRequest, ItemResponse, ItemsResponse, Scope, User, UserRole, now_utc
from agentmesh.routes.deps import create_audit_event, current_user
from agentmesh.store import store

router = APIRouter(prefix="/api/inbox", tags=["inbox"])


def is_active_inbox_item(item: InboxItem, now) -> bool:
    if item.status == "resolved":
        return False
    if item.status == "snoozed" and item.snooze_until is not None:
        return item.snooze_until <= now
    return True


@router.get("", response_model=ItemsResponse)
def inbox_items(
    include_snoozed: bool = False,
    user: User = Depends(current_user),
) -> ItemsResponse:
    now = now_utc()
    items = [item for item in reversed(store.inbox_items) if inbox_visible_to_user(item, user)]
    if not include_snoozed:
        items = [item for item in items if is_active_inbox_item(item, now)]
    return ItemsResponse(items=items)


@router.patch("/{item_id}", response_model=ItemResponse)
def update_inbox_item(
    item_id: str,
    request: InboxUpdateRequest,
    user: User = Depends(current_user),
) -> ItemResponse:
    item = store.get_inbox_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    if not inbox_visible_to_user(item, user):
        raise HTTPException(status_code=403, detail="Not allowed to update this inbox item")
    if request.ttl_minutes is not None and request.snooze_until is not None:
        raise HTTPException(status_code=400, detail="Use ttl_minutes or snooze_until, not both")
    next_status = request.status or item.status
    if next_status not in {"open", "snoozed", "resolved"}:
        raise HTTPException(status_code=400, detail="Unsupported inbox status")

    now = now_utc()
    item.status = next_status
    item.updated_at = now
    if next_status == "resolved":
        item.resolved_at = now
        item.acknowledged_at = item.acknowledged_at or now
        item.snooze_until = None
    elif next_status == "snoozed":
        snooze_until = request.snooze_until or (
            now + timedelta(minutes=request.ttl_minutes) if request.ttl_minutes is not None else None
        )
        if snooze_until is None or snooze_until <= now:
            raise HTTPException(status_code=400, detail="snooze_until must be in the future")
        item.acknowledged_at = now
        item.snooze_until = snooze_until
        item.resolved_at = None
    else:
        item.snooze_until = None
        item.resolved_at = None
    store.save_inbox_item(item)
    store.add_audit_event(
        create_audit_event(user.id, "update_inbox_item", "inbox_item", item.id, {"status": item.status})
    )
    return ItemResponse(item=item)


def inbox_visible_to_user(item: InboxItem, user: User) -> bool:
    if user.role == UserRole.ADMIN:
        return True
    if item.scope == Scope.PRIVATE:
        if item.user_id is not None:
            return item.user_id == user.id
        return item.workspace_id == user.workspace_id and (
            item.project_id is None or item.project_id == user.default_project_id
        )
    if user.role == UserRole.TEAM_LEAD:
        return item.workspace_id in {None, user.workspace_id}
    if item.user_id is not None:
        return item.user_id == user.id
    return item.workspace_id in {None, user.workspace_id} and item.project_id in {None, user.default_project_id}
