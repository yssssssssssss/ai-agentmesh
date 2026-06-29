"""评估脚本：对每个场景运行 chat 请求，检查输出质量。

用法:
    .venv/bin/python eval/run_eval.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# 确保项目在 path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

EvalContext = dict[str, Any]


def configure_eval_database() -> tempfile.TemporaryDirectory[str]:
    db_dir = tempfile.TemporaryDirectory(prefix="agentmesh-eval-")
    os.environ["AGENTMESH_DB_PATH"] = str(Path(db_dir.name) / "agentmesh-eval.sqlite3")
    return db_dir


def load_eval_context() -> EvalContext:
    from fastapi.testclient import TestClient

    from agentmesh.app import app
    from agentmesh.model_registry import ensure_model_seed_data
    from agentmesh.risk import ensure_risk_policy_seed_data
    from agentmesh.routes.blackboard import stop_auto_post_worker
    from agentmesh.seed import USER, ensure_initial_blackboard_data, ensure_seed_data
    from agentmesh.store import store
    from agentmesh.tools import ensure_tool_seed_data
    from eval.dataset import SCENARIOS

    return {
        "TestClient": TestClient,
        "app": app,
        "store": store,
        "user_id": USER.id,
        "scenarios": SCENARIOS,
        "ensure_seed_data": ensure_seed_data,
        "ensure_initial_blackboard_data": ensure_initial_blackboard_data,
        "ensure_tool_seed_data": ensure_tool_seed_data,
        "ensure_model_seed_data": ensure_model_seed_data,
        "ensure_risk_policy_seed_data": ensure_risk_policy_seed_data,
        "stop_auto_post_worker": stop_auto_post_worker,
    }


def reset_eval_store(context: EvalContext) -> None:
    """Reset only the temporary eval database, then restore required seed records."""
    store = context["store"]
    store.reset()
    context["ensure_seed_data"](store)
    context["ensure_initial_blackboard_data"](store)
    context["ensure_tool_seed_data"](store, granted_by="eval")
    context["ensure_model_seed_data"](store)
    context["ensure_risk_policy_seed_data"](store)


def login_client(context: EvalContext):
    client = context["TestClient"](context["app"])
    response = client.post("/api/auth/login", json={"user_id": context["user_id"], "password": "designer123"})
    assert response.status_code == 200, f"Login failed: {response.json()}"
    return client


def run_scenario(context: EvalContext, scenario: dict[str, Any]) -> dict[str, Any]:
    """运行单个场景并返回评估结果。"""
    reset_eval_store(context)
    client = login_client(context)

    # 发送 chat
    started_at = time.perf_counter()
    chat_response = client.post("/api/chat/messages", json={"content": scenario["input"]})
    duration_ms = int((time.perf_counter() - started_at) * 1000)
    if chat_response.status_code != 200:
        return {
            "id": scenario["id"],
            "passed": False,
            "error": f"Chat API returned {chat_response.status_code}: {chat_response.text}",
            "checks": {},
            "duration_ms": duration_ms,
        }

    data = chat_response.json()
    checks = scenario["expected_checks"]
    results = {}

    # 检查显式 $ skill 是否路由到预期工作流。
    actual_workflow = data.get("task", {}).get("intent") or data.get("workflow_trace", {}).get("intent")
    results["workflow_correct"] = actual_workflow == scenario["expected_workflow"]

    # 检查是否有 source
    if "has_source" in checks:
        evidence = data.get("evidence_post")
        risk = data.get("risk_post")
        sources = []
        if evidence:
            sources.extend(evidence.get("sources", []))
        if risk:
            sources.extend(risk.get("sources", []))
        results["has_source"] = (len(sources) > 0) == checks["has_source"]

    # 检查是否有 evidence post
    if "has_evidence_post" in checks:
        evidence = data.get("evidence_post")
        results["has_evidence_post"] = (evidence is not None) == checks["has_evidence_post"]

    # 检查是否有 activity log
    if "has_activity_log" in checks:
        activity = data.get("activity_logs", [])
        results["has_activity_log"] = (len(activity) > 0) == checks["has_activity_log"]

    # 检查是否有 inbox item
    if "has_inbox_item" in checks:
        inbox = data.get("inbox_items", [])
        results["has_inbox_item"] = (len(inbox) > 0) == checks["has_inbox_item"]

    # 检查是否有 memory candidate
    if "has_memory_candidate" in checks:
        memory = data.get("memory_items", [])
        results["has_memory_candidate"] = (len(memory) > 0) == checks["has_memory_candidate"]

    # 检查回答中是否包含关键词
    assistant_content = data.get("assistant_message", {}).get("content", "")
    if "response_mentions_keywords" in checks:
        keywords = checks["response_mentions_keywords"]
        matched = [kw for kw in keywords if kw in assistant_content]
        results["keyword_coverage"] = f"{len(matched)}/{len(keywords)}"
        results["keywords_found"] = matched
        results["keywords_missing"] = [kw for kw in keywords if kw not in assistant_content]

    # 检查 scope 是否私有
    if "scope_is_private" in checks:
        message = data.get("assistant_message", {})
        results["scope_is_private"] = message.get("scope") == "private"

    passed = all(
        v is True or (isinstance(v, str) and "/" in v and v.split("/")[0] == v.split("/")[1])
        for k, v in results.items()
        if k not in ("keywords_found", "keywords_missing", "keyword_coverage")
    )
    # keyword_coverage 单独检查：至少命中 1 个
    if "keyword_coverage" in results:
        coverage = results["keyword_coverage"]
        found_count = int(coverage.split("/")[0])
        passed = passed and found_count > 0

    return {
        "id": scenario["id"],
        "category": scenario["category"],
        "passed": passed,
        "checks": results,
        "response_preview": assistant_content[:200],
        "duration_ms": duration_ms,
    }


def main():
    db_dir = configure_eval_database()
    context = load_eval_context()
    try:
        print("=" * 70)
        print("AgentMesh 评估运行")
        print("=" * 70)
        print()

        total = len(context["scenarios"])
        passed = 0
        failed = 0
        results_by_category: dict[str, list[dict]] = {}

        all_results = []
        for scenario in context["scenarios"]:
            result = run_scenario(context, scenario)
            all_results.append(result)
            results_by_category.setdefault(scenario["category"], []).append(result)

            status = "PASS" if result["passed"] else "FAIL"
            if result["passed"]:
                passed += 1
            else:
                failed += 1
            print(f"  [{status}] {result['id']}")
            if not result["passed"]:
                for check_name, check_value in result["checks"].items():
                    if check_value is not True and not (isinstance(check_value, str) and "/" in check_value):
                        print(f"         {check_name}: {check_value}")

        print()
        print("-" * 70)
        print(f"总计: {total} | 通过: {passed} | 失败: {failed} | 通过率: {passed/total*100:.1f}%")
        print()

        # 按类别统计
        print("按类别统计:")
        for category, items in results_by_category.items():
            cat_passed = sum(1 for item in items if item["passed"])
            print(f"  {category}: {cat_passed}/{len(items)}")

        print()

        # 关键指标
        scenarios_by_id = {scenario["id"]: scenario for scenario in context["scenarios"]}
        total_sources = sum(
            1
            for result in all_results
            if scenarios_by_id[result["id"]]["expected_checks"].get("has_source") is True
            and result["checks"].get("has_source") is True
        )
        total_with_source_expected = sum(
            1 for s in context["scenarios"] if s["expected_checks"].get("has_source") is True
        )
        print("关键指标:")
        print(f"  引用覆盖率: {total_sources}/{total_with_source_expected}")
        print(f"  工作流路由准确率: {sum(1 for r in all_results if r['checks'].get('workflow_correct'))}/{total}")
        from eval.metrics import compute_mvp_metrics

        mvp_metrics = compute_mvp_metrics(all_results, context["scenarios"])
        for key, value in mvp_metrics["metrics"].items():
            print(f"  {key}: {value}")

        # 输出 JSON
        output_path = Path(__file__).parent / "results.json"
        output = {
            "results": all_results,
            "mvp_metrics": mvp_metrics,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n详细结果已保存到: {output_path}")
        print(f"评估使用临时数据库: {context['store'].db_path}")
    finally:
        asyncio.run(context["stop_auto_post_worker"]())
        db_dir.cleanup()


if __name__ == "__main__":
    main()
