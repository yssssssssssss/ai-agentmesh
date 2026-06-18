from __future__ import annotations

from dataclasses import dataclass, field

from agentmesh.acquisition import (
    AcquisitionAgent,
    AcquisitionRequest,
    AcquisitionResult,
    MockAcquisitionAgent,
)
from agentmesh.intent import classify_intent_hybrid
from agentmesh.llm import LLMClient
from agentmesh.model_registry import resolve_agent_model_id
from agentmesh.models import (
    ActivityLog,
    AuditEvent,
    BlackboardPost,
    BlackboardPostType,
    ChatMessage,
    ChatResponse,
    ChatRole,
    ChatThread,
    ChatWorkflowTrace,
    CollaborationStage,
    InboxItem,
    Intent,
    MemoryItem,
    MemoryLayer,
    Scope,
    Source,
    Task,
    TaskStatus,
    User,
    UserMemoryItem,
    new_id,
    now_utc,
)
from agentmesh.risk import RiskDecision, assess_external_content, assess_tool_request
from agentmesh.seed import PROJECT, USER, WORKSPACE
from agentmesh.service_agents import MockDataAgent, RiskAgent
from agentmesh.store import SQLiteStore
from agentmesh.synthesis import (
    ChatLLM,
    assistant_sources,
    build_llm_prompt,
    evidence_answer,
    source_titles,
    synthesize_with_llm,
)


@dataclass
class _ChatTurnState:
    request_post: BlackboardPost | None = None
    evidence_post: BlackboardPost | None = None
    synthesis_evidence_post: BlackboardPost | None = None
    risk_post: BlackboardPost | None = None
    activity_logs: list[ActivityLog] = field(default_factory=list)
    inbox_items: list[InboxItem] = field(default_factory=list)
    memory_items: list[MemoryItem] = field(default_factory=list)
    user_memory_items: list[UserMemoryItem] = field(default_factory=list)
    pending_tool_approval: bool = False


