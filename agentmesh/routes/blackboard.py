"""Blackboard routes."""

from __future__ import annotations

import asyncio
import contextlib
import os

from fastapi import APIRouter, Depends, HTTPException, Query

from agentmesh.models import (
    AutoBlackboardPostRequest,
    BlackboardHandoffRequest,
    BlackboardPost,
    BlackboardPostCreateRequest,
    BlackboardTaskCard,
    BlackboardTaskCardsResponse,
    CollaborationStage,
    DrainAutoPostsResponse,
    ExecutionLock,
    ExecutionLockAcquireRequest,
    ExecutionLockReleaseRequest,
    ItemResponse,
    ItemsResponse,
    PaginatedResponse,
    Scope,
    StructuredHandoffPacket,
    User,
    UserRole,
    now_utc,
)
from agentmesh.routes.agents import agent_display_name
from agentmesh.routes.deps import create_audit_event, current_user
from agentmesh.seed import AGENTS
from agentmesh.store import store

router = APIRouter(prefix="/api/blackboard", tags=["blackboard"])


def positive_int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except ValueError:
        return default


AUTO_POST_WORKER_ENABLED = os.getenv("AGENTMESH_AUTO_POST_WORKER_ENABLED", "").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
AUTO_POST_WORKER_INTERVAL_SECONDS = positive_int_env("AGENTMESH_AUTO_POST_WORKER_INTERVAL_SECONDS", 30)
auto_post_worker_task: asyncio.Task | None = None
auto_post_worker_state: dict[str, object] = {
    "enabled": AUTO_POST_WORKER_ENABLED,
    "interval_seconds": AUTO_POST_WORKER_INTERVAL_SECONDS,
    "running": False,
    "last_run_at": None,
    "last_posted": 0,
    "last_error": None,
}


def drain_queued_auto_blackboard_posts(actor: str) -> dict[str, object]:
    drained: list[AutoBlackboardPostRequest] = []
    for request in store.auto_blackboard_post_requests:
        if request.status != "reviewed":
            continue
        post = store.add_blackboard_post(
            BlackboardPost(
                task_id=request.task_id,
                post_type=request.post_type,
                actor=request.actor,
                title=request.title,
                content=request.content,
                scope=request.scope,
                permission=request.permission,
                related_post_id=request.related_post_id,
            )
        )
        updated = request.model_copy(
            update={"status": "published", "published_at": now_utc(), "blackboard_post_id": post.id}
        )
        store.save_auto_blackboard_post_request(updated)
        drained.append(updated)

    if drained:
        store.add_audit_event(
            create_audit_event(
                actor,
                "drain_auto_blackboard_posts",
                "blackboard_auto_post_queue",
                "auto_posts",
                {"posted": len(drained)},
            )
        )
    return DrainAutoPostsResponse(posted=len(drained), items=drained)


async def auto_post_worker_loop() -> None:
    while True:
        await asyncio.sleep(AUTO_POST_WORKER_INTERVAL_SECONDS)
        auto_post_worker_state["last_run_at"] = now_utc().isoformat()
        try:
            result = drain_queued_auto_blackboard_posts("auto_post_worker")
            auto_post_worker_state["last_posted"] = result["posted"]
            auto_post_worker_state["last_error"] = None
        except Exception as error:  # pragma: no cover - defensive worker boundary
            auto_post_worker_state["last_error"] = str(error)


async def start_auto_post_worker() -> None:
    global auto_post_worker_task
    if AUTO_POST_WORKER_ENABLED and (auto_post_worker_task is None or auto_post_worker_task.done()):
        auto_post_worker_task = asyncio.create_task(auto_post_worker_loop())
        auto_post_worker_state["running"] = True


async def stop_auto_post_worker() -> None:
    global auto_post_worker_task
    if auto_post_worker_task is not None:
        auto_post_worker_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await auto_post_worker_task
        auto_post_worker_task = None
    auto_post_worker_state["running"] = False


def handoff_summary(packet: StructuredHandoffPacket, next_owner_label: str) -> str:
    blockers = f" 阻塞点：{'；'.join(packet.blockers)}。" if packet.blockers else ""
    requires = f" 需要协作：{'、'.join(packet.requires_input_from)}。" if packet.requires_input_from else ""
    goal = packet.goal
    return (
        f"@{next_owner_label} 接棒：目标是\u201c{goal}\u201d。"
        f"当前结果：{packet.current_result}。"
        f"完成条件：{packet.done_when}。{blockers}{requires}"
    )


