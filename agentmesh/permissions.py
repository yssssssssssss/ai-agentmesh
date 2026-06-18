from __future__ import annotations

from fastapi import HTTPException, status

from agentmesh.models import Agent, MemoryStatus, PermissionPolicyRule, Scope, User, UserRole

ACTION_ACCEPT_TEAM_MEMORY = "accept_team_memory"
ACTION_MANAGE_PUBLIC_AGENT = "manage_public_agent"
ACTION_MANAGE_TEAM_MEMBERSHIP = "manage_team_membership"

DEFAULT_ROLE_POLICIES: dict[UserRole, set[str]] = {
    UserRole.USER: set(),
    UserRole.TEAM_LEAD: {
        ACTION_ACCEPT_TEAM_MEMORY,
        ACTION_MANAGE_PUBLIC_AGENT,
    },
    UserRole.ADMIN: {
        ACTION_ACCEPT_TEAM_MEMORY,
        ACTION_MANAGE_PUBLIC_AGENT,
        ACTION_MANAGE_TEAM_MEMBERSHIP,
    },
}


def is_admin(user: User) -> bool:
    return user.role == UserRole.ADMIN


def is_team_lead(user: User) -> bool:
    return user.role == UserRole.TEAM_LEAD


def ensure_admin(user: User) -> None:
    if is_admin(user):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")


def has_permission(user: User, action: str, rules: list[PermissionPolicyRule] | None = None) -> bool:
    role = UserRole(user.role)
    if role == UserRole.ADMIN:
        return True
    decision = action in DEFAULT_ROLE_POLICIES.get(role, set())
    for rule in rules or []:
        if not rule.enabled or rule.role != role or rule.action != action:
            continue
        decision = rule.effect == "allow"
    return decision


def ensure_permission(user: User, action: str, rules: list[PermissionPolicyRule] | None = None) -> None:
    if has_permission(user, action, rules):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission denied: {action}")


def ensure_can_manage_agent(
    user: User,
    agent: Agent,
    rules: list[PermissionPolicyRule] | None = None,
) -> None:
    if is_admin(user):
        return
    if agent.agent_type == "personal" and agent.owner_user_id == user.id:
        return
    if agent.agent_type != "personal" and has_permission(user, ACTION_MANAGE_PUBLIC_AGENT, rules):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to manage this agent")


def ensure_can_manage_agent_tools(
    user: User,
    agent: Agent,
    rules: list[PermissionPolicyRule] | None = None,
) -> None:
    ensure_can_manage_agent(user, agent, rules)


def ensure_can_update_memory(
    user: User,
    status_value: MemoryStatus | None,
    scope: Scope | None,
    rules: list[PermissionPolicyRule] | None = None,
) -> None:
    promotes_to_team = status_value == MemoryStatus.ACCEPTED or scope == Scope.TEAM_ACCEPTED
    if not promotes_to_team:
        return
    if has_permission(user, ACTION_ACCEPT_TEAM_MEMORY, rules):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to accept team memory")


def default_permission_policy_rules() -> list[PermissionPolicyRule]:
    return [
        PermissionPolicyRule(
            id="perm_team_lead_accept_team_memory",
            role=UserRole.TEAM_LEAD,
            action=ACTION_ACCEPT_TEAM_MEMORY,
            effect="allow",
            description="组长可以审核并接受团队候选记忆。",
        ),
        PermissionPolicyRule(
            id="perm_team_lead_manage_public_agent",
            role=UserRole.TEAM_LEAD,
            action=ACTION_MANAGE_PUBLIC_AGENT,
            effect="allow",
            description="组长可以调整公共 Agent 的基础配置。",
        ),
        PermissionPolicyRule(
            id="perm_admin_manage_team_membership",
            role=UserRole.ADMIN,
            action=ACTION_MANAGE_TEAM_MEMBERSHIP,
            effect="allow",
            description="管理员可以维护团队和成员关系。",
        ),
    ]


def ensure_permission_policy_seed_data(repository) -> None:
    existing_ids = {rule.id for rule in repository.permission_policy_rules}
    for rule in default_permission_policy_rules():
        if rule.id not in existing_ids:
            repository.save_permission_policy_rule(rule)
