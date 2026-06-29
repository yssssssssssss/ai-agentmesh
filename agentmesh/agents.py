from __future__ import annotations

from dataclasses import dataclass, field
import re

from agentmesh.acquisition import (
    AcquisitionAgent,
    AcquisitionRequest,
    AcquisitionResult,
    MockAcquisitionAgent,
)
from agentmesh.brief_templates import BriefTemplate, select_brief_template
from agentmesh.chat_skills import ChatSkillInvocation, list_chat_skills, parse_chat_skill_invocation, spec_for_intent
from agentmesh.llm import LLMRequestError
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
    DocumentRecord,
    InboxItem,
    Intent,
    MemoryItem,
    MemoryLayer,
    Scope,
    SearchResult,
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
    SynthesisResult,
    assistant_sources,
    build_llm_prompt,
    chat_llm_client,
    evidence_answer,
    source_titles,
    synthesize_with_llm_result,
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


class RequestAlreadyFulfilledError(RuntimeError):
    """Raised when a blackboard request post has already produced evidence."""


@dataclass
class ResearchFulfillment:
    task: Task
    request_post: BlackboardPost
    evidence_post: BlackboardPost
    assistant_message: ChatMessage | None
    activity_logs: list[ActivityLog] = field(default_factory=list)
    inbox_items: list[InboxItem] = field(default_factory=list)
    quarantined: bool = False
    llm_used: bool = False