@router.get("", response_model=PaginatedResponse)
def blackboard_posts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    task_id: str | None = Query(default=None, min_length=1, max_length=120),
    user: User = Depends(current_user),
) -> PaginatedResponse:
    posts = list(reversed(store.blackboard_posts))
    if task_id is not None:
        posts = [post for post in posts if post.task_id == task_id]
    posts_by_task: dict[str, list[BlackboardPost]] = {}
    for post in store.blackboard_posts:
        posts_by_task.setdefault(post.task_id, []).append(post)
    posts = [post for post in posts if post_visible_to_user(post, posts_by_task.get(post.task_id, []), user)]
    start = (page - 1) * page_size
    end = start + page_size
    return PaginatedResponse(
        items=posts[start:end],
        total=len(posts),
        page=page,
        page_size=page_size,
        has_next=end < len(posts),
    )


@router.get("/task-cards", response_model=BlackboardTaskCardsResponse)
def blackboard_task_cards(user: User = Depends(current_user)) -> BlackboardTaskCardsResponse:
    latest_posts_by_task: dict[str, BlackboardPost] = {}
    posts_by_task: dict[str, list[BlackboardPost]] = {}
    for post in store.blackboard_posts:
        latest_posts_by_task[post.task_id] = post
        posts_by_task.setdefault(post.task_id, []).append(post)
    cards = []
    for task in reversed(store.tasks):
        latest_post = latest_posts_by_task.get(task.id)
        task_posts = posts_by_task.get(task.id, [])
        if not task_visible_to_user(task.thread_id, task_posts, user):
            continue
        locked_post = next(
            (post for post in reversed(task_posts) if post.execution_lock and post.execution_lock.active),
            None,
        )
        active_lock = locked_post.execution_lock if locked_post and locked_post.execution_lock else None
        state_post = locked_post or latest_post
        thread = store.get_chat_thread(task.thread_id)
        cards.append(
            BlackboardTaskCard(
                task=task,
                latest_post=latest_post,
                stage=state_post.collaboration_stage if state_post else task.collaboration_stage,
                owner=state_post.current_owner_label
                if state_post and state_post.current_owner_label
                else task.current_owner_label,
                done_when=state_post.done_when if state_post and state_post.done_when else task.done_when,
                active_lock=active_lock,
                post_count=len(task_posts),
                initiator_user_id=thread.user_id if thread else None,
                initiated_by_current_user=thread is not None and thread.user_id == user.id,
                claimed_by_personal_agent=task_claimed_by_personal_agent(task, task_posts, user),
                upstream_agents=task_upstream_agents(task_posts),
                downstream_agents=task_downstream_agents(task, task_posts, active_lock),
            )
        )
    return BlackboardTaskCardsResponse(items=cards)


def task_claimed_by_personal_agent(task, posts: list[BlackboardPost], user: User) -> bool:
    personal_agent = store.get_agent(user.personal_agent_id)
    personal_agent_ids = {user.personal_agent_id, "personal_agent"}
    if personal_agent is not None:
        personal_agent_ids.add(personal_agent.name)
    values = {task.current_owner_agent_id or "", task.current_owner_label or ""}
    if task.execution_lock:
        values.add(task.execution_lock.owner_agent_id)
        values.add(task.execution_lock.owner_label)
    for post in posts:
        values.update(
            {
                post.current_owner_agent_id or "",
                post.current_owner_label or "",
            }
        )
        if post.execution_lock:
            values.add(post.execution_lock.owner_agent_id)
            values.add(post.execution_lock.owner_label)
    return bool(values & personal_agent_ids)


def task_upstream_agents(posts: list[BlackboardPost]) -> list[str]:
    return unique_non_empty(post.actor for post in posts if post.actor)


def task_downstream_agents(
    task,
    posts: list[BlackboardPost],
    active_lock: ExecutionLock | None,
) -> list[str]:
    values = []
    if active_lock is not None:
        values.append(active_lock.owner_label or active_lock.owner_agent_id)
    values.extend(post.handoff.next_owner_agent_id for post in posts if post.handoff)
    values.extend(post.current_owner_label or post.current_owner_agent_id or "" for post in posts)
    values.append(task.current_owner_label or task.current_owner_agent_id or "")
    return unique_non_empty(values)


def unique_non_empty(values) -> list[str]:
    result: list[str] = []
    for value in values:
        if not value or value in result:
            continue
        result.append(value)
    return result


def task_visible_to_user(thread_id: str, posts: list[BlackboardPost], user: User) -> bool:
    if user.role in {UserRole.TEAM_LEAD, UserRole.ADMIN}:
        return True
    thread = store.get_chat_thread(thread_id)
    if thread and thread.user_id == user.id:
        return True
    if thread and thread.user_id != user.id:
        personal_agent_ids = {user.personal_agent_id}
    else:
        personal_agent_ids = {"personal_agent", user.personal_agent_id}
    for post in posts:
        values = {
            post.actor,
            post.current_owner_agent_id or "",
            post.current_owner_label or "",
            *(post.read_by_agents or []),
        }
        if post.execution_lock:
            values.add(post.execution_lock.owner_agent_id)
            values.add(post.execution_lock.owner_label)
        if values & personal_agent_ids:
            return True
    return False


