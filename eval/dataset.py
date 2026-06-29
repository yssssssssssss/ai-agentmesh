"""评估数据集：定义测试场景和期望输出。"""

from __future__ import annotations

SCENARIOS = [
    # --- 场景 1: 找类似项目 ---
    {
        "id": "find_similar_project_01",
        "category": "find_similar_project",
        "input": "$research.request 我们去年有没有做过类似的618大促家电首页改版？",
        "expected_workflow": "request_external_research",
        "expected_checks": {
            "has_source": True,
            "has_evidence_post": True,
            "has_activity_log": True,
            "response_mentions_keywords": ["首屏", "复盘"],
            "scope_is_private": True,
        },
        "description": "用户显式调用资料调研，系统应走 research agent 并返回带引用的回答。",
    },
    {
        "id": "find_similar_project_02",
        "category": "find_similar_project",
        "input": "$research.request 搜索一下竞品有没有做过沉浸式头图的方案",
        "expected_workflow": "request_external_research",
        "expected_checks": {
            "has_source": True,
            "has_evidence_post": True,
            "has_activity_log": True,
            "response_mentions_keywords": ["沉浸式头图", "复盘"],
            "scope_is_private": True,
        },
        "description": "用户通过 $research.request 搜索竞品方案，系统应调用 research agent。",
    },
    {
        "id": "find_similar_project_03",
        "category": "find_similar_project",
        "input": "$research.request 查一下去年双11有没有相似的活动页设计",
        "expected_workflow": "request_external_research",
        "expected_checks": {
            "has_source": True,
            "has_evidence_post": True,
            "has_activity_log": True,
            "response_mentions_keywords": ["首屏", "复盘"],
            "scope_is_private": True,
        },
        "description": "用户查找相似活动页设计经验。",
    },
    {
        "id": "find_similar_project_memory",
        "category": "find_similar_project",
        "input": "$memory.search 团队记忆里有没有关于首屏转化率的经验？",
        "expected_workflow": "ask_memory",
        "expected_checks": {
            "has_source": True,
            "has_evidence_post": True,
            "has_activity_log": True,
            "response_mentions_keywords": ["经验"],
            "scope_is_private": True,
        },
        "description": "用户询问团队记忆中的经验。",
    },
    # --- 场景 2: 生成 Brief ---
    {
        "id": "generate_brief_01",
        "category": "generate_brief",
        "input": "$brief.create 帮我生成这个项目的 Brief",
        "expected_workflow": "generate_brief",
        "expected_checks": {
            "has_source": True,
            "has_evidence_post": True,
            "has_activity_log": True,
            "has_inbox_item": True,
            "response_mentions_keywords": ["Brief", "入口"],
            "scope_is_private": True,
        },
        "description": "用户请求生成 Brief，系统应返回结构化内容并在 Inbox 创建确认项。",
    },
    {
        "id": "generate_brief_02",
        "category": "generate_brief",
        "input": "$brief.create 根据现有资料写一个启动方案文档",
        "expected_workflow": "generate_brief",
        "expected_checks": {
            "has_source": True,
            "has_evidence_post": True,
            "has_activity_log": True,
            "has_inbox_item": True,
            "response_mentions_keywords": ["Brief"],
            "scope_is_private": True,
        },
        "description": "用户请求启动方案。",
    },
    {
        "id": "generate_brief_03",
        "category": "generate_brief",
        "input": "$brief.create 用之前的研究结论生成PRD草稿",
        "expected_workflow": "generate_brief",
        "expected_checks": {
            "has_source": True,
            "has_evidence_post": True,
            "has_activity_log": True,
            "has_inbox_item": True,
            "response_mentions_keywords": ["入口", "Brief"],
            "scope_is_private": True,
        },
        "description": "用户请求生成 PRD。",
    },
    # --- 辅助场景: 记录工作 ---
    {
        "id": "record_work_01",
        "category": "record_work",
        "input": "$note.save 记录一下今天的讨论要点",
        "expected_workflow": "record_private_note",
        "expected_checks": {
            "has_source": False,
            "has_evidence_post": False,
            "has_activity_log": True,
            "response_mentions_keywords": ["私有", "记录"],
            "scope_is_private": True,
        },
        "description": "用户记录工作，不触发外部 Agent。",
    },
    # --- 辅助场景: 数据查询 ---
    {
        "id": "data_query_01",
        "category": "data_query",
        "input": "$data.query 查一下上周首页点击率数据",
        "expected_workflow": "request_data_query",
        "expected_checks": {
            "has_source": True,
            "has_evidence_post": True,
            "has_activity_log": True,
            "response_mentions_keywords": ["数据", "指标"],
            "scope_is_private": True,
        },
        "description": "用户查询数据指标。",
    },
    # --- 辅助场景: 风险审查 ---
    {
        "id": "risk_review_01",
        "category": "risk_review",
        "input": "$risk.review 检查素材授权风险",
        "expected_workflow": "request_risk_review",
        "expected_checks": {
            "has_source": True,
            "has_evidence_post": False,
            "has_activity_log": True,
            "has_inbox_item": True,
            "response_mentions_keywords": ["risk_agent", "收件箱"],
            "scope_is_private": True,
        },
        "description": "用户请求风险审查。",
    },
    # --- 辅助场景: 沉淀记忆 ---
    {
        "id": "create_memory_01",
        "category": "create_memory",
        "input": "$memory.propose 把这个方法论沉淀为团队经验",
        "expected_workflow": "create_memory_candidate",
        "expected_checks": {
            "has_source": True,
            "has_evidence_post": True,
            "has_activity_log": True,
            "has_memory_candidate": True,
            "response_mentions_keywords": ["候选", "记忆"],
            "scope_is_private": True,
        },
        "description": "用户创建记忆候选。",
    },
]
