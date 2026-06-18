"""Shared dependencies for route modules."""

from __future__ import annotations

from fastapi import Request

from agentmesh.auth import require_current_user
from agentmesh.model_registry import ensure_model_seed_data
from agentmesh.models import AuditEvent, User
from agentmesh.risk import RiskDecision, ensure_risk_policy_seed_data
from agentmesh.seed import ensure_seed_data
from agentmesh.store import store
from agentmesh.tools import ensure_tool_seed_data


def current_user(request: Request) -> User:
    ensure_seed_data(store)
    ensure_tool_seed_data(store, granted_by="system")
    ensure_model_seed_data(store)
    ensure_risk_policy_seed_data(store)
    return require_current_user(store, request)


def create_audit_event(actor: str, action: str, target_type: str, target_id: str, metadata: dict[str, object]):
    return AuditEvent(actor=actor, action=action, target_type=target_type, target_id=target_id, metadata=metadata)


def validate_risk_decision(value: str) -> str:
    from fastapi import HTTPException

    if value not in {item.value for item in RiskDecision}:
        raise HTTPException(status_code=400, detail="Unsupported risk decision")
    return value
