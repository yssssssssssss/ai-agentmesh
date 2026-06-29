"""Tests for MVP evaluation metrics."""

from __future__ import annotations

from eval.metrics import compute_mvp_metrics


def test_compute_mvp_metrics_reports_quality_and_latency() -> None:
    scenarios = [
        {"id": "s1", "category": "research", "expected_checks": {"has_source": True}},
        {"id": "s2", "category": "create_memory", "expected_checks": {"has_memory_candidate": True}},
        {"id": "s3", "category": "correction", "expected_checks": {}},
    ]
    results = [
        {
            "id": "s1",
            "passed": True,
            "duration_ms": 100,
            "checks": {"workflow_correct": True, "has_source": True},
        },
        {
            "id": "s2",
            "passed": True,
            "duration_ms": 300,
            "checks": {"workflow_correct": True, "has_memory_candidate": True},
        },
        {
            "id": "s3",
            "passed": False,
            "duration_ms": 900,
            "checks": {"workflow_correct": False},
        },
    ]

    payload = compute_mvp_metrics(results, scenarios)

    assert payload["metrics"]["scenario_pass_rate"] == 0.6667
    assert payload["metrics"]["workflow_route_accuracy"] == 0.6667
    assert payload["metrics"]["citation_coverage"] == 1.0
    assert payload["metrics"]["time_to_useful_answer_p95_ms"] == 300
    assert payload["metrics"]["workflow_misroute_rate"] == 0.3333
    assert payload["metrics"]["memory_candidate_creation_rate"] == 1.0
    assert payload["metrics"]["memory_candidate_acceptance_rate"] is None
    assert payload["metrics"]["user_correction_rate"] == 0.3333