def post_visible_to_user(post: BlackboardPost, task_posts: list[BlackboardPost], user: User) -> bool:
    if user.role in {UserRole.TEAM_LEAD, UserRole.ADMIN}:
        return True
    if post.scope == Scope.PRIVATE and post.actor not in {user.id, user.personal_agent_id, "personal_agent"}:
        return False
    task = store.get_task(post.task_id)
    if task is not None:
        return task_visible_to_user(task.thread_id, task_posts, user)
    if post.scope == Scope.PROJECT:
        return True
    return (
        post.task_id == f"manual_{user.id}"
        or post.actor in {user.id, user.personal_agent_id, "personal_agent"}
        or user.personal_agent_id in post.read_by_agents
        or "personal_agent" in post.read_by_agents
    )


@router.get("/auto-posts", response_model=ItemsResponse)
def auto_blackboard_posts(_: User = Depends(current_user)) -> ItemsResponse:
    return ItemsResponse(items=list(reversed(store.auto_blackboard_post_requests)))


@router.get("/auto-posts/worker")
def auto_blackboard_worker_status(_: User = Depends(current_user)) -> dict[str, object]:
    return auto_post_worker_state


@router.post("/auto-posts", response_model=ItemResponse)
def enqueue_auto_blackboard_post(
    request: AutoBlackboardPostRequest,
    user: User = Depends(current_user),
) -> ItemResponse:
    if request.actor == "personal_agent":
        reader = store.get_agent(user.personal_agent_id) or next(
            (item for item in AGENTS if item.id == user.personal_agent_id),
            None,
        )
        actor = reader.name if reader else request.actor
        request = request.model_copy(update={"actor": actor})
    return ItemResponse(item=store.enqueue_auto_blackboard_post(request))


@router.post("/auto-posts/drain", response_model=DrainAutoPostsResponse)
def drain_auto_blackboard_posts_endpoint(_: User = Depends(current_user)) -> DrainAutoPostsResponse:
    return drain_queued_auto_blackboard_posts("manual_drain")


@router.post("/auto-posts/{request_id}/review", response_model=ItemResponse)
def review_auto_blackboard_post(request_id: str, user: User = Depends(current_user)) -> ItemResponse:
    request = next((item for item in store.auto_blackboard_post_requests if item.id == request_id), None)
    if request is None:
        raise HTTPException(status_code=404, detail="Auto blackboard post not found")
    if request.status != "queued":
        raise HTTPException(status_code=409, detail="Auto blackboard post is not queued")
    updated = request.model_copy(update={"status": "reviewed", "reviewed_at": now_utc(), "reviewed_by": user.id})
    store.save_auto_blackboard_post_request(updated)
    store.add_audit_event(
        create_audit_event(user.id, "review_auto_blackboard_post", "auto_blackboard_post", request.id, {})
    )
    return ItemResponse(item=updated)


@router.post("/posts", response_model=ItemResponse)
def create_blackboard_post(
    request: BlackboardPostCreateRequest,
    user: User = Depends(current_user),
) -> ItemResponse:
    post = store.add_blackboard_post(
        BlackboardPost(
            task_id=f"manual_{user.id}",
            post_type=request.post_type,
            actor=request.actor,
            title=request.title,
            content=request.content,
            scope=request.scope,
            permission=request.permission,
            related_post_id=request.related_post_id,
            collaboration_stage=request.collaboration_stage,
            done_when=request.done_when,
            handoff=request.handoff,
        )
    )
    return ItemResponse(item=post)


@router.post("/posts/{post_id}/lock", response_model=ItemResponse)
def acquire_blackboard_execution_lock(
    post_id: str,
    request: ExecutionLockAcquireRequest,
    user: User = Depends(current_user),
) -> ItemResponse:
    post = store.get_blackboard_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Blackboard post not found")
    active_lock = post.execution_lock if post.execution_lock and post.execution_lock.active else None
    if active_lock and active_lock.owner_agent_id != request.owner_agent_id:
        raise HTTPException(status_code=409, detail=f"{active_lock.owner_label} already owns execution")

    owner_label = request.owner_label or agent_display_name(request.owner_agent_id)
    lock = ExecutionLock(owner_agent_id=request.owner_agent_id, owner_label=owner_label)
    post.execution_lock = lock
    post.current_owner_agent_id = request.owner_agent_id
    post.current_owner_label = owner_label
    post.collaboration_stage = CollaborationStage.EXECUTION
    store.add_blackboard_post(post)

    task = store.get_task(post.task_id)
    if task is not None:
        task.execution_lock = lock
        task.current_owner_agent_id = request.owner_agent_id
        task.current_owner_label = owner_label
        task.collaboration_stage = CollaborationStage.EXECUTION
        task.updated_at = now_utc()
        store.save_task(task)

    store.add_audit_event(
        create_audit_event(user.id, "acquire_execution_lock", "blackboard_post", post.id, {"owner": owner_label})
    )
    return ItemResponse(item=post)


