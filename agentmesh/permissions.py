from __future__ import annotations

from fastapi import HTTPException, status

from agentmesh.models import Agent, MemoryStatus, Scope, User, UserRole


def is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


def is_team_lead(user: User) -> bool:
    return user.role == UserRole.TEAM_LEAD


def ensure_admin(user: User) -> None:
    if is_admin(user):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")


def ensure_can_manage_agent(user: User, agent: Agent) -> None:
    if is_admin(user):
        return
    if agent.agent_type == "personal" and agent.owner_user_id == user.id:
        return
    if agent.agent_type != "personal" and is_team_lead(user):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to manage this agent")


def ensure_can_manage_agent_tools(user: User, agent: Agent) -> None:
    ensure_can_manage_agent(user, agent)


def ensure_can_update_memory(user: User, status_value: MemoryStatus | None, scope: Scope | None) -> None:
    promotes_to_team = status_value == MemoryStatus.ACCEPTED or scope == Scope.TEAM_ACCEPTED
    if not promotes_to_team:
        return
    if is_admin(user) or is_team_lead(user):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to accept team memory")
