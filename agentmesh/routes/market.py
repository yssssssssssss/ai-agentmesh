"""Market observability route — exposes the autonomous-market workers' state and live counts.

Mirrors the memory router's worker-state exposure. Read-only ops surface; no auth (like
/health), returns non-sensitive counts only.
"""

from __future__ import annotations

from fastapi import APIRouter

from agentmesh.marketplace import MARKET_ENABLED, publish_worker_state, scout_worker_state
from agentmesh.models import BlackboardPostType
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
        },
    }
