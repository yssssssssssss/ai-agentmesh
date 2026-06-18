from __future__ import annotations

import os
import sqlite3
from datetime import date as dt_date
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from agentmesh.models import (
    ActivityLog,
    Agent,
    AgentToolGrant,
    AuditEvent,
    AuthCredential,
    AuthSession,
    AutoBlackboardPostRequest,
    BlackboardPost,
    BlackboardPostType,
    ChatMessage,
    ChatThread,
    DocumentParseJob,
    DocumentRecord,
    InboxItem,
    MemoryItem,
    ModelDefinition,
    Project,
    RiskPolicyRule,
    ScheduledAgentTaskDefinition,
    Scope,
    SearchResult,
    Source,
    Task,
    Team,
    TeamMembership,
    ToolDefinition,
    User,
    UserMemoryItem,
    Workspace,
)

ModelT = TypeVar("ModelT", bound=BaseModel)

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = ROOT_DIR / "data" / "agentmesh.sqlite3"


class SQLiteStore:
    def __init__(self, db_path: str | Path | None = None):
        configured_path = db_path or os.getenv("AGENTMESH_DB_PATH") or DEFAULT_DB_PATH
        self.db_path = Path(configured_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        self._ensure_schema(connection)
        return connection

    def _init_schema(self) -> None:
        with sqlite3.connect(self.db_path) as connection:
            self._ensure_schema(connection)

    @staticmethod
    def _ensure_schema(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS records (
              collection TEXT NOT NULL,
              id TEXT NOT NULL,
              payload TEXT NOT NULL,
              created_order INTEGER PRIMARY KEY AUTOINCREMENT,
              UNIQUE(collection, id)
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_records_collection ON records(collection, created_order)"
        )

    def reset(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM records")

    def _upsert(self, collection: str, item: BaseModel) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO records(collection, id, payload)
                VALUES (?, ?, ?)
                ON CONFLICT(collection, id)
                DO UPDATE SET payload = excluded.payload
                """,
                (collection, item.id, item.model_dump_json()),
            )

    def _get(self, collection: str, item_id: str, model: type[ModelT]) -> ModelT | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM records WHERE collection = ? AND id = ?",
                (collection, item_id),
            ).fetchone()
        if row is None:
            return None
        return model.model_validate_json(row["payload"])

    def _list(self, collection: str, model: type[ModelT]) -> list[ModelT]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload FROM records WHERE collection = ? ORDER BY created_order",
                (collection,),
            ).fetchall()
        return [model.model_validate_json(row["payload"]) for row in rows]

    @property
    def chat_messages(self) -> list[ChatMessage]:
        return self._list("chat_messages", ChatMessage)

    @property
    def workspaces(self) -> list[Workspace]:
        return self._list("workspaces", Workspace)

    @property
    def projects(self) -> list[Project]:
        return self._list("projects", Project)

    @property
    def chat_threads(self) -> list[ChatThread]:
        return self._list("chat_threads", ChatThread)

    @property
    def tasks(self) -> list[Task]:
        return self._list("tasks", Task)

    @property
    def blackboard_posts(self) -> list[BlackboardPost]:
        return self._list("blackboard_posts", BlackboardPost)

    @property
    def auto_blackboard_post_requests(self) -> list[AutoBlackboardPostRequest]:
        return self._list("auto_blackboard_post_requests", AutoBlackboardPostRequest)

    @property
    def activity_logs(self) -> list[ActivityLog]:
        return self._list("activity_logs", ActivityLog)

    @property
    def inbox_items(self) -> list[InboxItem]:
        return self._list("inbox_items", InboxItem)

    @property
    def memory_items(self) -> list[MemoryItem]:
        return self._list("memory_items", MemoryItem)

    @property
    def user_memory_items(self) -> list[UserMemoryItem]:
        return self._list("user_memory_items", UserMemoryItem)

    @property
    def sources(self) -> list[Source]:
        return self._list("sources", Source)

    @property
    def documents(self) -> list[DocumentRecord]:
        return self._list("documents", DocumentRecord)

    @property
    def document_parse_jobs(self) -> list[DocumentParseJob]:
        return self._list("document_parse_jobs", DocumentParseJob)

    @property
    def audit_events(self) -> list[AuditEvent]:
        return self._list("audit_events", AuditEvent)

    @property
    def agents(self) -> list[Agent]:
        return self._list("agents", Agent)

    @property
    def tool_definitions(self) -> list[ToolDefinition]:
        return self._list("tool_definitions", ToolDefinition)

    @property
    def model_definitions(self) -> list[ModelDefinition]:
        return self._list("model_definitions", ModelDefinition)

    @property
    def risk_policy_rules(self) -> list[RiskPolicyRule]:
        return self._list("risk_policy_rules", RiskPolicyRule)

    @property
    def scheduled_agent_task_definitions(self) -> list[ScheduledAgentTaskDefinition]:
        return self._list("scheduled_agent_task_definitions", ScheduledAgentTaskDefinition)

    @property
    def agent_tool_grants(self) -> list[AgentToolGrant]:
        return self._list("agent_tool_grants", AgentToolGrant)

    @property
    def users(self) -> list[User]:
        return self._list("users", User)

    @property
    def auth_credentials(self) -> list[AuthCredential]:
        return self._list("auth_credentials", AuthCredential)

    @property
    def auth_sessions(self) -> list[AuthSession]:
        return self._list("auth_sessions", AuthSession)

    @property
    def teams(self) -> list[Team]:
        return self._list("teams", Team)

    @property
    def team_memberships(self) -> list[TeamMembership]:
        return self._list("team_memberships", TeamMembership)

    def add_chat_message(self, message: ChatMessage) -> ChatMessage:
        self._upsert("chat_messages", message)
        return message

    def save_workspace(self, workspace: Workspace) -> Workspace:
        self._upsert("workspaces", workspace)
        return workspace

    def save_project(self, project: Project) -> Project:
        self._upsert("projects", project)
        return project

    def add_chat_thread(self, thread: ChatThread) -> ChatThread:
        self._upsert("chat_threads", thread)
        return thread

    def save_chat_thread(self, thread: ChatThread) -> ChatThread:
        self._upsert("chat_threads", thread)
        return thread

    def add_task(self, task: Task) -> Task:
        self._upsert("tasks", task)
        return task

    def save_task(self, task: Task) -> Task:
        self._upsert("tasks", task)
        return task

    def add_blackboard_post(self, post: BlackboardPost) -> BlackboardPost:
        self._upsert("blackboard_posts", post)
        return post

    def enqueue_auto_blackboard_post(self, request: AutoBlackboardPostRequest) -> AutoBlackboardPostRequest:
        self._upsert("auto_blackboard_post_requests", request)
        return request

    def save_auto_blackboard_post_request(
        self,
        request: AutoBlackboardPostRequest,
    ) -> AutoBlackboardPostRequest:
        self._upsert("auto_blackboard_post_requests", request)
        return request

    def add_activity_log(self, log: ActivityLog) -> ActivityLog:
        self._upsert("activity_logs", log)
        return log

    def save_agent(self, agent: Agent) -> Agent:
        self._upsert("agents", agent)
        return agent

    def save_tool_definition(self, tool: ToolDefinition) -> ToolDefinition:
        self._upsert("tool_definitions", tool)
        return tool

    def save_model_definition(self, model: ModelDefinition) -> ModelDefinition:
        self._upsert("model_definitions", model)
        return model

    def save_risk_policy_rule(self, rule: RiskPolicyRule) -> RiskPolicyRule:
        self._upsert("risk_policy_rules", rule)
        return rule

    def save_scheduled_agent_task_definition(
        self,
        definition: ScheduledAgentTaskDefinition,
    ) -> ScheduledAgentTaskDefinition:
        self._upsert("scheduled_agent_task_definitions", definition)
        return definition

    def save_agent_tool_grant(self, grant: AgentToolGrant) -> AgentToolGrant:
        self._upsert("agent_tool_grants", grant)
        return grant

    def save_user(self, user: User) -> User:
        self._upsert("users", user)
        return user

    def save_auth_credential(self, credential: AuthCredential) -> AuthCredential:
        self._upsert("auth_credentials", credential)
        return credential

    def save_auth_session(self, session: AuthSession) -> AuthSession:
        self._upsert("auth_sessions", session)
        return session

    def save_team(self, team: Team) -> Team:
        self._upsert("teams", team)
        return team

    def save_team_membership(self, membership: TeamMembership) -> TeamMembership:
        self._upsert("team_memberships", membership)
        return membership

    def add_inbox_item(self, item: InboxItem) -> InboxItem:
        self._upsert("inbox_items", item)
        return item

    def save_inbox_item(self, item: InboxItem) -> InboxItem:
        self._upsert("inbox_items", item)
        return item

    def add_memory_item(self, item: MemoryItem) -> MemoryItem:
        self._upsert("memory_items", item)
        return item

    def save_memory_item(self, item: MemoryItem) -> MemoryItem:
        self._upsert("memory_items", item)
        return item

    def add_user_memory_item(self, item: UserMemoryItem) -> UserMemoryItem:
        self._upsert("user_memory_items", item)
        return item

    def save_user_memory_item(self, item: UserMemoryItem) -> UserMemoryItem:
        self._upsert("user_memory_items", item)
        return item

    def add_source(self, source: Source) -> Source:
        self._upsert("sources", source)
        return source

    def add_document(self, document: DocumentRecord) -> DocumentRecord:
        self._upsert("documents", document)
        return document

    def save_document_parse_job(self, job: DocumentParseJob) -> DocumentParseJob:
        self._upsert("document_parse_jobs", job)
        return job

    def add_audit_event(self, event: AuditEvent) -> AuditEvent:
        self._upsert("audit_events", event)
        return event

    def get_inbox_item(self, item_id: str) -> InboxItem | None:
        return self._get("inbox_items", item_id, InboxItem)

    def get_workspace(self, workspace_id: str) -> Workspace | None:
        return self._get("workspaces", workspace_id, Workspace)

    def get_project(self, project_id: str) -> Project | None:
        return self._get("projects", project_id, Project)

    def get_memory_item(self, item_id: str) -> MemoryItem | None:
        return self._get("memory_items", item_id, MemoryItem)

    def get_user_memory_item(self, item_id: str) -> UserMemoryItem | None:
        return self._get("user_memory_items", item_id, UserMemoryItem)

    def get_chat_thread(self, thread_id: str) -> ChatThread | None:
        return self._get("chat_threads", thread_id, ChatThread)

    def get_task(self, task_id: str) -> Task | None:
        return self._get("tasks", task_id, Task)

    def get_blackboard_post(self, post_id: str) -> BlackboardPost | None:
        return self._get("blackboard_posts", post_id, BlackboardPost)

    def get_source(self, source_id: str) -> Source | None:
        return self._get("sources", source_id, Source)

    def get_agent(self, agent_id: str) -> Agent | None:
        return self._get("agents", agent_id, Agent)

    def get_document(self, document_id: str) -> DocumentRecord | None:
        return self._get("documents", document_id, DocumentRecord)

    def get_document_parse_job(self, job_id: str) -> DocumentParseJob | None:
        return self._get("document_parse_jobs", job_id, DocumentParseJob)

    def get_tool_definition(self, tool_id: str) -> ToolDefinition | None:
        return self._get("tool_definitions", tool_id, ToolDefinition)

    def get_model_definition(self, model_id: str) -> ModelDefinition | None:
        return self._get("model_definitions", model_id, ModelDefinition)

    def get_risk_policy_rule(self, rule_id: str) -> RiskPolicyRule | None:
        return self._get("risk_policy_rules", rule_id, RiskPolicyRule)

    def get_scheduled_agent_task_definition(self, definition_id: str) -> ScheduledAgentTaskDefinition | None:
        return self._get("scheduled_agent_task_definitions", definition_id, ScheduledAgentTaskDefinition)

    def get_user(self, user_id: str) -> User | None:
        return self._get("users", user_id, User)

    def get_auth_credential(self, user_id: str) -> AuthCredential | None:
        return self._get("auth_credentials", user_id, AuthCredential)

    def get_auth_session(self, session_id: str) -> AuthSession | None:
        return self._get("auth_sessions", session_id, AuthSession)

    def get_auth_session_by_token_hash(self, token_hash: str) -> AuthSession | None:
        for session in self.auth_sessions:
            if session.token_hash == token_hash:
                return session
        return None

    def get_team(self, team_id: str) -> Team | None:
        return self._get("teams", team_id, Team)

    def get_team_membership(self, membership_id: str) -> TeamMembership | None:
        return self._get("team_memberships", membership_id, TeamMembership)

    def list_teams(self, workspace_id: str | None = None) -> list[Team]:
        items = self.teams
        if workspace_id is not None:
            items = [team for team in items if team.workspace_id == workspace_id]
        return sorted(items, key=lambda item: item.created_at)

    def list_team_memberships(
        self,
        team_id: str | None = None,
        user_id: str | None = None,
    ) -> list[TeamMembership]:
        items = self.team_memberships
        if team_id is not None:
            items = [membership for membership in items if membership.team_id == team_id]
        if user_id is not None:
            items = [membership for membership in items if membership.user_id == user_id]
        return sorted(items, key=lambda item: item.created_at)

    def remove_team_membership(self, membership_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "DELETE FROM records WHERE collection = ? AND id = ?",
                ("team_memberships", membership_id),
            )
            return cursor.rowcount > 0

    def list_agent_tool_grants(self, agent_id: str) -> list[AgentToolGrant]:
        return [grant for grant in self.agent_tool_grants if grant.agent_id == agent_id]

    def list_thread_messages(self, thread_id: str) -> list[ChatMessage]:
        return [message for message in self.chat_messages if message.thread_id == thread_id]

    def list_user_memory_items(
        self,
        user_id: str,
        layer: str | None = None,
        project_id: str | None = None,
        memory_date: dt_date | None = None,
        memory_type: str | None = None,
    ) -> list[UserMemoryItem]:
        items = [item for item in self.user_memory_items if item.user_id == user_id]
        if layer is not None:
            items = [item for item in items if item.layer == layer]
        if project_id is not None:
            items = [item for item in items if item.project_id == project_id]
        if memory_date is not None:
            items = [item for item in items if item.memory_date == memory_date]
        if memory_type is not None:
            items = [item for item in items if item.memory_type == memory_type]
        return sorted(items, key=lambda item: item.created_at, reverse=True)

    def list_personal_activity(self) -> list[ActivityLog]:
        return [log for log in self.activity_logs if log.category == "personal"]

    def list_external_activity(self) -> list[ActivityLog]:
        return [log for log in self.activity_logs if log.category == "external_agent"]

    def search(
        self,
        query: str,
        allowed_scopes: set[Scope],
        workspace_id: str | None = None,
        project_id: str | None = None,
        user_id: str | None = None,
    ) -> list[SearchResult]:
        needle = query.strip().lower()
        if not needle:
            return []

        results: list[SearchResult] = []
        threads_by_id = {thread.id: thread for thread in self.chat_threads}
        tasks_by_id = {task.id: task for task in self.tasks}
        for message in self.chat_messages:
            thread = threads_by_id.get(message.thread_id)
            if (
                message.scope in allowed_scopes
                and self._thread_matches(thread, workspace_id, project_id)
                and self._matches(needle, message.content)
            ):
                results.append(
                    SearchResult(
                        id=message.id,
                        result_type="chat_message",
                        title="对话记录",
                        summary=message.content,
                        scope=message.scope,
                        sources=message.sources,
                        created_at=message.created_at,
                    )
                )

        for log in self.activity_logs:
            if (
                log.scope in allowed_scopes
                and self._project_fields_match(log.workspace_id, log.project_id, workspace_id, project_id)
                and self._matches(needle, log.title, log.summary)
            ):
                results.append(
                    SearchResult(
                        id=log.id,
                        result_type="activity_log",
                        title=log.title,
                        summary=log.summary,
                        scope=log.scope,
                        created_at=log.created_at,
                    )
                )

        for post in self.blackboard_posts:
            task = tasks_by_id.get(post.task_id)
            thread = threads_by_id.get(task.thread_id) if task else None
            if (
                post.scope in allowed_scopes
                and post.post_type == BlackboardPostType.EVIDENCE
                and self._thread_matches(thread, workspace_id, project_id)
                and self._matches(needle, post.title, post.content)
            ):
                results.append(
                    SearchResult(
                        id=post.id,
                        result_type="blackboard_evidence",
                        title=post.title,
                        summary=post.content,
                        scope=post.scope,
                        sources=post.sources,
                        created_at=post.created_at,
                    )
                )

        for item in self.memory_items:
            if (
                item.scope in allowed_scopes
                and self._project_fields_match(item.workspace_id, item.project_id, workspace_id, project_id)
                and self._matches(needle, item.title, item.summary)
            ):
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

        if Scope.PRIVATE in allowed_scopes and user_id is not None:
            for item in self.user_memory_items:
                if (
                    item.user_id == user_id
                    and self._project_fields_match(item.workspace_id, item.project_id, workspace_id, project_id)
                    and self._matches(needle, item.title, item.summary, item.memory_type)
                ):
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

            for document in self.documents:
                if (
                    document.uploaded_by == user_id
                    and self._project_fields_match(document.workspace_id, document.project_id, workspace_id, project_id)
                    and self._matches(needle, document.title, document.file_name, document.text)
                ):
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

        return sorted(results, key=lambda result: result.created_at, reverse=True)

    @staticmethod
    def _matches(needle: str, *values: str) -> bool:
        return any(needle in value.lower() for value in values)

    @staticmethod
    def _thread_matches(thread: ChatThread | None, workspace_id: str | None, project_id: str | None) -> bool:
        if thread is None:
            return workspace_id is None and project_id is None
        return SQLiteStore._project_fields_match(thread.workspace_id, thread.project_id, workspace_id, project_id)

    @staticmethod
    def _project_fields_match(
        item_workspace_id: str | None,
        item_project_id: str | None,
        workspace_id: str | None,
        project_id: str | None,
    ) -> bool:
        if workspace_id is not None and item_workspace_id != workspace_id:
            return False
        return not (project_id is not None and item_project_id != project_id)


store = SQLiteStore()