class PersonalAgent:
    actor = "personal_agent"
    MAX_HISTORY_MESSAGES = 10
    MAX_HISTORY_CHARS = 4000

    def __init__(
        self,
        repository: SQLiteStore,
        llm_client: ChatLLM | None = None,
        acquisition_agent: AcquisitionAgent | None = None,
        data_agent: MockDataAgent | None = None,
    ):
        self.repository = repository
        self.acquisition_agent = acquisition_agent or MockAcquisitionAgent()
        self.data_agent = data_agent or MockDataAgent()
        self.risk_agent = RiskAgent(repository)
        self.llm_client = llm_client

    def handle_chat(self, content: str, thread_id: str | None = None, user: User = USER) -> ChatResponse:
        actual_thread_id = thread_id or new_id("thread")

        # 读取对话历史用于上下文
        history = self._get_thread_history(actual_thread_id)

        # 先用模型判断是否需要进入工作流；规则只作为模型不可用时的兜底。
        llm_for_classification = self.llm_client or LLMClient.from_model_id(
            resolve_agent_model_id(self.repository, user)
        )
        classification = classify_intent_hybrid(content, llm_for_classification)
        intent = classification.intent
        workflow_trace = self._workflow_trace(classification, llm_for_classification, intent.value, persisted=True)

        if intent == Intent.GENERAL_CHAT:
            assistant_content = self._general_chat_answer(content, user, history, llm_for_classification)
            return ChatResponse(
                thread_id=actual_thread_id,
                user_message=ChatMessage(
                    thread_id=actual_thread_id,
                    role=ChatRole.USER,
                    content=content,
                    scope=Scope.PRIVATE,
                ),
                assistant_message=ChatMessage(
                    thread_id=actual_thread_id,
                    role=ChatRole.ASSISTANT,
                    content=assistant_content,
                    scope=Scope.PRIVATE,
                ),
                task=None,
                activity_logs=[],
                inbox_items=[],
                memory_items=[],
                user_memory_items=[],
                workflow_trace=self._workflow_trace(
                    classification,
                    llm_for_classification,
                    "general_chat",
                    persisted=False,
                ),
            )

        self._ensure_thread(actual_thread_id, content, user)

        user_message = self.repository.add_chat_message(
            ChatMessage(
                thread_id=actual_thread_id,
                role=ChatRole.USER,
                content=content,
                scope=Scope.PRIVATE,
            )
        )

        task = self.repository.add_task(
            Task(
                thread_id=actual_thread_id,
                intent=intent,
                status=TaskStatus.RUNNING,
                title=self._task_title(intent),
                steps=["received_user_message", "classified_intent"],
            )
        )
        self._audit(
            "create_task",
            "task",
            task.id,
            {"intent": intent, "intent_source": classification.source, "confidence": classification.confidence},
        )

        state = _ChatTurnState()

        try:
            if intent == Intent.REQUEST_DATA_QUERY:
                self._handle_data_query(task, content, user, state)

            if intent in {
                Intent.ASK_MEMORY,
                Intent.GENERATE_BRIEF,
                Intent.REQUEST_EXTERNAL_RESEARCH,
                Intent.CREATE_MEMORY_CANDIDATE,
            }:
                self._handle_acquisition_intent(task, content, intent, user, state)

            if intent == Intent.REQUEST_RISK_REVIEW:
                self._handle_risk_review(task, content, state)
        except Exception as error:
            self._mark_task_failed(task, error)
            raise

        assistant_content = self._assistant_content_for_turn(intent, content, state, user)

        if not state.pending_tool_approval and intent != Intent.ASK_SYSTEM_INFO:
            assistant_content = self._synthesize_with_llm(
                fallback_content=assistant_content,
                user_content=content,
                intent=intent,
                evidence_post=state.synthesis_evidence_post,
                risk_post=state.risk_post,
                inbox_items=state.inbox_items,
                memory_items=state.memory_items,
                user=user,
                history=history,
            )

        state.activity_logs.append(
            self._activity(
                title="处理了一条用户请求",
                summary=f"意图识别为 {intent.value}，默认保留在个人上下文。",
                category="personal",
                scope=Scope.PRIVATE,
            )
        )

        if task.status != TaskStatus.WAITING_EXTERNAL_AGENT:
            task.status = TaskStatus.COMPLETED
            task.collaboration_stage = CollaborationStage.COMPLETED
        else:
            task.collaboration_stage = CollaborationStage.BLOCKED
        task.updated_at = now_utc()
        task.steps.append("returned_chat_response")
        self.repository.save_task(task)

        assistant_message = self.repository.add_chat_message(
            ChatMessage(
                thread_id=actual_thread_id,
                role=ChatRole.ASSISTANT,
                content=assistant_content,
                scope=Scope.PRIVATE,
                sources=self._assistant_sources(state.evidence_post, state.risk_post),
            )
        )
        self._audit("return_chat_response", "chat_message", assistant_message.id, {"task_id": task.id})
        memory_item = self._record_short_term_memory(task, intent, content, assistant_content, state, user)
        if memory_item is not None:
            state.user_memory_items.append(memory_item)

        return ChatResponse(
            thread_id=actual_thread_id,
            user_message=user_message,
            assistant_message=assistant_message,
            task=task,
            request_post=state.request_post,
            evidence_post=state.evidence_post,
            risk_post=state.risk_post,
            activity_logs=state.activity_logs,
            inbox_items=state.inbox_items,
            memory_items=state.memory_items,
            user_memory_items=state.user_memory_items,
            workflow_trace=workflow_trace,
        )

    def _mark_task_failed(self, task: Task, error: Exception) -> None:
        step = f"failed:{type(error).__name__}"
        if step not in task.steps:
            task.steps.append(step)
        task.status = TaskStatus.FAILED
        task.collaboration_stage = CollaborationStage.BLOCKED
        task.updated_at = now_utc()
        self.repository.save_task(task)
        self._audit("fail_task", "task", task.id, {"error": type(error).__name__})

    def _handle_data_query(self, task: Task, content: str, user: User, state: _ChatTurnState) -> None:
        state.request_post = self._create_request_post(
            task,
            content,
            title="查询项目指标数据",
            read_by_agents=["data_agent"],
            current_owner_agent_id="data_agent",
            current_owner_label="data_agent",
            done_when="data_agent 返回可引用指标数据",
        )
        task.steps.append("created_blackboard_request")
        state.evidence_post = self.data_agent.query(task, state.request_post, content, user)
        state.synthesis_evidence_post = state.evidence_post
        self._persist_sources(state.evidence_post.sources)
        self.repository.add_blackboard_post(state.evidence_post)
        task.steps.append("received_data_agent_evidence")
        state.activity_logs.append(
            self._activity(
                title="请求 data_agent 查询指标",
                summary="data_agent 已返回本地指标数据并写入 BBS。",
                category="external_agent",
                scope=Scope.PROJECT,
            )
        )

    def _handle_acquisition_intent(
        self,
        task: Task,
        content: str,
        intent: Intent,
        user: User,
        state: _ChatTurnState,
    ) -> None:
        state.request_post = self._create_request_post(task, content)
        task.steps.append("created_blackboard_request")
        tool_risk = assess_tool_request(content)
        if tool_risk.decision == RiskDecision.NEEDS_REVIEW:
            state.pending_tool_approval = True
            task.status = TaskStatus.WAITING_EXTERNAL_AGENT
            task.steps.append("requested_tool_call_approval")
            state.inbox_items.append(
                self._inbox(
                    title="审批高风险工具调用",
                    summary="该请求涉及批量抓取、批量下载、内网访问或自动写入等高风险动作，需要审批后再执行。",
                    item_type="tool_call_approval",
                    scope=Scope.PROJECT,
                    user_id=user.id,
                )
            )
            return

        acquisition_request = AcquisitionRequest(
            query=content,
            intent=intent,
            workspace_id=WORKSPACE.id,
            project_id=PROJECT.id,
            user_id=user.id,
            task_id=task.id,
            request_post_id=state.request_post.id,
        )
        acquisition_result = self._document_acquisition_result(acquisition_request)
        if acquisition_result is None:
            acquisition_result = self.acquisition_agent.acquire(acquisition_request)
        state.evidence_post = self._create_evidence_post(task, state.request_post, acquisition_result)
        content_risk = assess_external_content(acquisition_result.content)
        if content_risk.decision == RiskDecision.NEEDS_REVIEW:
            state.evidence_post.status = "needs_review"
            task.steps.append("quarantined_acquisition_evidence")
            state.inbox_items.append(
                self._inbox(
                    title="审核可疑外部资料",
                    summary="外部资料包含疑似提示词注入内容，已隔离，暂不用于回答合成。",
                    item_type="prompt_injection_review",
                    scope=Scope.PROJECT,
                    user_id=user.id,
                )
            )
        else:
            state.synthesis_evidence_post = state.evidence_post
            task.steps.append("received_acquisition_evidence")
        self._persist_sources(state.evidence_post.sources)
        self.repository.add_blackboard_post(state.evidence_post)
        state.activity_logs.append(
            self._activity(
                title="请求外接 Agent 补充资料",
                summary=f"{state.evidence_post.actor} 已返回资料证据和来源。",
                category="external_agent",
                scope=Scope.PROJECT,
            )
        )

    def _document_acquisition_result(self, request: AcquisitionRequest) -> AcquisitionResult | None:
        document_results = self._document_search_results(request)
        if not document_results:
            return None
        selected = document_results[:3]
        content = "\n".join(f"{item.title}：{item.summary}" for item in selected)
        sources: list[Source] = []
        for item in selected:
            sources.extend(item.sources)
        return AcquisitionResult(
            actor="document_agent",
            title="已检索上传文档",
            content=content,
            sources=sources,
            metadata={"provider": "documents", "request_post_id": request.request_post_id},
        )

    def _document_search_results(self, request: AcquisitionRequest):
        matches = self.repository.search(
            request.query,
            {Scope.PRIVATE},
            workspace_id=request.workspace_id,
            project_id=request.project_id,
            user_id=request.user_id,
        )
        document_results = [item for item in matches if item.result_type in {"document", "user_memory_item"}]
        if document_results:
            return document_results

        query_tokens = [token.lower() for token in request.query.replace("，", " ").replace("。", " ").split()]
        if not query_tokens:
            return []
        fallback_results = []
        for document in self.repository.documents:
            if document.uploaded_by != request.user_id:
                continue
            if document.workspace_id != request.workspace_id or document.project_id != request.project_id:
                continue
            haystack = f"{document.title} {document.file_name} {document.text}".lower()
            if any(token and token in haystack for token in query_tokens):
                fallback_results.append(
                    type(
                        "DocumentSearchHit",
                        (),
                        {
                            "result_type": "document",
                            "title": document.title,
                            "summary": document.text[:500],
                            "sources": [document.source],
                        },
                    )()
                )
        return fallback_results

    def _handle_risk_review(self, task: Task, content: str, state: _ChatTurnState) -> None:
        state.request_post = self._create_request_post(
            task,
            content,
            title="检查素材和来源风险",
            read_by_agents=["risk_agent"],
            current_owner_agent_id="risk_agent",
            current_owner_label="risk_agent",
            done_when="risk_agent 返回策略规则评审结论",
        )
        state.risk_post = self.risk_agent.review(task, state.request_post)
        self._persist_sources(state.risk_post.sources)
        self.repository.add_blackboard_post(state.risk_post)
        task.steps.extend(["created_blackboard_request", "received_policy_risk_review"])
        state.activity_logs.append(
            self._activity(
                title="请求 risk_agent 检查风险",
                summary="risk_agent 已返回策略规则评审结论，并放入收件箱。",
                category="external_agent",
                scope=Scope.PROJECT,
            )
        )

    def _assistant_content_for_turn(self, intent: Intent, content: str, state: _ChatTurnState, user: User) -> str:
        if intent == Intent.ASK_SYSTEM_INFO:
            return self._system_info_answer(user)
        if intent == Intent.RECORD_PRIVATE_NOTE:
            return "已记录为你的私有工作上下文，暂不共享到项目或团队记忆。"
        if intent == Intent.GENERATE_BRIEF:
            state.inbox_items.append(
                self._inbox(
                    title="确认 Brief 中的设计原则",
                    summary="该原则会影响项目 Brief 和后续团队记忆，建议在收件箱确认。",
                    item_type="decision_review",
                    scope=Scope.PROJECT,
                    user_id=user.id,
                )
            )
            return (
                "我可以基于现有项目经验生成 Brief 草稿。当前最重要的可引用结论是："
                "去年沉浸式头图降低了核心入口点击，建议今年优先保证入口效率。"
            )
        if intent == Intent.REQUEST_RISK_REVIEW:
            state.inbox_items.append(
                self._inbox(
                    title="确认外部素材授权范围",
                    summary="正式稿使用前需要确认授权范围、使用期限和二次加工权限。",
                    item_type="risk_review",
                    scope=Scope.PROJECT,
                    user_id=user.id,
                )
            )
            return "risk_agent 已返回策略规则评审结论，我已放入收件箱等待你处理。"
        if intent == Intent.CREATE_MEMORY_CANDIDATE:
            state.memory_items.append(
                self._memory(
                    title="大促会场首屏结构偏好",
                    summary="转化目标优先时，首屏应优先保证核心入口密度。",
                    memory_type="method",
                    sources=state.synthesis_evidence_post.sources if state.synthesis_evidence_post else [],
                )
            )
            return "我已提取一条候选团队记忆，并放入记忆库审核，不会自动写入团队记忆。"
        if state.pending_tool_approval:
            return "这个请求涉及高风险工具调用，需要你先在收件箱审批，我不会在审批前执行。"
        if state.evidence_post and state.evidence_post.status == "needs_review":
            return "外部资料存在安全风险，已放入收件箱等待审核。"
        return self._evidence_answer(state.synthesis_evidence_post, intent, content)

    def _system_info_answer(self, user: User) -> str:
        model_id = resolve_agent_model_id(self.repository, user)
        model = self.repository.get_model_definition(model_id)
        if model and model.configured:
            return f"当前个人 Agent 配置的模型是 {model.label}（{model.model_name}）。"
        return "当前没有配置外部大模型，正在使用本地兜底模式；可在 Agent 页面选择并保存模型。"

    def _general_chat_answer(
        self,
        content: str,
        user: User,
        history: list[ChatMessage],
        llm_client: ChatLLM | None,
    ) -> str:
        client = llm_client or LLMClient.from_model_id(resolve_agent_model_id(self.repository, user))
        if client is None:
            return "我可以先帮你澄清问题；如果你需要查资料、查数据、生成 Brief 或沉淀记忆，我会再进入对应工作流。"
        history_text = "\n".join(
            f"{'用户' if message.role == ChatRole.USER else '助理'}：{message.content}" for message in history[-6:]
        )
        prompt = f"历史上下文：\n{history_text or '无'}\n\n用户输入：{content}\n请直接自然回复，不要创建任务或编造数据。"
        try:
            generated = client.complete(
                system_prompt=(
                    "你是 AgentMesh 作战室里的中文对话助手。"
                    "当前输入未形成明确的项目工作流意图，只做普通对话、解释或澄清。"
                    "不要声称已经调用 Agent，不要写入记忆，不要创建任务。"
                ),
                user_prompt=prompt,
            )
        except Exception:
            return "我可以继续和你澄清需求；当问题明确需要查资料、查数据、生成 Brief 或沉淀记忆时，我会进入对应 Agent 工作流。"
        return generated.strip() or "我在，可以继续说。"

    def _create_request_post(
        self,
        task: Task,
        content: str,
        title: str = "补充团队历史经验",
        read_by_agents: list[str] | None = None,
        current_owner_agent_id: str = "mock_research_agent",
        current_owner_label: str = "research_agent",
        done_when: str = "服务 Agent 返回可引用证据或风险结论",
    ) -> BlackboardPost:
        post = BlackboardPost(
            task_id=task.id,
            post_type=BlackboardPostType.REQUEST,
            actor=self.actor,
            title=title,
            content=content,
            scope=Scope.PROJECT,
            permission="project_visible",
            read_by_agents=read_by_agents or ["mock_research_agent", "risk_agent"],
            collaboration_stage=CollaborationStage.DISCUSSION,
            current_owner_agent_id=current_owner_agent_id,
            current_owner_label=current_owner_label,
            done_when=done_when,
        )
        self.repository.add_blackboard_post(post)
        self._audit("create_blackboard_request", "blackboard_post", post.id, {"task_id": task.id})
        return post

    @staticmethod
    def _create_evidence_post(
        task: Task,
        request_post: BlackboardPost,
        result: AcquisitionResult,
    ) -> BlackboardPost:
        return BlackboardPost(
            task_id=task.id,
            post_type=BlackboardPostType.EVIDENCE,
            actor=result.actor,
            title=result.title,
            content=result.content,
            scope=Scope.PROJECT,
            permission=result.permission,
            sources=result.sources,
            read_by_agents=[request_post.actor],
            related_post_id=request_post.id,
            collaboration_stage=CollaborationStage.REVIEW,
            current_owner_agent_id=result.actor,
            current_owner_label=result.actor,
            done_when="个人 Agent 完成证据合成并返回用户",
        )

    def _ensure_thread(self, thread_id: str, content: str, user: User) -> ChatThread:
        existing_thread = self.repository.get_chat_thread(thread_id)
        if existing_thread is not None:
            return existing_thread
        title = content.strip()[:60] or "新的团队大脑对话"
        return self.repository.add_chat_thread(
            ChatThread(
                id=thread_id,
                workspace_id=WORKSPACE.id,
                project_id=PROJECT.id,
                user_id=user.id,
                title=title,
            )
        )

    def _get_thread_history(self, thread_id: str) -> list[ChatMessage]:
        """获取当前 thread 的最近 N 条消息作为对话上下文。

        控制 token budget：最多 MAX_HISTORY_MESSAGES 条，总字符数不超过 MAX_HISTORY_CHARS。
        """
        messages = self.repository.list_thread_messages(thread_id)
        # 取最近 N 条（不含当前正在处理的，因为还没存入）
        recent = messages[-self.MAX_HISTORY_MESSAGES:]
        # 按字符 budget 截断
        result = []
        total_chars = 0
        for msg in reversed(recent):
            msg_chars = len(msg.content)
            if total_chars + msg_chars > self.MAX_HISTORY_CHARS:
                break
            result.append(msg)
            total_chars += msg_chars
        result.reverse()
        return result

    def _activity(self, title: str, summary: str, category: str, scope: Scope) -> ActivityLog:
        log = ActivityLog(
            actor=self.actor,
            title=title,
            summary=summary,
            category=category,
            scope=scope,
            workspace_id=WORKSPACE.id,
            project_id=PROJECT.id,
        )
        self.repository.add_activity_log(log)
        return log

    def _inbox(self, title: str, summary: str, item_type: str, scope: Scope, user_id: str) -> InboxItem:
        item = InboxItem(
            title=title,
            summary=summary,
            item_type=item_type,
            scope=scope,
            user_id=user_id,
            workspace_id=WORKSPACE.id,
            project_id=PROJECT.id,
        )
        self.repository.add_inbox_item(item)
        return item

    def _memory(
        self,
        title: str,
        summary: str,
        memory_type: str,
        sources: list[Source],
    ) -> MemoryItem:
        item = MemoryItem(
            title=title,
            summary=summary,
            memory_type=memory_type,
            scope=Scope.TEAM_CANDIDATE,
            workspace_id=WORKSPACE.id,
            project_id=PROJECT.id,
            sources=sources,
        )
        self.repository.add_memory_item(item)
        return item

    def _record_short_term_memory(
        self,
        task: Task,
        intent: Intent,
        user_content: str,
        assistant_content: str,
        state: _ChatTurnState,
        user: User,
    ) -> UserMemoryItem | None:
        if intent == Intent.ASK_SYSTEM_INFO or state.pending_tool_approval:
            return None
        sources = self._assistant_sources(state.evidence_post, state.risk_post)
        item = UserMemoryItem(
            user_id=user.id,
            layer=MemoryLayer.SHORT_TERM,
            title=self._short_term_memory_title(intent),
            summary=(
                f"用户请求：{self._truncate(user_content, 120)}；"
                f"处理结果：{self._truncate(assistant_content, 240)}"
            ),
            source_kind=f"chat_workflow:{intent.value}",
            memory_type=self._short_term_memory_type(intent),
            memory_date=now_utc().date(),
            workspace_id=WORKSPACE.id,
            project_id=PROJECT.id,
            source_thread_id=task.thread_id,
            source_task_id=task.id,
            sources=sources,
        )
        return self.repository.add_user_memory_item(item)

    def _audit(self, action: str, target_type: str, target_id: str, metadata: dict[str, object]) -> None:
        self.repository.add_audit_event(
            AuditEvent(actor=self.actor, action=action, target_type=target_type, target_id=target_id, metadata=metadata)
        )

    def _persist_sources(self, sources: list[Source]) -> None:
        for source in sources:
            self.repository.add_source(source)

    def _synthesize_with_llm(
        self,
        fallback_content: str,
        user_content: str,
        intent: Intent,
        evidence_post: BlackboardPost | None,
        risk_post: BlackboardPost | None,
        inbox_items: list[InboxItem],
        memory_items: list[MemoryItem],
        user: User = USER,
        history: list[ChatMessage] | None = None,
    ) -> str:
        return synthesize_with_llm(
            repository=self.repository,
            llm_client=self.llm_client,
            fallback_content=fallback_content,
            user_content=user_content,
            intent=intent,
            evidence_post=evidence_post,
            risk_post=risk_post,
            inbox_items=inbox_items,
            memory_items=memory_items,
            user=user,
            history=history,
        )

    @staticmethod
    def _llm_prompt(
        fallback_content: str,
        user_content: str,
        intent: Intent,
        evidence_post: BlackboardPost | None,
        risk_post: BlackboardPost | None,
        inbox_items: list[InboxItem],
        memory_items: list[MemoryItem],
        history: list[ChatMessage] | None = None,
    ) -> str:
        return build_llm_prompt(
            fallback_content=fallback_content,
            user_content=user_content,
            intent=intent,
            evidence_post=evidence_post,
            risk_post=risk_post,
            inbox_items=inbox_items,
            memory_items=memory_items,
            history=history,
        )

    @staticmethod
    def _assistant_sources(evidence_post: BlackboardPost | None, risk_post: BlackboardPost | None) -> list[Source]:
        return assistant_sources(evidence_post, risk_post)

    @staticmethod
    def _source_titles(evidence_post: BlackboardPost | None, risk_post: BlackboardPost | None) -> str:
        return source_titles(evidence_post, risk_post)

    @staticmethod
    def _task_title(intent: Intent) -> str:
        labels = {
            Intent.GENERAL_CHAT: "普通对话",
            Intent.ASK_MEMORY: "查询团队经验",
            Intent.GENERATE_BRIEF: "生成项目 Brief",
            Intent.RECORD_PRIVATE_NOTE: "记录私有工作上下文",
            Intent.REQUEST_EXTERNAL_RESEARCH: "请求外接 Agent 补充资料",
            Intent.REQUEST_DATA_QUERY: "请求 data_agent 查询指标",
            Intent.REQUEST_RISK_REVIEW: "请求 risk_agent 检查风险",
            Intent.CREATE_MEMORY_CANDIDATE: "创建候选团队记忆",
            Intent.ASK_SYSTEM_INFO: "查询系统与模型配置",
        }
        return labels[intent]

    @staticmethod
    def _short_term_memory_title(intent: Intent) -> str:
        labels = {
            Intent.ASK_MEMORY: "短期记忆：查询团队经验",
            Intent.GENERATE_BRIEF: "短期记忆：生成项目 Brief",
            Intent.RECORD_PRIVATE_NOTE: "短期记忆：私有工作记录",
            Intent.REQUEST_EXTERNAL_RESEARCH: "短期记忆：资料检索结果",
            Intent.REQUEST_DATA_QUERY: "短期记忆：数据查询结果",
            Intent.REQUEST_RISK_REVIEW: "短期记忆：风险检查结果",
            Intent.CREATE_MEMORY_CANDIDATE: "短期记忆：候选记忆提取",
            Intent.ASK_SYSTEM_INFO: "短期记忆：系统信息查询",
            Intent.GENERAL_CHAT: "短期记忆：普通对话",
        }
        return labels[intent]

    @staticmethod
    def _short_term_memory_type(intent: Intent) -> str:
        labels = {
            Intent.ASK_MEMORY: "project_background",
            Intent.GENERATE_BRIEF: "project_background",
            Intent.RECORD_PRIVATE_NOTE: "note",
            Intent.REQUEST_EXTERNAL_RESEARCH: "competitor",
            Intent.REQUEST_DATA_QUERY: "data",
            Intent.REQUEST_RISK_REVIEW: "risk",
            Intent.CREATE_MEMORY_CANDIDATE: "decision",
            Intent.ASK_SYSTEM_INFO: "note",
            Intent.GENERAL_CHAT: "note",
        }
        return labels[intent]

    @staticmethod
    def _workflow_trace(
        classification,
        llm_client: ChatLLM | None,
        selected_workflow: str,
        persisted: bool,
    ) -> ChatWorkflowTrace:
        fallback_reason = None
        if classification.source != "llm":
            fallback_reason = classification.fallback_reason or (
                "model_not_configured" if llm_client is None else "model_low_confidence_or_failed"
            )
        return ChatWorkflowTrace(
            intent=classification.intent,
            confidence=classification.confidence,
            source=classification.source,
            selected_workflow=selected_workflow,
            persisted=persisted,
            llm_used=classification.source == "llm",
            fallback_reason=fallback_reason,
        )

    @staticmethod
    def _truncate(value: str, limit: int) -> str:
        text = " ".join(value.split())
        return text if len(text) <= limit else f"{text[: limit - 1]}…"

    @staticmethod
    def _evidence_answer(evidence_post: BlackboardPost | None, intent: Intent, user_content: str) -> str:
        return evidence_answer(evidence_post, intent, user_content)
