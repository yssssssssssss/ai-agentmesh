"""Authenticated market observability and current-user participation routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from agentmesh.marketplace import MARKET_ENABLED, publish_worker_state, scout_worker_state
from agentmesh.models import BlackboardPostType, MarketParticipation, MarketParticipationRequest, User
from agentmesh.routes.deps import current_user
from agentmesh.seed import list_users
from agentmesh.store import store

router = APIRouter(prefix="/api/market", tags=["market"])


def _counts() -> dict[str, int]:
    signals = [post for post in store.blackboard_posts if post.post_type == BlackboardPostType.MARKETPLACE_SIGNAL]
    return {
        "signals": len(signals),
        "matches": len([event for event in store.audit_events if event.action == "marketplace_match"]),
        "consent_grants": len([grant for grant in store.consent_grants if grant.active]),
        "participants": len([record for record in store.market_participations if record.enabled]),
    }


@router.get("/status")
def market_status(_: User = Depends(current_user)) -> dict[str, object]:
    return {
        "enabled": MARKET_ENABLED,
        "publish_worker": publish_worker_state,
        "scout_worker": scout_worker_state,
        "counts": _counts(),
    }


def _parse_signal(content: str) -> dict[str, str]:
    fields = {"capability": "", "offer": "", "need": ""}
    labels = {"能力": "capability", "可提供": "offer", "需要": "need"}
    for raw in content.splitlines():
        line = raw.strip()
        for label, key in labels.items():
            for sep in (f"{label}：", f"{label}:"):
                if line.startswith(sep):
                    fields[key] = line[len(sep):].strip()
    return fields


@router.get("/board")
def market_board(_: User = Depends(current_user)) -> dict[str, object]:
    """Everything the dashboard needs in one fetch: workers, counts, signal cards, matches."""
    users_by_id = {user.id: user for user in list_users(store)}
    signals = []
    for post in store.blackboard_posts:
        if post.post_type != BlackboardPostType.MARKETPLACE_SIGNAL:
            continue
        owner_id = post.task_id.removeprefix("signal_")
        owner = users_by_id.get(owner_id)
        signals.append(
            {
                "owner_id": owner_id,
                "owner_name": owner.name if owner else owner_id,
                "participating": store.is_market_participant(owner_id),
                **_parse_signal(post.content),
                "created_at": post.created_at.isoformat(),
            }
        )
    signals.sort(key=lambda item: item["created_at"], reverse=True)

    def _name(user_id: str | None) -> str | None:
        user = users_by_id.get(user_id) if user_id else None
        return user.name if user else user_id

    matches = [
        {
            "helper_id": event.metadata.get("helper"),
            "helper_name": _name(event.metadata.get("helper")),
            "needer_id": event.target_id,
            "needer_name": _name(event.target_id),
            "status": event.metadata.get("status"),
            "at": event.created_at.isoformat(),
        }
        for event in store.audit_events
        if event.action == "marketplace_match"
    ]
    matches = matches[-30:][::-1]

    return {
        "enabled": MARKET_ENABLED,
        "publish_worker": publish_worker_state,
        "scout_worker": scout_worker_state,
        "counts": _counts(),
        "signals": signals,
        "matches": matches,
    }


@router.put("/participation", response_model=MarketParticipation)
def set_participation(
    request: MarketParticipationRequest,
    user: User = Depends(current_user),
) -> MarketParticipation:
    """The current user opts their twins into (or out of) the autonomous market."""
    return store.set_market_participation(user.id, request.enabled)


@router.get("/participation", response_model=MarketParticipation)
def get_participation(user: User = Depends(current_user)) -> MarketParticipation:
    record = store.get_market_participation(user.id)
    return record or MarketParticipation(id=user.id, user_id=user.id, enabled=False)

