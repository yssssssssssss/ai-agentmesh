"""Inbox routes."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException

from agentmesh.models import (
    InboxItem,
    InboxUpdateRequest,
    ItemResponse,
    ItemsResponse,
    MemoryItem,
    Scope,
    User,
    UserRole,
    now_utc,
)
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


@router.post("/{item_id}/confirm-brief")
def confirm_brief_item(
    item_id: str,
    user: User = Depends(current_user),
) -> dict[str, object]:
    item = store.get_inbox_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    if not inbox_visible_to_user(item, user):
        raise HTTPException(status_code=403, detail="Not allowed to update this inbox item")
    document_id = item.metadata.get("document_id")
    if item.item_type != "decision_review" or item.metadata.get("artifact_type") != "brief_draft" or not document_id:
        raise HTTPException(status_code=400, detail="Inbox item is not a brief draft")
    document = store.get_document(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Brief draft document not found")

    memory = store.add_memory_item(
        MemoryItem(
            title=f"候选团队记忆：{document.title}",
            summary=_brief_memory_summary(document.text),
            memory_type="brief_decision",
            scope=Scope.TEAM_CANDIDATE,
            workspace_id=item.workspace_id or user.workspace_id,
            project_id=item.project_id or user.default_project_id,
            sources=[document.source],
            metadata={"document_id": document.id, "artifact_type": "brief_draft", "inbox_item_id": item.id},
        )
    )
    now = now_utc()
    item.status = "resolved"
    item.acknowledged_at = item.acknowledged_at or now
    item.resolved_at = now
    item.updated_at = now
    item.metadata["confirmed_memory_id"] = memory.id
    item.metadata["confirmed_document_id"] = document.id
    store.save_inbox_item(item)
    store.add_audit_event(
        create_audit_event(
            user.id,
            "confirm_brief_draft",
            "inbox_item",
            item.id,
            {"document_id": document.id, "memory_id": memory.id},
        )
    )
    return {"item": item, "memory_item": memory}


@router.post("/{item_id}/resolve-injection-review")
def resolve_injection_review_item(
    item_id: str,
    action: str,
    user: User = Depends(current_user),
) -> dict[str, object]:
    from agentmesh.agents import RequestAlreadyFulfilledError
    from agentmesh.routes.chat import agent

    item = store.get_inbox_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Inbox item not found")
    if not inbox_visible_to_user(item, user):
        raise HTTPException(status_code=403, detail="Not allowed to update this inbox item")
    if item.item_type != "prompt_injection_review":
        raise HTTPException(status_code=400, detail="Inbox item is not a prompt-injection review")
    if action not in {"release", "discard"}:
        raise HTTPException(status_code=400, detail="action must be 'release' or 'discard'")
    request_post_id = item.metadata.get("request_post_id")
    evidence_post_id = item.metadata.get("evidence_post_id")
    if not request_post_id or not evidence_post_id:
        raise HTTPException(status_code=400, detail="Inbox item is missing quarantine references")
    request_post = store.get_blackboard_post(request_post_id)
    evidence_post = store.get_blackboard_post(evidence_post_id)
    if request_post is None or evidence_post is None:
        raise HTTPException(status_code=404, detail="Quarantined blackboard posts not found")

    try:
        fulfillment = agent.resolve_quarantined_research(request_post, evidence_post, user, action)
    except RequestAlreadyFulfilledError:
        raise HTTPException(status_code=409, detail="Quarantined evidence has already been resolved")

    now = now_utc()
    item.status = "resolved"
    item.acknowledged_at = item.acknowledged_at or now
    item.resolved_at = now
    item.updated_at = now
    item.metadata["injection_review_action"] = action
    store.save_inbox_item(item)
    store.add_audit_event(
        create_audit_event(
            user.id,
            "resolve_injection_review",
            "inbox_item",
            item.id,
            {
                "action": action,
                "request_post_id": request_post.id,
                "evidence_post_id": evidence_post.id,
                "task_id": fulfillment.task.id,
            },
        )
    )
    return {
        "item": item,
        "request_post": fulfillment.request_post,
        "evidence_post": fulfillment.evidence_post,
        "task": fulfillment.task,
        "assistant_message": fulfillment.assistant_message,
        "activity_logs": fulfillment.activity_logs,
        "quarantined": fulfillment.quarantined,
    }


def _brief_memory_summary(text: str) -> str:
    normalized = " ".join(text.split())
    if not normalized:
        return "用户已确认 Brief 草稿，可进入团队候选记忆审核。"
    return normalized[:800]


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
