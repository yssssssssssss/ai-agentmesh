"""Tests for A3: team memory isolation by team_id."""

from __future__ import annotations

import tempfile
from pathlib import Path

from agentmesh.models import (
    MemoryItem,
    MemoryStatus,
    Scope,
    Team,
    TeamMembership,
    User,
    UserRole,
)
from agentmesh.store import SQLiteStore


def _fresh_store() -> SQLiteStore:
    db_path = Path(tempfile.mktemp(suffix=".sqlite3"))
    return SQLiteStore(db_path=db_path)


def _setup_teams(store: SQLiteStore) -> tuple[str, str, str, str]:
    """Create 2 teams, user_a in team_1 only, user_b in team_2 only.
    Returns (team1_id, team2_id, user_a_id, user_b_id)."""
    team1 = Team(workspace_id="ws1", name="前端团队")
    team2 = Team(workspace_id="ws1", name="后端团队")
    store._upsert("teams", team1)
    store._upsert("teams", team2)

    user_a = User(
        id="user_a", workspace_id="ws1", default_project_id="proj1",
        name="前端工程师", role=UserRole.USER, personal_agent_id="agent_a",
    )
    user_b = User(
        id="user_b", workspace_id="ws1", default_project_id="proj1",
        name="后端工程师", role=UserRole.USER, personal_agent_id="agent_b",
    )
    store._upsert("users", user_a)
    store._upsert("users", user_b)

    mem1 = TeamMembership(team_id=team1.id, user_id="user_a")
    mem2 = TeamMembership(team_id=team2.id, user_id="user_b")
    store._upsert("team_memberships", mem1)
    store._upsert("team_memberships", mem2)

    return team1.id, team2.id, user_a.id, user_b.id


class TestTeamMemoryIsolation:
    def test_user_sees_own_team_memory(self) -> None:
        s = _fresh_store()
        team1_id, _, user_a, _ = _setup_teams(s)
        s.add_memory_item(
            MemoryItem(
                title="前端团队部署规范",
                summary="前端团队内部的部署规范文档",
                memory_type="standard",
                scope=Scope.TEAM_ACCEPTED,
                status=MemoryStatus.ACCEPTED,
                workspace_id="ws1",
                team_id=team1_id,
            )
        )
        results = s.search("部署规范", {Scope.TEAM_ACCEPTED}, workspace_id="ws1", user_id=user_a)
        assert len(results) == 1
        assert "前端" in results[0].title

    def test_user_cannot_see_other_team_memory(self) -> None:
        s = _fresh_store()
        _, team2_id, user_a, _ = _setup_teams(s)
        s.add_memory_item(
            MemoryItem(
                title="后端团队部署规范",
                summary="后端团队内部的部署流程说明",
                memory_type="standard",
                scope=Scope.TEAM_ACCEPTED,
                status=MemoryStatus.ACCEPTED,
                workspace_id="ws1",
                team_id=team2_id,
            )
        )
        results = s.search("部署规范", {Scope.TEAM_ACCEPTED}, workspace_id="ws1", user_id=user_a)
        team_results = [r for r in results if r.scope == Scope.TEAM_ACCEPTED]
        assert len(team_results) == 0

    def test_no_team_id_means_workspace_wide(self) -> None:
        """Memory without team_id is visible to all workspace users."""
        s = _fresh_store()
        _, _, user_a, user_b = _setup_teams(s)
        s.add_memory_item(
            MemoryItem(
                title="全工作区部署规范",
                summary="所有团队共享的部署规范",
                memory_type="standard",
                scope=Scope.TEAM_ACCEPTED,
                status=MemoryStatus.ACCEPTED,
                workspace_id="ws1",
                team_id=None,
            )
        )
        results_a = s.search("部署规范", {Scope.TEAM_ACCEPTED}, workspace_id="ws1", user_id=user_a)
        results_b = s.search("部署规范", {Scope.TEAM_ACCEPTED}, workspace_id="ws1", user_id=user_b)
        assert len(results_a) == 1
        assert len(results_b) == 1

    def test_admin_sees_all_team_memories(self) -> None:
        s = _fresh_store()
        team1_id, team2_id, _, _ = _setup_teams(s)
        admin = User(
            id="admin_x", workspace_id="ws1", default_project_id="proj1",
            name="管理员", role=UserRole.ADMIN, personal_agent_id="agent_admin",
        )
        s._upsert("users", admin)
        s.add_memory_item(
            MemoryItem(
                title="前端团队部署规范",
                summary="前端团队内部规范",
                memory_type="standard",
                scope=Scope.TEAM_ACCEPTED,
                status=MemoryStatus.ACCEPTED,
                workspace_id="ws1",
                team_id=team1_id,
            )
        )
        s.add_memory_item(
            MemoryItem(
                title="后端团队部署规范",
                summary="后端团队内部规范",
                memory_type="standard",
                scope=Scope.TEAM_ACCEPTED,
                status=MemoryStatus.ACCEPTED,
                workspace_id="ws1",
                team_id=team2_id,
            )
        )
        results = s.search("部署规范", {Scope.TEAM_ACCEPTED}, workspace_id="ws1", user_id=admin.id)
        assert len(results) == 2

    def test_team_candidate_also_isolated(self) -> None:
        """TEAM_CANDIDATE scope respects team isolation too."""
        s = _fresh_store()
        _, team2_id, user_a, _ = _setup_teams(s)
        s.add_memory_item(
            MemoryItem(
                title="后端待审核部署经验",
                summary="后端团队的候选记忆",
                memory_type="standard",
                scope=Scope.TEAM_CANDIDATE,
                status=MemoryStatus.PROPOSED,
                workspace_id="ws1",
                team_id=team2_id,
            )
        )
        results = s.search("部署经验", {Scope.TEAM_CANDIDATE}, workspace_id="ws1", user_id=user_a)
        assert len(results) == 0

    def test_no_user_id_skips_team_check(self) -> None:
        """System-level search without user_id sees all team memories."""
        s = _fresh_store()
        team1_id, _, _, _ = _setup_teams(s)
        s.add_memory_item(
            MemoryItem(
                title="前端团队部署规范",
                summary="前端内部规范",
                memory_type="standard",
                scope=Scope.TEAM_ACCEPTED,
                status=MemoryStatus.ACCEPTED,
                workspace_id="ws1",
                team_id=team1_id,
            )
        )
        results = s.search("部署规范", {Scope.TEAM_ACCEPTED}, workspace_id="ws1", user_id=None)
        assert len(results) == 1
