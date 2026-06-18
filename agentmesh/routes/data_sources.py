"""Data source routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from agentmesh.datasources import DataSourceQuery, default_data_source_registry
from agentmesh.models import BlackboardPost, DataSourceQueryRequest, Scope, User
from agentmesh.o2 import O2CommandError, maybe_register_o2_data_connector
from agentmesh.routes.deps import current_user
from agentmesh.seed import PROJECT, WORKSPACE
from agentmesh.store import store

router = APIRouter(prefix="/api", tags=["data_sources"])

data_source_registry = default_data_source_registry()
maybe_register_o2_data_connector(data_source_registry)


@router.get("/data-sources")
def data_sources(_: User = Depends(current_user)) -> dict[str, object]:
    return {"items": data_source_registry.list_connectors()}


@router.post("/data-agent/query")
def query_data_agent(request: DataSourceQueryRequest, user: User = Depends(current_user)) -> dict[str, object]:
    try:
        result = data_source_registry.query(
            DataSourceQuery(
                connector_name=request.connector_name,
                operation=request.operation,
                parameters=request.parameters,
                workspace_id=WORKSPACE.id,
                project_id=PROJECT.id,
                requested_by=user.id,
            )
        )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except O2CommandError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    store.add_source(result.source)
    post = store.add_blackboard_post(
        BlackboardPost(
            task_id=f"data_{user.id}",
            post_type="evidence",
            actor="data_agent",
            title=result.title,
            content=str(result.records),
            scope=Scope.PROJECT,
            permission="project_visible",
            sources=[result.source],
            read_by_agents=["personal_agent"],
        )
    )
    return {"result": result, "post": post}
