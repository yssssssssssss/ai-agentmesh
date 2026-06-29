"""Chat routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from agentmesh.agents import PersonalAgent
from agentmesh.chat_skills import list_chat_skills
from agentmesh.models import ChatRequest, ChatResponse, ChatThread, ChatThreadCreateRequest, ItemsResponse, User
from agentmesh.o2 import build_acquisition_agent
from agentmesh.routes.deps import current_user
from agentmesh.seed import PROJECT, WORKSPACE
from agentmesh.store import store

router = APIRouter(prefix="/api/chat", tags=["chat"])

agent = PersonalAgent(store, acquisition_agent=build_acquisition_agent())


@router.post("/threads", response_model=dict[str, ChatThread])
def create_chat_thread(request: ChatThreadCreateRequest, user: User = Depends(current_user)) -> dict[str, ChatThread]:
    thread = store.add_chat_thread(
        ChatThread(
            workspace_id=WORKSPACE.id,
            project_id=PROJECT.id,
            user_id=user.id,
            title=request.title,
        )
    )
    return {"thread": thread}


@router.get("/skills", response_model=ItemsResponse)
def chat_skills(_: User = Depends(current_user)) -> ItemsResponse:
    return ItemsResponse(items=list_chat_skills())


@router.post("/messages", response_model=ChatResponse)
def create_chat_message(request: ChatRequest, user: User = Depends(current_user)) -> ChatResponse:
    return agent.handle_chat(content=request.content, thread_id=request.thread_id, user=user)
