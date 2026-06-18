from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from agentmesh.models import RiskPolicyRule


class RiskDecision(StrEnum):
    ALLOW = "allow"
    NEEDS_REVIEW = "needs_review"
    BLOCK = "block"


class RiskFinding(BaseModel):
    rule_id: str
    category: str
    message: str
    signal: str


class RiskAssessment(BaseModel):
    decision: RiskDecision
    findings: list[RiskFinding] = Field(default_factory=list)


PROMPT_INJECTION_SIGNALS = (
    "忽略之前",
    "忽略以上",
    "忽略所有指令",
    "ignore previous",
    "ignore all previous",
    "system prompt",
    "系统提示词",
    "developer message",
    "执行 rm",
    "rm -rf",
    "泄露",
    "api key",
)

HIGH_RISK_TOOL_SIGNALS = (
    "批量抓取",
    "批量爬取",
    "抓取所有",
    "下载所有",
    "批量下载",
    "内网",
    "写入团队记忆",
    "自动发布",
    "删除",
    "delete",
    "crawl all",
    "download all",
    "intranet",
)

ASSET_POLICY_SIGNALS = (
    "竞品截图",
    "第三方素材",
    "外部素材",
    "授权范围",
    "使用期限",
    "二次加工",
    "对外 brief",
    "对外brief",
)

HUMAN_APPROVAL_SIGNALS = (
    "已获得授权",
    "法务已确认",
    "审批通过",
    "用户已确认",
    "使用期限已确认",
)


def assess_external_content(content: str) -> RiskAssessment:
    findings = [
        RiskFinding(
            rule_id="prompt_injection_signal",
            category="prompt_injection",
            message="外部内容包含疑似提示词注入信号。",
            signal=signal,
        )
        for signal in match_signals(content, PROMPT_INJECTION_SIGNALS)
    ]
    return RiskAssessment(
        decision=RiskDecision.NEEDS_REVIEW if findings else RiskDecision.ALLOW,
        findings=findings,
    )


def assess_tool_request(content: str) -> RiskAssessment:
    findings = [
        RiskFinding(
            rule_id="high_risk_tool_signal",
            category="tool_call",
            message="请求涉及高风险工具调用，需要人工审批。",
            signal=signal,
        )
        for signal in match_signals(content, HIGH_RISK_TOOL_SIGNALS)
    ]
    return RiskAssessment(
        decision=RiskDecision.NEEDS_REVIEW if findings else RiskDecision.ALLOW,
        findings=findings,
    )


def assess_risk_review(content: str) -> RiskAssessment:
    return assess_risk_review_with_rules(content, default_risk_policy_rules())


def assess_risk_review_with_rules(content: str, rules: list[RiskPolicyRule]) -> RiskAssessment:
    findings = []
    active_rules = [rule for rule in rules if rule.enabled] or default_risk_policy_rules()
    for rule in active_rules:
        if rule.signal.lower() in content.lower():
            findings.append(
                RiskFinding(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    message=rule.message,
                    signal=rule.signal,
                )
            )
    allow_categories = {
        rule.category
        for rule in active_rules
        if rule.enabled and rule.decision == RiskDecision.ALLOW and rule.signal.lower() in content.lower()
    }
    if allow_categories and not any(finding.category in {"prompt_injection", "tool_call"} for finding in findings):
        return RiskAssessment(decision=RiskDecision.ALLOW, findings=findings)
    if any(
        rule.decision == RiskDecision.BLOCK and rule.enabled and rule.signal.lower() in content.lower()
        for rule in active_rules
    ):
        return RiskAssessment(decision=RiskDecision.BLOCK, findings=findings)
    return RiskAssessment(decision=RiskDecision.NEEDS_REVIEW if findings else RiskDecision.ALLOW, findings=findings)


def default_risk_policy_rules() -> list[RiskPolicyRule]:
    rules: list[RiskPolicyRule] = []
    rules.extend(
        RiskPolicyRule(
            id=f"risk_policy_prompt_{index}",
            rule_id="prompt_injection_signal",
            category="prompt_injection",
            message="外部内容包含疑似提示词注入信号。",
            signal=signal,
            decision=RiskDecision.NEEDS_REVIEW,
        )
        for index, signal in enumerate(PROMPT_INJECTION_SIGNALS)
    )
    rules.extend(
        RiskPolicyRule(
            id=f"risk_policy_tool_{index}",
            rule_id="high_risk_tool_signal",
            category="tool_call",
            message="请求涉及高风险工具调用，需要人工审批。",
            signal=signal,
            decision=RiskDecision.NEEDS_REVIEW,
        )
        for index, signal in enumerate(HIGH_RISK_TOOL_SIGNALS)
    )
    rules.extend(
        RiskPolicyRule(
            id=f"risk_policy_asset_{index}",
            rule_id="asset_policy_signal",
            category="source_policy",
            message="素材或来源策略需要确认授权和使用边界。",
            signal=signal,
            decision=RiskDecision.NEEDS_REVIEW,
        )
        for index, signal in enumerate(ASSET_POLICY_SIGNALS)
    )
    rules.extend(
        RiskPolicyRule(
            id=f"risk_policy_approval_{index}",
            rule_id="human_approval_signal",
            category="approval",
            message="内容包含人工确认或法务审批结果。",
            signal=signal,
            decision=RiskDecision.ALLOW,
        )
        for index, signal in enumerate(HUMAN_APPROVAL_SIGNALS)
    )
    return rules


def ensure_risk_policy_seed_data(repository) -> None:
    existing_ids = {rule.id for rule in repository.risk_policy_rules}
    for rule in default_risk_policy_rules():
        if rule.id not in existing_ids:
            repository.save_risk_policy_rule(rule)


def match_signals(content: str, signals: tuple[str, ...]) -> list[str]:
    lowered = content.lower()
    return [signal for signal in signals if signal in lowered]
