"""Market observability route — exposes the autonomous-market workers' state and live counts.

Mirrors the memory router's worker-state exposure. Read-only ops surface; no auth (like
/health), returns non-sensitive counts only.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from agentmesh.marketplace import MARKET_ENABLED, publish_worker_state, scout_worker_state
from agentmesh.models import BlackboardPostType, MarketParticipation, MarketParticipationRequest, User
from agentmesh.routes.deps import current_user
from agentmesh.store import store

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/status")
def market_status() -> dict[str, object]:
    signals = [post for post in store.blackboard_posts if post.post_type == BlackboardPostType.MARKETPLACE_SIGNAL]
    return {
        "enabled": MARKET_ENABLED,
        "publish_worker": publish_worker_state,
        "scout_worker": scout_worker_state,
        "counts": {
            "signals": len(signals),
            "matches": len(store.contribution_points),
            "consent_grants": len([grant for grant in store.consent_grants if grant.active]),
            "participants": len([p for p in store.market_participations if p.enabled]),
        },
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

