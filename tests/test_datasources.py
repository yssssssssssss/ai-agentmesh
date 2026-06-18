import pytest

from agentmesh.datasources import (
    DataSourceQuery,
    DataSourceRegistry,
    DataSourceResult,
    ExternalDataSourceConnector,
    LocalMetricsConnector,
)
from agentmesh.models import Source
from agentmesh.seed import PROJECT, USER, WORKSPACE


def test_data_source_query_accepts_generic_parameters() -> None:
    query = DataSourceQuery(
        connector_name="future_bi",
        operation="query",
        parameters={"metric": "conversion_rate", "date": "2026-06-13"},
        workspace_id=WORKSPACE.id,
        project_id=PROJECT.id,
        requested_by=USER.id,
    )

    assert query.connector_name == "future_bi"
    assert query.parameters["metric"] == "conversion_rate"
    assert query.workspace_id == WORKSPACE.id


def test_data_source_result_carries_records_and_source() -> None:
    result = DataSourceResult(
        connector_name="future_bi",
        title="转化率查询结果",
        records=[{"date": "2026-06-13", "conversion_rate": 0.123}],
        source=Source(
            title="future_bi",
            source_type="data_source",
            reference="datasource://future_bi/query",
        ),
        metadata={"provider": "external_project"},
    )

    assert result.records[0]["conversion_rate"] == 0.123
    assert result.source.source_type == "data_source"
    assert result.metadata["provider"] == "external_project"


def test_external_data_source_connector_is_explicit_placeholder() -> None:
    query = DataSourceQuery(
        connector_name="future_bi",
        operation="query",
        parameters={"metric": "conversion_rate"},
        workspace_id=WORKSPACE.id,
        project_id=PROJECT.id,
        requested_by=USER.id,
    )

    with pytest.raises(NotImplementedError, match="External data source"):
        ExternalDataSourceConnector().query(query)


def test_data_source_registry_routes_to_connector() -> None:
    registry = DataSourceRegistry()
    registry.register(LocalMetricsConnector.connector_name, LocalMetricsConnector())

    result = registry.query(
        DataSourceQuery(
            connector_name="local_metrics",
            operation="query",
            parameters={"metric": "ctr"},
            workspace_id=WORKSPACE.id,
            project_id=PROJECT.id,
            requested_by=USER.id,
        )
    )

    assert result.connector_name == "local_metrics"
    assert result.records[0]["metric"] == "ctr"
    assert registry.list_connectors() == ["local_metrics"]


def test_data_source_registry_falls_back_to_next_connector() -> None:
    class FailingConnector:
        def query(self, query: DataSourceQuery) -> DataSourceResult:
            raise RuntimeError("auth_required")

    registry = DataSourceRegistry()
    registry.register("o2_cli", FailingConnector())
    registry.register(LocalMetricsConnector.connector_name, LocalMetricsConnector())

    result = registry.query_first_available(
        connector_names=["o2_cli", "local_metrics"],
        operation="query",
        parameters={"metric": "ctr"},
        workspace_id=WORKSPACE.id,
        project_id=PROJECT.id,
        requested_by=USER.id,
    )

    assert result.connector_name == "local_metrics"
    assert result.metadata["fallback_diagnostics"] == "o2_cli: auth_required"
