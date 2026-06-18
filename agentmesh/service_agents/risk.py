from __future__ import annotations

from agentmesh.models import BlackboardPost, BlackboardPostType, CollaborationStage, Scope, Source, Task
from agentmesh.risk import RiskAssessment, RiskDecision, assess_risk_review_with_rules
from agentmesh.store import SQLiteStore


class RiskAgent:
    actor = "risk_agent"

    def __init__(self, repository: SQLiteStore):
        self.repository = repository

    def review(self, task: Task, request_post: BlackboardPost) -> BlackboardPost:
        assessment = assess_risk_review_with_rules(request_post.content, self.repository.risk_policy_rules)
        source = Source(
            title="risk_agent 策略规则包",
            source_type="risk_rule",
            reference="risk://policy-backed-review",
        )
        return BlackboardPost(
            task_id=task.id,
            post_type=BlackboardPostType.RISK,
            actor=self.actor,
            title=self._title(assessment),
            content=self._content(assessment),
            scope=Scope.PROJECT,
            permission="project_visible",
            sources=[source],
            read_by_agents=["personal_agent"],
            related_post_id=request_post.id,
            collaboration_stage=CollaborationStage.REVIEW,
            current_owner_agent_id=self.actor,
            current_owner_label="risk_agent",
            done_when="用户在收件箱确认风险处理方式",
        )

    @staticmethod
    def _title(assessment: RiskAssessment) -> str:
        if assessment.decision == RiskDecision.BLOCK:
            return "发现阻断风险"
        return "发现风险确认项" if assessment.decision == RiskDecision.NEEDS_REVIEW else "未发现阻断风险"

    @staticmethod
    def _content(assessment: RiskAssessment) -> str:
        if not assessment.findings:
            return "risk_agent 根据策略规则包未命中风险信号，可继续推进。"
        findings = "；".join(
            f"{finding.rule_id}/{finding.category}: {finding.message} 命中“{finding.signal}”"
            for finding in assessment.findings
        )
        if assessment.decision == RiskDecision.ALLOW:
            return f"risk_agent 根据策略规则包允许继续推进。规则记录：{findings}。"
        if assessment.decision == RiskDecision.BLOCK:
            return f"risk_agent 根据策略规则包阻断继续推进。规则命中：{findings}。"
        return f"risk_agent 根据策略规则包要求人工确认。规则命中：{findings}。"