@router.post("/posts/{post_id}/unlock", response_model=ItemResponse)
def release_blackboard_execution_lock(
    post_id: str,
    request: ExecutionLockReleaseRequest,
    user: User = Depends(current_user),
) -> ItemResponse:
    post = store.get_blackboard_post(post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Blackboard post not found")
    if post.execution_lock and post.execution_lock.active:
        post.execution_lock.released_at = now_utc()
        post.execution_lock.released_reason = request.reason
    post.collaboration_stage = CollaborationStage.REVIEW
    store.add_blackboard_post(post)

    task = store.get_task(post.task_id)
    if task is not None:
        if task.execution_lock and task.execution_lock.active:
            task.execution_lock.released_at = now_utc()
            task.execution_lock.released_reason = request.reason
        task.collaboration_stage = CollaborationStage.REVIEW
        task.updated_at = now_utc()
        store.save_task(task)

    store.add_audit_event(
        create_audit_event(user.id, "release_execution_lock", "blackboard_post", post.id, {"reason": request.reason})
    )
    return ItemResponse(item=post)


@router.post("/posts/{post_id}/handoff", response_model=ItemResponse)
def create_blackboard_handoff(
    post_id: str,
    request: BlackboardHandoffRequest,
    user: User = Depends(current_user),
) -> ItemResponse:
    parent = store.get_blackboard_post(post_id)
    if parent is None:
        raise HTTPException(status_code=404, detail="Blackboard post not found")
    packet = StructuredHandoffPacket(
        goal=request.goal,
        current_result=request.current_result,
        done_when=request.done_when,
        next_owner_agent_id=request.next_owner_agent_id,
        blockers=[item.strip() for item in request.blockers if item.strip()],
        requires_input_from=[item.strip() for item in request.requires_input_from if item.strip()],
    )
    next_owner_label = agent_display_name(packet.next_owner_agent_id)
    post = store.add_blackboard_post(
        BlackboardPost(
            task_id=parent.task_id,
            post_type="handoff",
            actor=parent.current_owner_label or parent.actor,
            title="任务交接",
            content=handoff_summary(packet, next_owner_label),
            scope=parent.scope,
            permission=parent.permission,
            related_post_id=parent.id,
            collaboration_stage=CollaborationStage.DISCUSSION,
            current_owner_agent_id=packet.next_owner_agent_id,
            current_owner_label=next_owner_label,
            done_when=packet.done_when,
            handoff=packet,
        )
    )
    if parent.execution_lock and parent.execution_lock.active:
        parent.execution_lock.released_at = now_utc()
        parent.execution_lock.released_reason = f"handoff:{packet.next_owner_agent_id}"
        parent.collaboration_stage = CollaborationStage.REVIEW
        store.add_blackboard_post(parent)

    task = store.get_task(parent.task_id)
    if task is not None:
        task.current_owner_agent_id = packet.next_owner_agent_id
        task.current_owner_label = next_owner_label
        task.done_when = packet.done_when
        task.collaboration_stage = CollaborationStage.DISCUSSION
        task.execution_lock = None
        task.steps.append("created_structured_handoff")
        task.updated_at = now_utc()
        store.save_task(task)

    store.add_audit_event(
        create_audit_event(user.id, "create_handoff", "blackboard_post", post.id, {"next_owner": next_owner_label})
    )
    return ItemResponse(item=post)


@router.patch("/posts/{post_id}/read", response_model=ItemResponse)
def mark_blackboard_post_read(post_id: str, user: User = Depends(current_user)) -> ItemResponse:
    post = next((item for item in store.blackboard_posts if item.id == post_id), None)
    if post is None:
        raise HTTPException(status_code=404, detail="Blackboard post not found")
    reader = store.get_agent(user.personal_agent_id) or next(
        (item for item in AGENTS if item.id == user.personal_agent_id),
        None,
    )
    reader_id = reader.name if reader else user.personal_agent_id
    if reader_id not in post.read_by_agents:
        post.read_by_agents.append(reader_id)
        store.add_blackboard_post(post)
    return ItemResponse(item=post)


@router.post("/posts/{post_id}/reply", response_model=ItemResponse)
def reply_blackboard_post(
    post_id: str,
    request: BlackboardPostCreateRequest,
    user: User = Depends(current_user),
) -> ItemResponse:
    parent = next((item for item in store.blackboard_posts if item.id == post_id), None)
    if parent is None:
        raise HTTPException(status_code=404, detail="Blackboard post not found")
    reply = request.model_copy(update={"related_post_id": post_id})
    return create_blackboard_post(reply, user)