class PersonalAgent:
    actor = "personal_agent"
    MAX_HISTORY_MESSAGES = 10
    MAX_HISTORY_CHARS = 4000
    SEARCH_STOP_TERMS = {"查询", "搜索", "经验", "项目", "相关", "有没有", "是否", "什么", "资料"}

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

        llm_client = chat_llm_client(self.repository, user, self.llm_client)
        invocation = parse_chat_skill_invocation(content)
        if invocation is None:
            classified_intent, classified_arg, confidence = self._classify_intent(content, history, llm_client)
            classified_spec = spec_for_intent(classified_intent)
            if classified_spec is not None:
                invocation = ChatSkillInvocation(
                    command=classified_spec.command,
                    argument=classified_arg,
                    spec=classified_spec,
                )
                return self._run_skill_invocation(
                    invocation, content, actual_thread_id, user, history,
                    intent_source="llm", confidence=confidence,
                )
            chat_result = self._general_chat_answer(content, user, history, llm_client)
            return self._persist_private_chat_turn(
                content=content,
                assistant_content=chat_result.content,
                thread_id=actual_thread_id,
                user=user,
                selected_workflow="chat",
                source="chat",
                llm_used=chat_result.llm_used,
                fallback_reason=chat_result.fallback_reason,
            )

        if invocation.spec is None:
            return self._persist_private_chat_turn(
                content=content,
                assistant_content=self._unknown_skill_answer(invocation),
                thread_id=actual_thread_id,
                user=user,
                selected_workflow=invocation.command or "$",
                source="skill",
                llm_used=False,
            )

        if invocation.spec.requires_input and not invocation.argument:
            return self._persist_private_chat_turn(
                content=content,
                assistant_content=f"请补充要处理的内容。用法：{invocation.spec.usage}",
                thread_id=actual_thread_id,
                user=user,
                selected_workflow=invocation.spec.command,
                source="skill",
                llm_used=False,
            )

        return self._run_skill_invocation(
            invocation, content, actual_thread_id, user, history,
            intent_source="skill", confidence=1.0,
        )

    _INTENT_CLASSIFIER_SYSTEM_PROMPT = (
        "你是一个意图分类器。根据用户的输入判断最匹配的意图标签。\n"
        "可用标签：\n"
        "- ASK_MEMORY — 查询团队经验、历史记录、知识库\n"
        "- GENERATE_BRIEF — 生成文档、Brief、方案\n"
        "- RECORD_PRIVATE_NOTE — 保存个人笔记、备忘\n"
        "- REQUEST_EXTERNAL_RESEARCH — 搜索外部资料、竞品、网页\n"
        "- REQUEST_DATA_QUERY — 查询数据指标（点击率、转化率等）\n"
        "- REQUEST_RISK_REVIEW — 风险检查、授权审核\n"
        "- CREATE_MEMORY_CANDIDATE — 提炼经验为团队记忆候选\n"
        "- GENERAL_CHAT — 普通对话、闲聊、不确定\n\n"
        "规则：\n"
        "1. 只选一个标签。不确定时选 GENERAL_CHAT。\n"
        "2. 只输出一行：标签|参数（参数为用户真正想查/做的核心内容）。\n"
        "3. 如果选 GENERAL_CHAT，参数留空。\n"
        "示例输出：ASK_MEMORY|618 家电会场首屏经验"
    )

    _INTENT_LABEL_MAP: dict[str, Intent] = {
        "ASK_MEMORY": Intent.ASK_MEMORY,
        "GENERATE_BRIEF": Intent.GENERATE_BRIEF,
        "RECORD_PRIVATE_NOTE": Intent.RECORD_PRIVATE_NOTE,
        "REQUEST_EXTERNAL_RESEARCH": Intent.REQUEST_EXTERNAL_RESEARCH,
        "REQUEST_DATA_QUERY": Intent.REQUEST_DATA_QUERY,
        "REQUEST_RISK_REVIEW": Intent.REQUEST_RISK_REVIEW,
        "CREATE_MEMORY_CANDIDATE": Intent.CREATE_MEMORY_CANDIDATE,
        "GENERAL_CHAT": Intent.GENERAL_CHAT,
    }

    def _classify_intent(
        self,
        content: str,
        history: list[ChatMessage],
        llm_client,
    ) -> tuple[Intent, str, float]:
        if llm_client is None:
            return Intent.GENERAL_CHAT, content, 0.0
        try:
            response = llm_client.complete(self._INTENT_CLASSIFIER_SYSTEM_PROMPT, content)
        except LLMRequestError:
            return Intent.GENERAL_CHAT, content, 0.0
        except Exception:
            return Intent.GENERAL_CHAT, content, 0.0
        line = response.strip().split("\n")[0].strip()
        if "|" in line:
            label, _, argument = line.partition("|")
        else:
            label = line
            argument = ""
        label = label.strip().upper()
        intent = self._INTENT_LABEL_MAP.get(label)
        if intent is None or intent == Intent.GENERAL_CHAT:
            return Intent.GENERAL_CHAT, content, 0.0
        return intent, argument.strip() or content, 0.85

    def _run_skill_invocation(
        self,
        invocation: ChatSkillInvocation,
        content: str,
        thread_id: str,
        user: User,
        history: list[ChatMessage],
        *,
        intent_source: str,
        confidence: float,
    ) -> ChatResponse:
        skill_content = invocation.argument or content
        intent = invocation.spec.intent
        workflow_trace = self._command_workflow_trace(
            intent, invocation.spec.command, persisted=True, source=intent_source, confidence=confidence,
        )

        self._ensure_thread(thread_id, content, user)

        user_message = self.repository.add_chat_message(
            ChatMessage(
                thread_id=thread_id,
                role=ChatRole.USER,
                content=content,
                scope=Scope.PRIVATE,
            )
        )

        task = self.repository.add_task(
            Task(
                thread_id=thread_id,
                intent=intent,
                status=TaskStatus.RUNNING,
                title=self._task_title(intent),
                steps=["received_user_message", "parsed_skill_command"],
            )
        )
        self._audit(
            "create_task",
            "task",
            task.id,
            {"intent": intent, "intent_source": intent_source, "command": invocation.spec.command, "confidence": confidence},
        )

        state = _ChatTurnState()

        try:
            if intent == Intent.ASK_MEMORY:
                self._handle_memory_search(task, skill_content, user, state)

            if intent == Intent.REQUEST_DATA_QUERY:
                self._handle_data_query(task, skill_content, user, state)

            if intent in {
                Intent.GENERATE_BRIEF,
                Intent.REQUEST_EXTERNAL_RESEARCH,
                Intent.CREATE_MEMORY_CANDIDATE,
            }:
                self._handle_acquisition_intent(task, skill_content, intent, user, state)

            if intent == Intent.REQUEST_RISK_REVIEW:
                self._handle_risk_review(task, skill_content, state)
        except Exception as error:
            self._mark_task_failed(task, error)
            raise

        assistant_content = self._assistant_content_for_turn(intent, skill_content, state, user)

        if not state.pending_tool_approval and intent not in {Intent.ASK_SYSTEM_INFO, Intent.GENERATE_BRIEF}:
            synthesis = self._synthesize_with_llm(
                fallback_content=assistant_content,
                user_content=skill_content,
                intent=intent,
                evidence_post=state.synthesis_evidence_post,
                risk_post=state.risk_post,
                inbox_items=state.inbox_items,
                memory_items=state.memory_items,
                user=user,
                history=history,
            )
            assistant_content = synthesis.content
            workflow_trace.llm_used = synthesis.llm_used
            workflow_trace.fallback_reason = synthesis.fallback_reason

        state.activity_logs.append(
            self._activity(
                title="处理了一条用户请求",
                summary=f"通过 {invocation.spec.command} 调用 {intent.value}，默认保留在个人上下文。",
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
                thread_id=thread_id,
                role=ChatRole.ASSISTANT,
                content=assistant_content,
                scope=Scope.PRIVATE,
                sources=self._assistant_sources(state.evidence_post, state.risk_post),
            )
        )
        self._audit("return_chat_response", "chat_message", assistant_message.id, {"task_id": task.id})
        memory_item = self._record_short_term_memory(task, intent, skill_content, assistant_content, state, user)
        if memory_item is not None:
            state.user_memory_items.append(memory_item)

        return ChatResponse(
            thread_id=thread_id,
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

    def _persist_private_chat_turn(
        self,
        content: str,
        assistant_content: str,
        thread_id: str,
        user: User,
        selected_workflow: str,
        source: str,
        llm_used: bool,
        fallback_reason: str | None = None,
    ) -> ChatResponse:
        self._ensure_thread(thread_id, content, user)
        user_message = self.repository.add_chat_message(
            ChatMessage(thread_id=thread_id, role=ChatRole.USER, content=content, scope=Scope.PRIVATE)
        )
        assistant_message = self.repository.add_chat_message(
            ChatMessage(thread_id=thread_id, role=ChatRole.ASSISTANT, content=assistant_content, scope=Scope.PRIVATE)
        )
        return ChatResponse(
            thread_id=thread_id,
            user_message=user_message,
            assistant_message=assistant_message,
            task=None,
            activity_logs=[],
            inbox_items=[],
            memory_items=[],
            user_memory_items=[],
            workflow_trace=ChatWorkflowTrace(
                intent=Intent.GENERAL_CHAT,
                confidence=1.0,
                source=source,
                selected_workflow=selected_workflow,
                persisted=True,
                llm_used=llm_used,
                fallback_reason=fallback_reason,
            ),
        )

    @staticmethod
    def _unknown_skill_answer(invocation: ChatSkillInvocation) -> str:
        skills = "、".join(item["command"] for item in list_chat_skills())
        command = invocation.command or "$"
        return f"没有找到 {command} 这个能力。当前可用能力：{skills}。"

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

    def _handle_memory_search(self, task: Task, content: str, user: User, state: _ChatTurnState) -> None:
        results = self._search_team_brain(content, user)
        if results:
            state.evidence_post = self._create_memory_search_evidence(task, results)
            state.synthesis_evidence_post = state.evidence_post
            task.steps.append("searched_memory")
            state.activity_logs.append(
                self._activity(
                    title="检索个人与团队记忆",
                    summary=f"命中 {len(results)} 条个人、项目或团队记忆，未发起新的 BBS 求助。",
                    category="personal",
                    scope=Scope.PRIVATE,
                )
            )
            return

        state.request_post = self._create_request_post(
            task,
            content,
            title="请求补充团队经验",
            read_by_agents=["research_agent", "data_agent"],
            current_owner_agent_id="research_agent",
            current_owner_label="research_agent",
            done_when="团队成员或服务 Agent 补充可引用经验",
        )
        task.status = TaskStatus.WAITING_EXTERNAL_AGENT
        task.steps.extend(["searched_memory", "created_blackboard_request"])
        state.activity_logs.append(
            self._activity(
                title="记忆未命中，转入 BBS 求助",
                summary="个人、项目和团队记忆中没有足够结果，已在项目 BBS 发帖等待补充。",
                category="external_agent",
                scope=Scope.PROJECT,
            )
        )

    def _search_team_brain(self, query: str, user: User) -> list[SearchResult]:
        allowed_scopes = {Scope.PRIVATE, Scope.PROJECT, Scope.TEAM_CANDIDATE, Scope.TEAM_ACCEPTED}
        direct_results = self.repository.search(
            query,
            allowed_scopes,
            workspace_id=WORKSPACE.id,
            project_id=PROJECT.id,
            user_id=user.id,
        )
        direct_results = [
            result
            for result in direct_results
            if result.result_type in {"user_memory_item", "memory_item", "document", "blackboard_evidence"}
        ]
        if direct_results:
            return direct_results[:5]

        terms = self._search_terms(query)
        scored_results: list[tuple[int, SearchResult]] = []
        for result in self._memory_search_pool(user):
            text = f"{result.title} {result.summary}".lower()
            score = sum(1 for term in terms if term in text)
            if score >= 2:
                scored_results.append((score, result))
        scored_results.sort(key=lambda item: (item[0], item[1].created_at), reverse=True)
        return [result for _, result in scored_results[:5]]

    def _memory_search_pool(self, user: User) -> list[SearchResult]:
        results: list[SearchResult] = []
        for item in self.repository.user_memory_items:
            if item.user_id != user.id:
                continue
            if item.workspace_id != WORKSPACE.id or item.project_id != PROJECT.id:
                continue
            results.append(
                SearchResult(
                    id=item.id,
                    result_type="user_memory_item",
                    title=item.title,
                    summary=item.summary,
                    scope=item.scope,
                    sources=item.sources,
                    created_at=item.created_at,
                )
            )

        for item in self.repository.memory_items:
            if item.workspace_id != WORKSPACE.id or item.project_id != PROJECT.id:
                continue
            results.append(
                SearchResult(
                    id=item.id,
                    result_type="memory_item",
                    title=item.title,
                    summary=item.summary,
                    scope=item.scope,
                    sources=item.sources,
                    created_at=item.created_at,
                )
            )

        for document in self.repository.documents:
            if document.uploaded_by != user.id:
                continue
            if document.workspace_id != WORKSPACE.id or document.project_id != PROJECT.id:
                continue
            results.append(
                SearchResult(
                    id=document.id,
                    result_type="document",
                    title=document.title,
                    summary=document.text[:500],
                    scope=Scope.PRIVATE,
                    sources=[document.source],
                    created_at=document.created_at,
                )
            )

        for post in self.repository.blackboard_posts:
            if post.scope not in {Scope.PROJECT, Scope.TEAM_CANDIDATE, Scope.TEAM_ACCEPTED}:
                continue
            if post.post_type not in {
                BlackboardPostType.EVIDENCE,
                BlackboardPostType.DECISION,
                BlackboardPostType.MEMORY_CANDIDATE,
                BlackboardPostType.ARCHIVE,
            }:
                continue
            results.append(
                SearchResult(
                    id=post.id,
                    result_type=f"blackboard_{post.post_type.value}",
                    title=post.title,
                    summary=post.content,
                    scope=post.scope,
                    sources=post.sources,
                    created_at=post.created_at,
                )
            )
        return results

    @staticmethod
    def _create_memory_search_evidence(task: Task, results: list[SearchResult]) -> BlackboardPost:
        sources: list[Source] = []
        for result in results:
            sources.extend(result.sources)
        lines = [f"{index}. {result.title}：{result.summary}" for index, result in enumerate(results[:3], start=1)]
        return BlackboardPost(
            task_id=task.id,
            post_type=BlackboardPostType.EVIDENCE,
            actor="memory_search",
            title="个人、项目与团队记忆检索结果",
            content="\n".join(lines),
            scope=Scope.PRIVATE,
            permission="private_visible",
            sources=sources,
            read_by_agents=[PersonalAgent.actor],
            collaboration_stage=CollaborationStage.REVIEW,
            done_when="个人 Agent 基于记忆结果回答用户",
        )

    @staticmethod
    def _search_terms(query: str) -> list[str]:
        text = query.strip().lower()
        terms = set(re.findall(r"[a-z0-9]+", text))
        for part in re.findall(r"[\u4e00-\u9fff]{2,}", text):
            terms.add(part)
            for size in (2, 3):
                terms.update(part[index : index + size] for index in range(0, len(part) - size + 1))
        return sorted(term for term in terms if len(term) >= 2 and term not in PersonalAgent.SEARCH_STOP_TERMS)

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

    def fulfill_research_request(self, request_post: BlackboardPost, user: User) -> ResearchFulfillment:
        """消费一条 waiting_external_agent 的 BBS 求助帖，产出 evidence 回帖并推进任务。

        让 research_agent 真正认领 ``_handle_memory_search`` 留下的 open request，
        通过 acquisition 边界补充证据；命中提示词注入则隔离转人工审核，否则把任务推回完成
        并向原对话线程追加一条带来源的回答。重复处置同一请求会抛 RequestAlreadyFulfilledError。
        """
        if request_post.post_type != BlackboardPostType.REQUEST:
            raise ValueError("Only request posts can be fulfilled by a research agent")

        already = next(
            (
                post
                for post in self.repository.blackboard_posts
                if post.related_post_id == request_post.id and post.post_type == BlackboardPostType.EVIDENCE
            ),
            None,
        )
        if already is not None:
            raise RequestAlreadyFulfilledError(request_post.id)

        task = self.repository.get_task(request_post.task_id)
        if task is None:
            raise ValueError("Request post has no backing task")

        activity_logs: list[ActivityLog] = []
        inbox_items: list[InboxItem] = []

        result = self.acquisition_agent.acquire(
            AcquisitionRequest(
                query=request_post.content,
                intent=task.intent,
                workspace_id=WORKSPACE.id,
                project_id=PROJECT.id,
                user_id=user.id,
                task_id=task.id,
                request_post_id=request_post.id,
            )
        )
        evidence_post = self._create_evidence_post(task, request_post, result)
        self._persist_sources(evidence_post.sources)

        content_risk = assess_external_content(result.content)
        if content_risk.decision == RiskDecision.NEEDS_REVIEW:
            evidence_post.status = "needs_review"
            evidence_post.collaboration_stage = CollaborationStage.BLOCKED
            self.repository.add_blackboard_post(evidence_post)
            inbox_items.append(
                self._inbox(
                    title="审核可疑外部资料",
                    summary="BBS 求助返回的外部资料包含疑似提示词注入内容，已隔离，暂不用于回答合成。",
                    item_type="prompt_injection_review",
                    scope=Scope.PROJECT,
                    user_id=user.id,
                    metadata={"request_post_id": request_post.id, "evidence_post_id": evidence_post.id},
                )
            )
            task.steps.append("quarantined_research_evidence")
            task.collaboration_stage = CollaborationStage.BLOCKED
            task.updated_at = now_utc()
            self.repository.save_task(task)
            activity_logs.append(
                self._activity(
                    title="BBS 求助资料被隔离",
                    summary=f"{evidence_post.actor} 返回的资料疑似含提示词注入，已隔离并转人工审核。",
                    category="external_agent",
                    scope=Scope.PROJECT,
                )
            )
            self._audit(
                "fulfill_blackboard_request",
                "blackboard_post",
                request_post.id,
                {"task_id": task.id, "evidence_post_id": evidence_post.id, "quarantined": True},
            )
            return ResearchFulfillment(
                task=task,
                request_post=request_post,
                evidence_post=evidence_post,
                assistant_message=None,
                activity_logs=activity_logs,
                inbox_items=inbox_items,
                quarantined=True,
            )

        self.repository.add_blackboard_post(evidence_post)
        task.steps.append("received_blackboard_evidence")
        activity_logs.append(
            self._activity(
                title="BBS 求助得到补充",
                summary=f"{evidence_post.actor} 在项目 BBS 回帖补充了可引用证据。",
                category="external_agent",
                scope=Scope.PROJECT,
            )
        )
        assistant_message, llm_used = self._finalize_research_evidence(task, request_post, evidence_post, user)
        self._audit(
            "fulfill_blackboard_request",
            "blackboard_post",
            request_post.id,
            {"task_id": task.id, "evidence_post_id": evidence_post.id, "quarantined": False},
        )
        return ResearchFulfillment(
            task=task,
            request_post=request_post,
            evidence_post=evidence_post,
            assistant_message=assistant_message,
            activity_logs=activity_logs,
            inbox_items=inbox_items,
            quarantined=False,
            llm_used=llm_used,
        )

    def _finalize_research_evidence(
        self,
        task: Task,
        request_post: BlackboardPost,
        evidence_post: BlackboardPost,
        user: User,
    ) -> tuple[ChatMessage, bool]:
        """把一条已采纳的 evidence 推进为最终回答:回填证据状态、完成任务并向原线程追加带源回复。"""
        evidence_post.status = "published"
        evidence_post.collaboration_stage = CollaborationStage.REVIEW
        self.repository.add_blackboard_post(evidence_post)

        request_post.collaboration_stage = CollaborationStage.REVIEW
        if evidence_post.actor not in request_post.read_by_agents:
            request_post.read_by_agents.append(evidence_post.actor)
        self.repository.add_blackboard_post(request_post)

        task.status = TaskStatus.COMPLETED
        task.collaboration_stage = CollaborationStage.COMPLETED
        task.updated_at = now_utc()
        self.repository.save_task(task)

        fallback = self._evidence_answer(evidence_post, task.intent, request_post.content)
        synthesis = self._synthesize_with_llm(
            fallback_content=fallback,
            user_content=request_post.content,
            intent=task.intent,
            evidence_post=evidence_post,
            risk_post=None,
            inbox_items=[],
            memory_items=[],
            user=user,
            history=self._get_thread_history(task.thread_id),
        )
        assistant_message = self.repository.add_chat_message(
            ChatMessage(
                thread_id=task.thread_id,
                role=ChatRole.ASSISTANT,
                content=synthesis.content,
                scope=Scope.PRIVATE,
                sources=self._assistant_sources(evidence_post, None),
            )
        )
        return assistant_message, synthesis.llm_used

    def resolve_quarantined_research(
        self,
        request_post: BlackboardPost,
        evidence_post: BlackboardPost,
        user: User,
        action: str,
    ) -> ResearchFulfillment:
        """人工对隔离的 BBS 求助资料做终态决定:release 放行补全闭环,discard 丢弃并终止任务。

        关闭了隔离分支永远停在 waiting_external_agent 的漏洞:误报放行后任务正常完成,
        真注入则丢弃证据并把任务标记为 failed,不再悬空。
        """
        if action not in {"release", "discard"}:
            raise ValueError("action must be 'release' or 'discard'")
        task = self.repository.get_task(request_post.task_id)
        if task is None:
            raise ValueError("Request post has no backing task")
        if evidence_post.status != "needs_review":
            raise RequestAlreadyFulfilledError(request_post.id)

        if action == "release":
            task.steps.append("released_quarantined_research_evidence")
            activity_logs = [
                self._activity(
                    title="人工放行隔离资料",
                    summary="审核确认外部资料安全，已放行用于回答合成并完成 BBS 求助。",
                    category="external_agent",
                    scope=Scope.PROJECT,
                )
            ]
            assistant_message, llm_used = self._finalize_research_evidence(task, request_post, evidence_post, user)
            self._audit(
                "resolve_quarantined_research",
                "blackboard_post",
                request_post.id,
                {"task_id": task.id, "evidence_post_id": evidence_post.id, "action": "release"},
            )
            return ResearchFulfillment(
                task=task,
                request_post=request_post,
                evidence_post=evidence_post,
                assistant_message=assistant_message,
                activity_logs=activity_logs,
                inbox_items=[],
                quarantined=False,
                llm_used=llm_used,
            )

        evidence_post.status = "discarded"
        evidence_post.collaboration_stage = CollaborationStage.BLOCKED
        self.repository.add_blackboard_post(evidence_post)
        task.status = TaskStatus.FAILED
        task.collaboration_stage = CollaborationStage.BLOCKED
        task.steps.append("discarded_quarantined_research_evidence")
        task.updated_at = now_utc()
        self.repository.save_task(task)
        activity_logs = [
            self._activity(
                title="人工丢弃隔离资料",
                summary="审核确认外部资料存在风险，已丢弃证据并终止该 BBS 求助任务。",
                category="external_agent",
                scope=Scope.PROJECT,
            )
        ]
        self._audit(
            "resolve_quarantined_research",
            "blackboard_post",
            request_post.id,
            {"task_id": task.id, "evidence_post_id": evidence_post.id, "action": "discard"},
        )
        return ResearchFulfillment(
            task=task,
            request_post=request_post,
            evidence_post=evidence_post,
            assistant_message=None,
            activity_logs=activity_logs,
            inbox_items=[],
            quarantined=True,
        )

    def _assistant_content_for_turn(self, intent: Intent, content: str, state: _ChatTurnState, user: User) -> str:
        if intent == Intent.ASK_SYSTEM_INFO:
            return self._system_info_answer(user)
        if intent == Intent.RECORD_PRIVATE_NOTE:
            return "已记录为你的私有工作上下文，暂不共享到项目或团队记忆。"
        if intent == Intent.GENERATE_BRIEF:
            brief_document = self._create_brief_document(content, state, user)
            state.inbox_items.append(
                self._inbox(
                    title="确认 Brief 中的设计原则",
                    summary="已生成 Brief 草稿。该原则会影响项目 Brief 和后续团队记忆，建议在收件箱打开确认。",
                    item_type="decision_review",
                    scope=Scope.PROJECT,
                    user_id=user.id,
                    metadata={"document_id": brief_document.id, "artifact_type": "brief_draft"},
                )
            )
            return (
                f"我已按「{brief_document.metadata.get('template_title', '匹配模板')}」生成 Brief 草稿"
                f"《{brief_document.title}》，并放入收件箱供你打开确认。"
                "草稿已结合当前用户需求、可引用证据和来源生成。"
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
        if intent == Intent.ASK_MEMORY and state.request_post and state.evidence_post is None:
            return "我没有在个人、项目或团队记忆中找到足够结果，已在项目 BBS 发帖等待团队或服务 Agent 补充。"
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
    ) -> SynthesisResult:
        if llm_client is None:
            return SynthesisResult(
                content="我可以先帮你澄清问题；如果你需要查资料、查数据、生成 Brief 或沉淀记忆，我会再进入对应工作流。",
                llm_used=False,
                fallback_reason="llm_not_configured",
            )
        history_text = "\n".join(
            f"{'用户' if message.role == ChatRole.USER else '助理'}：{message.content}" for message in history[-6:]
        )
        prompt = f"历史上下文：\n{history_text or '无'}\n\n用户输入：{content}\n请直接自然回复，不要创建任务或编造数据。"
        try:
            generated = llm_client.complete(
                system_prompt=(
                    "你是 AgentMesh 作战室里的中文对话助手。"
                    "当前输入未形成明确的项目工作流意图，只做普通对话、解释或澄清。"
                    "不要声称已经调用 Agent，不要写入记忆，不要创建任务。"
                ),
                user_prompt=prompt,
            )
        except Exception as error:
            reason = error.reason if isinstance(error, LLMRequestError) else "llm_error"
            return SynthesisResult(
                content="我可以继续和你澄清需求；当问题明确需要查资料、查数据、生成 Brief 或沉淀记忆时，我会进入对应 Agent 工作流。",
                llm_used=False,
                fallback_reason=reason,
            )
        content_text = generated.strip()
        if not content_text:
            return SynthesisResult(content="我在，可以继续说。", llm_used=False, fallback_reason="empty_response")
        return SynthesisResult(content=content_text, llm_used=True)

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

    def _create_brief_document(self, content: str, state: _ChatTurnState, user: User) -> DocumentRecord:
        template = select_brief_template(content)
        title = f"Brief 草稿：{template.title}"
        evidence = state.synthesis_evidence_post.content if state.synthesis_evidence_post else "暂无可引用证据。"
        source_titles = self._source_titles(state.synthesis_evidence_post, state.risk_post)
        document_source = Source(
            title=title,
            source_type="generated_brief",
            reference=f"generated://brief/{new_id('brief')}",
        )
        self.repository.add_source(document_source)
        fallback_draft = self._brief_template_fallback(content, template, evidence, source_titles)
        draft, generation_mode = self._generate_brief_draft_with_llm(content, template, evidence, source_titles, fallback_draft, user)
        return self.repository.add_document(
            DocumentRecord(
                title=title,
                file_name="generated-brief.md",
                content_type="text/markdown",
                text=draft,
                source=document_source,
                workspace_id=WORKSPACE.id,
                project_id=PROJECT.id,
                uploaded_by=user.id,
                metadata={
                    "generated_by": self.actor,
                    "artifact_type": "brief_draft",
                    "template_id": template.id,
                    "template_title": template.title,
                    "generation_mode": generation_mode,
                },
            )
        )

    def _generate_brief_draft_with_llm(
        self,
        content: str,
        template: BriefTemplate,
        evidence: str,
        source_titles: str,
        fallback_draft: str,
        user: User,
    ) -> tuple[str, str]:
        client = chat_llm_client(self.repository, user, self.llm_client)
        if client is None:
            return fallback_draft, "template_fallback"
        try:
            draft = client.complete(
                system_prompt=(
                    "你是 AgentMesh 的资深项目 Brief 写作助手。"
                    "必须基于用户需求、匹配到的 Brief 模板和可引用证据生成中文 Markdown。"
                    "不要编造来源；来源只能使用输入中的来源。"
                ),
                user_prompt=(
                    f"用户需求：{content}\n\n"
                    f"匹配模板：{template.title}\n"
                    f"模板说明：{template.description}\n"
                    f"模板写作要求：{template.guidance}\n"
                    f"建议章节：{'、'.join(template.sections)}\n\n"
                    f"可引用证据：{evidence}\n"
                    f"来源：{source_titles}\n\n"
                    "请生成一份可放入收件箱确认的 Brief 草稿。"
                ),
            ).strip()
        except Exception:
            return fallback_draft, "template_fallback"
        return (draft or fallback_draft), ("llm_regenerated" if draft else "template_fallback")

    @staticmethod
    def _brief_template_fallback(content: str, template: BriefTemplate, evidence: str, source_titles: str) -> str:
        sections = "\n".join(f"- {section}" for section in template.sections)
        return (
            f"# Brief 草稿：{template.title}\n\n"
            f"## 匹配模板\n{template.title}：{template.description}\n\n"
            f"## 用户请求\n{content}\n\n"
            f"## 模板章节\n{sections}\n\n"
            "## 核心结论\n"
            "基于当前需求和可引用证据，优先沿用模板中的关键章节，并围绕已验证的项目经验生成 Brief 草稿。\n\n"
            "## 可引用依据\n"
            f"{evidence}\n\n"
            "## 写作原则\n"
            f"{template.guidance}\n\n"
            "## 待确认\n"
            "- 是否将该 Brief 草稿作为项目正式 Brief 的基础版本。\n"
            "- 是否需要补充更多真实数据、竞品资料或用户研究。\n"
            "- 是否将确认后的结论沉淀为团队候选记忆。\n\n"
            f"## 来源\n{source_titles}\n"
        )

    def _inbox(
        self,
        title: str,
        summary: str,
        item_type: str,
        scope: Scope,
        user_id: str,
        metadata: dict[str, str] | None = None,
    ) -> InboxItem:
        item = InboxItem(
            title=title,
            summary=summary,
            item_type=item_type,
            scope=scope,
            user_id=user_id,
            workspace_id=WORKSPACE.id,
            project_id=PROJECT.id,
            metadata=metadata or {},
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
    ):
        return synthesize_with_llm_result(
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
    def _command_workflow_trace(
        intent: Intent, command: str, persisted: bool, source: str = "skill", confidence: float = 1.0,
    ) -> ChatWorkflowTrace:
        return ChatWorkflowTrace(
            intent=intent,
            confidence=confidence,
            source=source,
            selected_workflow=command,
            persisted=persisted,
            llm_used=False,
        )

    @staticmethod
    def _truncate(value: str, limit: int) -> str:
        text = " ".join(value.split())
        return text if len(text) <= limit else f"{text[: limit - 1]}…"

    @staticmethod
    def _evidence_answer(evidence_post: BlackboardPost | None, intent: Intent, user_content: str) -> str:
        return evidence_answer(evidence_post, intent, user_content)
