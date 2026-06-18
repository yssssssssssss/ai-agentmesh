"""MVP evaluation metrics."""

from __future__ import annotations

from typing import Any

MVP_SUCCESS_TARGETS = {
    "scenario_pass_rate": 0.8,
    "intent_accuracy": 0.8,
    "citation_coverage": 0.75,
    "time_to_useful_answer_p95_ms": 3000,
    "workflow_misroute_rate": 0.2,
    "memory_candidate_creation_rate": 0.8,
    "user_correction_rate": 0.1,
}


def compute_mvp_metrics(results: list[dict[str, Any]], scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    scenarios_by_id = {scenario["id"]: scenario for scenario in scenarios}
    total = len(results)
    passed = sum(1 for result in results if result.get("passed"))
    expected_source = [
        result
        for result in results
        if scenarios_by_id[result["id"]]["expected_checks"].get("has_source") is True
    ]
    useful_durations = sorted(
        int(result["duration_ms"])
        for result in results
        if result.get("passed") and isinstance(result.get("duration_ms"), int)
    )
    memory_expected = [
        result
        for result in results
        if scenarios_by_id[result["id"]]["expected_checks"].get("has_memory_candidate") is True
    ]
    correction_expected = [
        result
        for result in results
        if scenarios_by_id[result["id"]].get("category") == "correction"
    ]
    metrics = {
        "scenario_pass_rate": _ratio(passed, total),
        "intent_accuracy": _ratio(sum(1 for result in results if result["checks"].get("intent_correct")), total),
        "citation_coverage": _ratio(
            sum(1 for result in expected_source if result["checks"].get("has_source") is True),
            len(expected_source),
        ),
        "time_to_useful_answer_p50_ms": _percentile(useful_durations, 0.5),
        "time_to_useful_answer_p95_ms": _percentile(useful_durations, 0.95),
        "workflow_misroute_rate": _ratio(
            sum(1 for result in results if result["checks"].get("intent_correct") is False),
            total,
        ),
        "memory_candidate_creation_rate": _ratio(
            sum(1 for result in memory_expected if result["checks"].get("has_memory_candidate") is True),
            len(memory_expected),
        ),
        "memory_candidate_acceptance_rate": None,
        "user_correction_rate": _ratio(len(correction_expected), total),
    }
    return {
        "targets": MVP_SUCCESS_TARGETS,
        "metrics": metrics,
        "passes_targets": _passes_targets(metrics),
    }


def _passes_targets(metrics: dict[str, Any]) -> dict[str, bool | None]:
    passed: dict[str, bool | None] = {}
    for key, target in MVP_SUCCESS_TARGETS.items():
        value = metrics.get(key)
        if value is None:
            passed[key] = None
            continue
        if key.endswith("_rate") and key in {"workflow_misroute_rate", "user_correction_rate"} or key.endswith("_ms"):
            passed[key] = value <= target
        else:
            passed[key] = value >= target
    return passed


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _percentile(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    index = min(len(values) - 1, max(0, round((len(values) - 1) * percentile)))
    return values[index]
