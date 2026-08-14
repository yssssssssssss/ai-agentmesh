"""Tests for P1 search budget control (max_results / max_chars)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from agentmesh.models import MemoryItem, Scope
from agentmesh.store import SQLiteStore


def _fresh_store() -> SQLiteStore:
    db_path = Path(tempfile.mktemp(suffix=".sqlite3"))
    return SQLiteStore(db_path=db_path)


def _seed_memories(store: SQLiteStore, count: int, prefix: str = "记忆条目") -> None:
    for i in range(count):
        store.add_memory_item(
            MemoryItem(
                title=f"{prefix}编号{i:03d}的部署记录",
                summary=f"这是第{i}条关于部署流程的详细记录内容，包含了完整的操作步骤和注意事项说明",
                memory_type="note",
                scope=Scope.TEAM_ACCEPTED,
                workspace_id="ws1",
                project_id="proj1",
            )
        )


class TestMaxResults:
    def test_default_limit_caps_at_20(self) -> None:
        s = _fresh_store()
        _seed_memories(s, 30)
        results = s.search("部署", {Scope.TEAM_ACCEPTED}, workspace_id="ws1", project_id="proj1")
        assert len(results) <= 20

    def test_custom_limit_respected(self) -> None:
        s = _fresh_store()
        _seed_memories(s, 10)
        results = s.search(
            "部署", {Scope.TEAM_ACCEPTED}, workspace_id="ws1", project_id="proj1", max_results=3
        )
        assert len(results) == 3

    def test_limit_larger_than_available(self) -> None:
        s = _fresh_store()
        _seed_memories(s, 5)
        results = s.search(
            "部署", {Scope.TEAM_ACCEPTED}, workspace_id="ws1", project_id="proj1", max_results=100
        )
        assert len(results) == 5


class TestMaxChars:
    def test_char_budget_truncates_results(self) -> None:
        s = _fresh_store()
        _seed_memories(s, 10)
        results_full = s.search(
            "部署", {Scope.TEAM_ACCEPTED}, workspace_id="ws1", project_id="proj1", max_chars=50000
        )
        results_tight = s.search(
            "部署", {Scope.TEAM_ACCEPTED}, workspace_id="ws1", project_id="proj1", max_chars=200
        )
        assert len(results_tight) < len(results_full)
        assert len(results_tight) >= 1

    def test_at_least_one_result_even_if_over_budget(self) -> None:
        """First result always included even if it alone exceeds max_chars."""
        s = _fresh_store()
        s.add_memory_item(
            MemoryItem(
                title="部署" * 50,
                summary="非常长的内容" * 100,
                memory_type="note",
                scope=Scope.TEAM_ACCEPTED,
                workspace_id="ws1",
                project_id="proj1",
            )
        )
        results = s.search(
            "部署", {Scope.TEAM_ACCEPTED}, workspace_id="ws1", project_id="proj1", max_chars=100
        )
        assert len(results) == 1

    def test_char_budget_counts_title_and_summary(self) -> None:
        s = _fresh_store()
        _seed_memories(s, 10)
        results = s.search(
            "部署", {Scope.TEAM_ACCEPTED}, workspace_id="ws1", project_id="proj1", max_chars=50000
        )
        total_chars = sum(len(r.title) + len(r.summary) for r in results)
        results_capped = s.search(
            "部署",
            {Scope.TEAM_ACCEPTED},
            workspace_id="ws1",
            project_id="proj1",
            max_chars=total_chars // 2,
        )
        capped_chars = sum(len(r.title) + len(r.summary) for r in results_capped)
        assert capped_chars <= total_chars // 2 + 200  # tolerance for first-result inclusion


class TestBudgetBackwardCompatibility:
    def test_no_budget_params_uses_defaults(self) -> None:
        """Calling without budget params still works (backward compat)."""
        s = _fresh_store()
        _seed_memories(s, 5)
        results = s.search("部署", {Scope.TEAM_ACCEPTED}, workspace_id="ws1", project_id="proj1")
        assert len(results) == 5

    def test_combined_limits(self) -> None:
        """Both max_results and max_chars apply; whichever is tighter wins."""
        s = _fresh_store()
        _seed_memories(s, 10)
        results = s.search(
            "部署",
            {Scope.TEAM_ACCEPTED},
            workspace_id="ws1",
            project_id="proj1",
            max_results=3,
            max_chars=50000,
        )
        assert len(results) == 3
