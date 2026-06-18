"""Search, activity, audit, and workspace routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from agentmesh.models import (
    Project,
    ProjectCreateRequest,
    Scope,
    SearchResult,
    User,
    Workspace,
    WorkspaceCreateRequest,
)
from agentmesh.permissions import ensure_admin
from agentmesh.routes.deps import current_user
from agentmesh.seed import PROJECT, WORKSPACE, list_projects, list_workspaces
from agentmesh.store import store

router = APIRouter(prefix="/api", tags=["workspace"])

SEARCH_VISIBILITY_SCOPES: dict[str, set[Scope]] = {
    "personal": {Scope.PRIVATE, Scope.PROJECT, Scope.TEAM_CANDIDATE, Scope.TEAM_ACCEPTED},
    "project": {Scope.PROJECT, Scope.TEAM_CANDIDATE, Scope.TEAM_ACCEPTED},
    "team": {Scope.TEAM_ACCEPTED},
}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/activity/today")
def activity_today(_: User = Depends(current_user)) -> dict[str, object]:
    return {
        "personal": store.list_personal_activity(),
        "external": store.list_external_activity(),
    }


@router.get("/audit")
def audit_events(
    limit: int = Query(default=50, ge=1, le=200),
    action: str | None = Query(default=None, min_length=1, max_length=120),
    target_type: str | None = Query(default=None, min_length=1, max_length=120),
    _: User = Depends(current_user),
) -> dict[str, object]:
    events = list(reversed(store.audit_events))
    if action is not None:
        events = [event for event in events if event.action == action]
    if target_type is not None:
        events = [event for event in events if event.target_type == target_type]
    visible_events = events[:limit]
    counts: dict[str, int] = {}
    for event in events:
        counts[event.action] = counts.get(event.action, 0) + 1
    return {
        "items": visible_events,
        "total": len(events),
        "limit": limit,
        "counts": counts,
    }


@router.get("/search", response_model=dict[str, list[SearchResult]])
def search_items(
    q: str = Query(min_length=1, max_length=200),
    workspace_id: str | None = None,
    project_id: str | None = None,
    visibility: str = "personal",
    user: User = Depends(current_user),
) -> dict[str, list[SearchResult]]:
    allowed_scopes = SEARCH_VISIBILITY_SCOPES.get(visibility)
    if allowed_scopes is None:
        raise HTTPException(status_code=400, detail="Unsupported search visibility")
    return {
        "items": store.search(
            q,
            allowed_scopes,
            workspace_id=workspace_id or WORKSPACE.id,
            project_id=project_id or PROJECT.id,
            user_id=user.id,
        )
    }


@router.get("/workspaces")
def workspaces(_: User = Depends(current_user)) -> dict[str, object]:
    return {"items": list_workspaces(store)}


@router.get("/workspaces/{workspace_id}")
def workspace_detail(workspace_id: str, _: User = Depends(current_user)) -> dict[str, object]:
    workspace = store.get_workspace(workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return {"item": workspace}


@router.post("/workspaces")
def create_workspace(request: WorkspaceCreateRequest, user: User = Depends(current_user)) -> dict[str, object]:
    ensure_admin(user)
    workspace = store.save_workspace(Workspace(name=request.name, description=request.description))
    return {"item": workspace}


@router.get("/projects")
def projects(workspace_id: str | None = None, _: User = Depends(current_user)) -> dict[str, object]:
    return {"items": list_projects(store, workspace_id=workspace_id)}


@router.get("/projects/{project_id}")
def project_detail(project_id: str, _: User = Depends(current_user)) -> dict[str, object]:
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"item": project}


@router.post("/projects")
def create_project(request: ProjectCreateRequest, user: User = Depends(current_user)) -> dict[str, object]:
    ensure_admin(user)
    if store.get_workspace(request.workspace_id) is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    project = store.save_project(Project(workspace_id=request.workspace_id, name=request.name, goal=request.goal))
    return {"item": project}
