"""Tests for hybrid intent classification."""

from __future__ import annotations

from unittest.mock import MagicMock

from agentmesh.intent import (
    _parse_classification_json,
    classify_intent_hybrid,
    classify_intent_with_rules,
)
from agentmesh.models import Intent


class TestRuleClassification:
    def test_risk_keywords(self):
        result = classify_intent_with_rules("检查素材授权风险")
        assert result.intent == Intent.REQUEST_RISK_REVIEW
        assert result.confidence >= 0.9

    def test_data_keywords(self):
        result = classify_intent_with_rules("查一下上周点击率数据")
        assert result.intent == Intent.REQUEST_DATA_QUERY
        assert result.confidence >= 0.9

    def test_record_keywords(self):
        result = classify_intent_with_rules("记录一下今天的工作")
        assert result.intent == Intent.RECORD_PRIVATE_NOTE
        assert result.confidence >= 0.9

    def test_project_record_query_prefers_memory(self):
        result = classify_intent_with_rules("我想找团队的 618 的项目记录")
        assert result.intent == Intent.ASK_MEMORY
        assert result.confidence >= 0.8

    def test_history_record_query_is_not_private_note(self):
        result = classify_intent_with_rules("历史记录里有没有 618 项目的结论")
        assert result.intent == Intent.ASK_MEMORY
        assert result.intent != Intent.RECORD_PRIVATE_NOTE

    def test_brief_keywords(self):
        result = classify_intent_with_rules("帮我生成 Brief")
        assert result.intent == Intent.GENERATE_BRIEF
        assert result.confidence >= 0.8

    def test_research_keywords(self):
        result = classify_intent_with_rules("搜索竞品方案")
        assert result.intent == Intent.REQUEST_EXTERNAL_RESEARCH
        assert result.confidence >= 0.6

    def test_similar_project_question_is_research(self):
        result = classify_intent_with_rules("我们去年有没有做过类似的618大促家电首页改版？")
        assert result.intent == Intent.REQUEST_EXTERNAL_RESEARCH
        assert result.confidence >= 0.6

    def test_team_memory_metric_question_prefers_memory_over_data(self):
        result = classify_intent_with_rules("团队记忆里有没有关于首屏转化率的经验？")
        assert result.intent == Intent.ASK_MEMORY
        assert result.confidence >= 0.8

    def test_startup_document_generation_prefers_brief_over_research(self):
        result = classify_intent_with_rules("根据现有资料写一个启动方案文档")
        assert result.intent == Intent.GENERATE_BRIEF
        assert result.confidence >= 0.8

    def test_memory_keywords(self):
        result = classify_intent_with_rules("沉淀这个方法论")
        assert result.intent == Intent.CREATE_MEMORY_CANDIDATE
        assert result.confidence >= 0.8

    def test_model_question_is_system_info(self):
        result = classify_intent_with_rules("你使用什么模型")
        assert result.intent == Intent.ASK_SYSTEM_INFO
        assert result.confidence >= 0.9

    def test_ambiguous_falls_to_low_confidence(self):
        result = classify_intent_with_rules("看看这个方案")
        assert result.confidence < 0.6

    def test_unknown_defaults_to_general_chat(self):
        result = classify_intent_with_rules("你好呀")
        assert result.intent == Intent.GENERAL_CHAT
        assert result.confidence < 0.5


class TestHybridClassification:
    def test_llm_classification_runs_before_high_confidence_rule(self):
        mock_llm = MagicMock()
        mock_llm.complete.return_value = (
            '{"intent": "request_external_research", "entities": {"topic": "素材风险"}, "confidence": 0.8}'
        )
        result = classify_intent_hybrid("检查素材风险", mock_llm)
        assert result.intent == Intent.REQUEST_EXTERNAL_RESEARCH
        assert result.source == "llm"
        mock_llm.complete.assert_called_once()

    def test_low_confidence_rule_calls_llm(self):
        mock_llm = MagicMock()
        mock_llm.complete.return_value = '{"intent": "request_external_research", "entities": {"topic": "方案"}, "confidence": 0.85}'
        result = classify_intent_hybrid("看看这个方案", mock_llm)
        assert result.intent == Intent.REQUEST_EXTERNAL_RESEARCH
        assert result.source == "llm"
        mock_llm.complete.assert_called_once()

    def test_llm_failure_falls_back_to_rule(self):
        mock_llm = MagicMock()
        mock_llm.complete.side_effect = Exception("API error")
        result = classify_intent_hybrid("看看这个方案", mock_llm)
        assert result.source == "rule"
        assert result.fallback_reason == "model_call_failed"

    def test_low_confidence_llm_fallback_reason(self):
        mock_llm = MagicMock()
        mock_llm.complete.return_value = '{"intent": "general_chat", "entities": {}, "confidence": 0.2}'
        result = classify_intent_hybrid("看看这个方案", mock_llm)
        assert result.source == "rule"
        assert result.fallback_reason == "model_low_confidence"

    def test_no_llm_uses_rule_only(self):
        result = classify_intent_hybrid("看看这个方案", None)
        assert result.source == "rule"
        assert result.fallback_reason == "model_not_configured"


class TestParseClassificationJson:
    def test_valid_json(self):
        result = _parse_classification_json(
            '{"intent": "generate_brief", "entities": {"topic": "项目"}, "confidence": 0.9}'
        )
        assert result is not None
        assert result.intent == Intent.GENERATE_BRIEF
        assert result.confidence == 0.9
        assert result.entities == {"topic": "项目"}

    def test_json_in_markdown_code_block(self):
        result = _parse_classification_json(
            '```json\n{"intent": "ask_memory", "entities": {}, "confidence": 0.7}\n```'
        )
        assert result is not None
        assert result.intent == Intent.ASK_MEMORY

    def test_json_with_surrounding_text(self):
        result = _parse_classification_json(
            '分析结果：{"intent": "record_private_note", "entities": {}, "confidence": 0.8} 以上。'
        )
        assert result is not None
        assert result.intent == Intent.RECORD_PRIVATE_NOTE

    def test_invalid_intent_returns_none(self):
        result = _parse_classification_json(
            '{"intent": "nonexistent_intent", "confidence": 0.9}'
        )
        assert result is None

    def test_invalid_json_returns_none(self):
        result = _parse_classification_json("这不是 JSON")
        assert result is None
