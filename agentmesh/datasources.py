from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel, Field

from agentmesh.models import Source


class DataSourceQuery(BaseModel):
    connector_name: str = Field(min_length=1, max_length=120)
    operation: str = Field(min_length=1, max_length=80)
    parameters: dict[str, Any] = Field(default_factory=dict)
    workspace_id: str
    project_id: str
    requested_by: str


class DataSourceResult(BaseModel):
    connector_name: str
    title: str = Field(min_length=1, max_length=200)
    records: list[dict[str, Any]] = Field(default_factory=list)
    source: Source
    metadata: dict[str, str] = Field(default_factory=dict)


class DataSourceConnector(Protocol):
    def query(self, query: DataSourceQuery) -> DataSourceResult: ...


class ExternalDataSourceConnector:
    def query(self, query: DataSourceQuery) -> DataSourceResult:
        raise NotImplementedError("External data source integration is provided by another project.")


class LocalMetricsConnector:
    connector_name = "local_metrics"

    def query(self, query: DataSourceQuery) -> DataSourceResult:
        metric = str(query.parameters.get("metric") or "conversion_rate")
        return DataSourceResult(
            connector_name=self.connector_name,
            title=f"{metric} 查询结果",
            records=[{"metric": metric, "value": 0.123, "source": "local_sample"}],
            source=Source(
                title="local_metrics",
                source_type="data_source",
                reference=f"datasource://local_metrics/{query.operation}",
            ),
            metadata={"provider": "local"},
        )


class DataSourceRegistry:
    def __init__(self):
        self._connectors: dict[str, DataSourceConnector] = {}

    def register(self, name: str, connector: DataSourceConnector) -> None:
        self._connectors[name] = connector

    def query(self, query: DataSourceQuery) -> DataSourceResult:
        connector = self._connectors.get(query.connector_name)
        if connector is None:
            raise KeyError(f"Unknown data source connector: {query.connector_name}")
        return connector.query(query)

    def query_first_available(
        self,
        connector_names: list[str],
        operation: str,
        parameters: dict[str, Any],
        workspace_id: str,
        project_id: str,
        requested_by: str,
    ) -> DataSourceResult:
        errors: list[str] = []
        for connector_name in connector_names:
            if connector_name not in self._connectors:
                continue
            try:
                result = self.query(
                    DataSourceQuery(
                        connector_name=connector_name,
                        operation=operation,
                        parameters=parameters,
                        workspace_id=workspace_id,
                        project_id=project_id,
                        requested_by=requested_by,
                    )
                )
            except Exception as error:
                errors.append(f"{connector_name}: {str(error) or error.__class__.__name__}")
                continue
            if result.records:
                if errors:
                    result.metadata["fallback_diagnostics"] = " | ".join(errors)[:500]
                return result
            errors.append(f"{connector_name}: empty result")
        raise RuntimeError("No data source connector returned records: " + " | ".join(errors))

    def list_connectors(self) -> list[str]:
        return sorted(self._connectors)


def default_data_source_registry() -> DataSourceRegistry:
    registry = DataSourceRegistry()
    registry.register(LocalMetricsConnector.connector_name, LocalMetricsConnector())
    return registry
