"""LLM-backed intent classification with rule fallback."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from agentmesh.llm import LLMClient
from agentmesh.models import Intent

logger = logging.getLogger(__name__)

INTENT_CLASSIFICATION_SYSTEM_PROMPT = """\
你是 AgentMesh 意图分类器。根据用户输入，返回 JSON 格式的分类结果。

可选意图：
- ask_memory: 查询团队记忆、项目经验、历史知识
- generate_brief: 生成 Brief、PRD、方案文档、启动文档
- record_private_note: 记录个人笔记、日结、工作总结
- request_external_research: 搜索外部资料、竞品调研、查找类似项目
- request_data_query: 查询数据指标、点击率、转化率、数据分析
- request_risk_review: 风险审查、授权检查、合规检查
- create_memory_candidate: 沉淀经验、方法论、团队知识
- ask_system_info: 询问系统自身、模型、能力、配置、当前使用的模型
- general_chat: 普通对话、解释、澄清、问候，不需要进入项目工作流

返回格式（严格 JSON，无其他文字）：
{"intent": "<intent_name>", "entities": {"topic": "<主题>", "scope": "<范围>"}, "confidence": <0.0-1.0>}
"""

# 高置信度阈值：低于此值使用规则兜底
CONFIDENCE_THRESHOLD = 0.6


@dataclass
class IntentClassification:
    """意图分类结果。"""

    intent: Intent
    confidence: float = 1.0
    entities: dict[str, str] = field(default_factory=dict)
    source: str = "rule"  # "rule" | "llm"
    fallback_reason: str | None = None


def classify_intent_with_rules(content: str) -> IntentClassification:
    """基于规则的意图分类（fast-path）。

    对明确关键词直接命中，无需调用 LLM。
    """
    lowered = content.lower()

    # 高确定性关键词直接命中
    if any(word in lowered for word in ["什么模型", "哪个模型", "使用模型", "用的模型", "model"]) or (
        any(word in lowered for word in ["你", "当前", "现在"]) and any(word in lowered for word in ["模型", "能力", "配置"])
    ):
        return IntentClassification(intent=Intent.ASK_SYSTEM_INFO, confidence=0.95, source="rule")

    if any(word in lowered for word in ["风险", "授权", "合规", "检查素材", "risk"]):
        return IntentClassification(intent=Intent.REQUEST_RISK_REVIEW, confidence=0.95, source="rule")

    if any(word in lowered for word in ["沉淀", "方法论"]):
        return IntentClassification(intent=Intent.CREATE_MEMORY_CANDIDATE, confidence=0.85, source="rule")

    if any(word in lowered for word in ["团队记忆", "记忆里", "记忆库", "历史经验"]):
        return IntentClassification(intent=Intent.ASK_MEMORY, confidence=0.85, source="rule")

    if any(word in lowered for word in ["项目记录", "团队记录", "历史记录", "记录里"]) or (
        any(word in lowered for word in ["查", "找", "查询", "检索", "有没有"])
        and any(word in lowered for word in ["记录", "记忆"])
    ):
        return IntentClassification(intent=Intent.ASK_MEMORY, confidence=0.88, source="rule")

    if any(
        word in lowered
        for word in ["记录一下", "帮我记录", "记一下", "保存为笔记", "私有笔记", "私有记录", "个人记录", "日结"]
    ):
        return IntentClassification(intent=Intent.RECORD_PRIVATE_NOTE, confidence=0.9, source="rule")

    # 中等确定性：有歧义的关键词
    if any(word in lowered for word in ["brief", "prd", "启动文档"]) or (
        any(word in lowered for word in ["写", "生成", "草稿", "整理"])
        and any(word in lowered for word in ["方案", "文档", "brief", "prd", "启动"])
    ):
        return IntentClassification(intent=Intent.GENERATE_BRIEF, confidence=0.85, source="rule")

    if any(word in lowered for word in ["数据", "指标", "点击率", "转化率", "ctr", "conversion", "metric"]):
        return IntentClassification(intent=Intent.REQUEST_DATA_QUERY, confidence=0.9, source="rule")

    # 低确定性规则：可能触发但不确定
    if any(word in lowered for word in ["搜索", "竞品", "资料", "相似", "类似", "调研"]):
        return IntentClassification(intent=Intent.REQUEST_EXTERNAL_RESEARCH, confidence=0.7, source="rule")

    if any(word in lowered for word in ["去年", "历史", "做过"]) and any(
        word in lowered for word in ["项目", "活动页", "改版", "大促", "双11", "618"]
    ):
        return IntentClassification(intent=Intent.REQUEST_EXTERNAL_RESEARCH, confidence=0.7, source="rule")

    if any(word in lowered for word in ["方案", "文档"]):
        # "方案"可能是 brief 也可能是 research，置信度低
        return IntentClassification(intent=Intent.GENERATE_BRIEF, confidence=0.5, source="rule")

    if any(word in lowered for word in ["经验", "记忆"]):
        return IntentClassification(intent=Intent.ASK_MEMORY, confidence=0.5, source="rule")

    if any(word in lowered for word in ["查", "找"]):
        return IntentClassification(intent=Intent.REQUEST_EXTERNAL_RESEARCH, confidence=0.5, source="rule")

    return IntentClassification(intent=Intent.GENERAL_CHAT, confidence=0.4, source="rule")


def classify_intent_with_llm(content: str, llm_client: LLMClient) -> IntentClassification | None:
    """使用 LLM 进行意图分类。

    返回 None 表示 LLM 调用失败，调用方应回退到规则分类。
    """
    result, _ = _classify_intent_with_llm_detail(content, llm_client)
    return result


def _classify_intent_with_llm_detail(
    content: str,
    llm_client: LLMClient,
) -> tuple[IntentClassification | None, str | None]:
    """返回 LLM 分类结果及失败原因。"""
    try:
        raw = llm_client.complete(
            system_prompt=INTENT_CLASSIFICATION_SYSTEM_PROMPT,
            user_prompt=content,
        )
        # 尝试解析 JSON
        parsed = _parse_classification_json(raw)
        if parsed is None:
            return None, "model_invalid_json"
        return parsed, None
    except Exception as error:
        logger.debug("LLM intent classification failed: %s", error)
        return None, "model_call_failed"


def classify_intent_hybrid(content: str, llm_client: LLMClient | None = None) -> IntentClassification:
    """混合意图分类：LLM 优先，规则兜底。"""
    if llm_client is not None:
        llm_result, fallback_reason = _classify_intent_with_llm_detail(content, llm_client)
        if llm_result is not None and llm_result.confidence >= CONFIDENCE_THRESHOLD:
            return llm_result
        rule_result = classify_intent_with_rules(content)
        rule_result.fallback_reason = fallback_reason or "model_low_confidence"
        return rule_result
    rule_result = classify_intent_with_rules(content)
    rule_result.fallback_reason = "model_not_configured"
    return rule_result


def _parse_classification_json(raw: str) -> IntentClassification | None:
    """解析 LLM 返回的 JSON 分类结果。"""
    # 移除可能的 markdown 代码块包裹
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]) if len(lines) > 2 else text

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # 尝试从文本中提取 JSON 部分
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start:end])
            except json.JSONDecodeError:
                return None
        else:
            return None

    intent_str = data.get("intent", "")
    confidence = float(data.get("confidence", 0.5))
    entities = data.get("entities", {})

    # 映射 intent 字符串到枚举
    try:
        intent = Intent(intent_str)
    except ValueError:
        return None

    return IntentClassification(
        intent=intent,
        confidence=confidence,
        entities=entities if isinstance(entities, dict) else {},
        source="llm",
    )
