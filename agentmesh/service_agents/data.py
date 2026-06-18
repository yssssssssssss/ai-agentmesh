from __future__ import annotations

from agentmesh.datasources import DataSourceRegistry, default_data_source_registry
from agentmesh.models import BlackboardPost, BlackboardPostType, CollaborationStage, Scope, Task, User
from agentmesh.seed import PROJECT, WORKSPACE


class MockDataAgent:
    actor = "data_agent"

    def __init__(self, registry: DataSourceRegistry | None = None):
        self.registry = registry or default_data_source_registry()

    def query(self, task: Task, request_post: BlackboardPost, content: str, user: User) -> BlackboardPost:
        result = self.registry.query_first_available(
            connector_names=["o2_cli", "local_metrics"],
            operation="query",
            parameters={"metric": self._metric_from_content(content), "query": content, "limit": 5},
            workspace_id=WORKSPACE.id,
            project_id=PROJECT.id,
            requested_by=user.id,
        )
        records = "；".join(", ".join(f"{key}={value}" for key, value in record.items()) for record in result.records)
        diagnostics = result.metadata.get("fallback_diagnostics")
        diagnostic_text = f"（fallback: {diagnostics}）" if diagnostics else ""
        return BlackboardPost(
            task_id=task.id,
            post_type=BlackboardPostType.EVIDENCE,
            actor=self.actor,
            title=result.title,
            content=f"data_agent 通过 {result.connector_name} 返回指标数据：{records}。{diagnostic_text}",
            scope=Scope.PROJECT,
            permission="project_visible",
            sources=[result.source],
            read_by_agents=["personal_agent"],
            related_post_id=request_post.id,
            collaboration_stage=CollaborationStage.REVIEW,
            current_owner_agent_id=self.actor,
            current_owner_label="data_agent",
            done_when="个人 Agent 完成数据合成并返回用户",
        )

    @staticmethod
    def _metric_from_content(content: str) -> str:
        lowered = content.lower()
        if any(word in lowered for word in ["点击", "ctr"]):
            return "ctr"
        if any(word in lowered for word in ["入口", "entry"]):
            return "entry_efficiency"
        return "conversion_rate"
