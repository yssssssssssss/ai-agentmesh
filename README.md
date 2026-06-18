# AgentMesh

Chat-first team agent platform prototype.

## Current Slice

The first implementation slice proves:

1. A user sends a chat message.
2. The backend stores the message.
3. A personal Agent classifies intent.
4. The backend creates a task.
5. The task creates an internal blackboard request.
6. A mock research Agent returns evidence.
7. The chat response includes a source.
8. Activity logs record what the personal Agent and external Agent did.
9. The workspace can search chat, activity, blackboard evidence, and memory items with source-aware results.
10. The UI loads workspace, project, user, Agent, and live metric context from the backend.
11. Chat sessions persist as project-bound threads and the UI reuses the active thread for follow-up messages.
12. Search results are filtered by the current workspace and project context.
13. Search supports permission-aware visibility modes: `personal`, `project`, and `team`.
14. Memory review uses explicit states, and accepting a memory promotes it to team scope.
15. `risk_agent` creates policy-backed risk posts and routes human confirmations to Inbox.
16. Chat answers can be synthesized by an OpenAI-compatible LLM when a configured model is selected.
17. External research is behind an acquisition Agent interface, so the crawler/search implementation can be supplied by another project.
18. The API now has a minimal cookie session auth layer, local user lifecycle APIs, and role checks for personal Agent edits and team-memory acceptance.
19. System tools are registered in the backend and explicitly granted to Agents; tools are not automatically exposed to every personal Agent.
20. Text, Markdown, PDF, Word, slide, and image files can be uploaded, parsed, stored, and surfaced as Sources.
21. Workspace/project APIs persist records in SQLite and allow admins to create new workspaces and projects.
22. Blackboard supports agent/system-created posts, read markers, replies, pagination, and a queued auto-post drain path.
23. Risk review uses persisted policy rules for prompt-injection, source policy, approval, and high-risk tool signals; admins can manage rules from the Members page.
24. `data_agent` has a connector registry with a local metrics connector and can answer chat-triggered metric queries.
25. `research_agent` can use a Web acquisition provider when `AGENTMESH_WEB_PROVIDER` is configured.

## Run Locally

Set up an isolated environment:

```bash
/opt/homebrew/bin/python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
```

Start the app:

```bash
.venv/bin/uvicorn agentmesh.app:app --reload --port 8010
```

Port `8000` is intentionally avoided because it may already be used by another local backend.

Open:

```text
http://127.0.0.1:8010/app.html
```

The app UI shows a local login panel when no session exists. Use the seeded development accounts below.

Development accounts:

```text
usr_current_designer / designer123
usr_team_lead / lead123
usr_admin / admin123
```

## Test

```bash
.venv/bin/python -m pytest
```

Tests use an isolated SQLite database under the system temp directory, so they do not clear `data/agentmesh.sqlite3`.
The pytest bootstrap also clears default LLM environment variables so unit tests stay deterministic and do not call the real model service unless a test explicitly configures a mocked model endpoint.

## Local Data

The prototype uses SQLite by default:

```text
data/agentmesh.sqlite3
```

Override it with:

```bash
AGENTMESH_DB_PATH=/path/to/agentmesh.sqlite3 .venv/bin/uvicorn agentmesh.app:app --port 8010
```

## Auth and Permissions

AgentMesh uses a minimal local auth and user-management layer for the current MVP slice:

- `POST /api/auth/login` creates an HttpOnly cookie session.
- `POST /api/auth/logout` revokes the session.
- `GET /api/auth/me` returns the current user.
- `POST /api/auth/password` lets the current user rotate their password and revokes existing sessions.
- Users are seeded into SQLite on startup if missing.
- Admins can create local users with initial passwords.
- Admins can reset local user passwords and revoke existing sessions.
- Creating a local user also creates that user's personal Agent.
- Admins can disable users; disabled users cannot log in or continue an existing session.
- Regular users can manage only their own personal Agent.
- Team leads and admins can accept candidate memories into team scope.
- Admins can manage public Agents.
- Admins can create workspaces and projects.

This is intentionally not an enterprise identity implementation yet. OAuth, SSO, and organization provisioning are reserved for later slices.

## Agents and Tools

Public Agents are registered by backend code first, then exposed through API:

- `GET /api/agents/public`
- `GET /api/tools`
- `GET /api/agents/{agent_id}/tools`
- `PATCH /api/agents/{agent_id}/tools`

Tools are explicitly granted to Agents. Some tools now have MVP execution paths (`document_upload`, local data queries, risk rules, and configurable web research), but web research still requires a provider to be configured.

## Oxygen-CLI Internal Provider

Oxygen-CLI is treated as an internal company capability provider, not the only data source. AgentMesh keeps external Web providers, uploaded documents, local memory, and future BI/database connectors as separate sources.

Status and tool discovery APIs:

- `GET /api/integrations/o2/status`
- `POST /api/integrations/o2/sync` admin only

The sync endpoint reads Oxygen registry metadata and stores discovered CLI capabilities as `ToolDefinition` records with `provider=o2`. It does not automatically grant those tools to every Agent; existing Agent tool grants still apply.

Enable Oxygen-backed internal research:

```bash
export AGENTMESH_O2_RESEARCH_ENABLED=true
export AGENTMESH_O2_RESEARCH_CLI=metasearch
```

Enable Oxygen-backed data queries:

```bash
export AGENTMESH_O2_DATA_ENABLED=true
export AGENTMESH_O2_DATA_CLI=metasearch
```

Built-in Oxygen command contracts:

- Research through `metasearch`: `o2 launch metasearch --json search <query> --token-env JD_METASEARCH_ACCESS_TOKEN --output json`
- Research through `o2-kb`: `o2 launch o2-kb recall list <query> --json`, with optional `AGENTMESH_O2_KB_RECALL_TOKEN` and `AGENTMESH_O2_KB_FOLDER_TO_APP`.
- Data through `metasearch`: same read-only search contract as research.
- Data through `oxygen-comment`: `o2 launch oxygen-comment --json [--dry-run] comment list --page-size <limit> ...`
- Data through `bdp-copilot`: `o2 launch bdp-copilot --json-output find-tables <query>`

If an approved CLI uses a different shape, override it with:

```bash
export AGENTMESH_O2_RESEARCH_COMMAND_TEMPLATE='launch {cli} search {query} --limit {limit} --json'
export AGENTMESH_O2_DATA_COMMAND_TEMPLATE='launch {cli} {operation} {query} --limit {limit} --json'
```

The Oxygen data connector is read-only in this slice. Write actions such as upload, edit, delete, install, and batch operations should be routed through Inbox/Risk review before execution.

Known runtime prerequisites:

- `metasearch` needs `JD_METASEARCH_ACCESS_TOKEN`.
- `o2-kb` must be initialized by `o2-kb init` before its config commands work.
- `webcli`/browser-backed CLIs need the Browser Bridge daemon and extension connected.
- `bdp-copilot` execution still depends on the user's internal runtime and auth context.

## LLM Configuration

AgentMesh reads model services from environment variables. The legacy single-model configuration still works as the `default` model:

```bash
export AI_API_URL=https://modelservice.jdcloud.com/v1/responses
export AI_MODEL=Gemini-3-Flash-Preview
export AI_API_KEY=your-api-key
```

If you prefer the older chat-completions layout, keep using:

```bash
export AGENTMESH_LLM_BASE_URL=https://modelservice.jdcloud.com/v1/
export AGENTMESH_LLM_MODEL=GPT-5.5
export AGENTMESH_LLM_API_KEY=your-api-key
.venv/bin/uvicorn agentmesh.app:app --port 8010
```

Additional selectable models use `AGENTMESH_MODELS` plus per-model variables:

```bash
export AGENTMESH_MODELS=gpt55,fast
export AGENTMESH_MODEL_DEFAULT=gpt55
export AGENTMESH_MODEL_GPT55_BASE_URL=https://modelservice.jdcloud.com/v1/
export AGENTMESH_MODEL_GPT55_MODEL=GPT-5.5
export AGENTMESH_MODEL_GPT55_LABEL="GPT-5.5 高"
export AGENTMESH_MODEL_GPT55_API_KEY=your-api-key
```

The UI stores only `model_id` on the Agent. API keys stay server-side and are never returned by `/api/models`. If a selected model is missing or the model call fails, AgentMesh falls back to the deterministic local response.

## Acquisition Agent Boundary

AgentMesh keeps external acquisition as an interface boundary:

- `AcquisitionRequest` describes what the personal Agent needs.
- `AcquisitionResult` returns evidence, sources, actor, permission, and metadata.
- `MockAcquisitionAgent` keeps the default local flow working.
- `WebAcquisitionAgent` can call a configured Web provider.
- `ExternalAcquisitionConnector` remains a placeholder for an implementation supplied by another project.
- External content is treated as untrusted input. Suspicious prompt-injection text is saved for audit, marked `needs_review`, routed to Inbox, and excluded from LLM synthesis.
- High-risk tool requests such as batch crawling, batch downloads, intranet access, or automatic team-memory writes are routed to Inbox for approval before any acquisition connector runs.

To enable command-backed Web research:

```bash
export AGENTMESH_WEB_PROVIDER=opencli
export AGENTMESH_OPENCLI_COMMAND=opencli
export AGENTMESH_OPENCLI_COMMAND_TEMPLATE='opencli search {query} --limit {limit} --json'
```

or:

```bash
export AGENTMESH_WEB_PROVIDER=agent_browser
export AGENTMESH_AGENT_BROWSER_COMMAND=agent-browser
export AGENTMESH_AGENT_BROWSER_COMMAND_TEMPLATE='agent-browser search {query} --limit {limit} --json'
```

Without a command template, the provider runs `COMMAND query --limit N --json`. Templates support `{query}` and `{limit}` placeholders. The command should return JSON as an array, or an object with `items`, `results`, or `data`, containing `title`/`name`, `url`/`href`/`link`, and `snippet`/`content`/`summary`.

## Document Ingestion Boundary

Document ingestion is also kept as a thin boundary:

- `DocumentIngestionRequest` carries file metadata, bytes, workspace, project, and uploader.
- `ParsedDocument` returns normalized text plus a document `Source`.
- `CompositeDocumentParser` routes `.txt`, `.md`, `.markdown`, `.pdf`, `.docx`, `.pptx`, and common image files to built-in parsers.
- PDF parsing uses PyMuPDF when available through the project dependencies.
- Word and slide parsing extract OOXML text from `.docx` and `.pptx`.
- Image OCR uses a configured `tesseract` command; without that runtime, image uploads fail with an explicit parser error.
- `POST /api/documents/upload` stores parsed documents, creates Sources, and writes a short-term document-summary memory item.
- Files larger than the sync threshold are parsed through a `DocumentParseJob` background task and can be checked with `/api/documents/jobs/{job_id}`.
- `ExternalDocumentParserConnector` remains only as an extension boundary for future richer parsers, not as the default path for the file types above.

## Data Source Connector Boundary

Data source integration is reserved as a generic connector contract:

- `DataSourceQuery` carries connector name, operation, free-form parameters, workspace, project, and requester.
- `DataSourceResult` returns generic records plus a `data_source` Source.
- `DataSourceRegistry` routes queries to registered connectors.
- `http_data_api` is a production-facing read-only HTTP connector enabled by `AGENTMESH_DATA_API_URL`.
- `data_agent` tries configured production data connectors before falling back to O2 and `local_metrics`.
- `local_metrics` is a working local connector used by `POST /api/data-agent/query`.
- `ExternalDataSourceConnector` is a placeholder until a concrete external project provides the real data shape and access method.

Enable a real read-only data API:

```bash
export AGENTMESH_DATA_API_URL=https://your-company-data-api.example/api/data
export AGENTMESH_DATA_API_KEY=your-server-side-token
```

For a query operation such as `query`, AgentMesh POSTs to:

```text
{AGENTMESH_DATA_API_URL}/query
```

with JSON containing `operation`, `parameters`, `workspace_id`, `project_id`, and `requested_by`. The response may be an array, or an object with `records`, `items`, `results`, `data`, or `rows`. API keys stay server-side and are not returned by health or connector list endpoints.

## Workspace And Blackboard

Workspace and project records are persisted through the same SQLite store as the rest of the prototype:

- `GET /api/workspaces`
- `POST /api/workspaces` admin only
- `GET /api/projects`
- `POST /api/projects` admin only

Blackboard also has an auto-post queue for Agent background jobs:

- `GET /api/blackboard/auto-posts`
- `POST /api/blackboard/auto-posts`
- `POST /api/blackboard/auto-posts/drain`
- `GET /api/blackboard/auto-posts/worker`

Auto-post requests must be reviewed before drain publishes them into the BBS. A background worker is available but disabled by default; enable it with `AGENTMESH_AUTO_POST_WORKER_ENABLED=true` and configure the interval with `AGENTMESH_AUTO_POST_WORKER_INTERVAL_SECONDS`.

User memory daily summaries also have a disabled-by-default worker. Enable it with `AGENTMESH_DAILY_MEMORY_WORKER_ENABLED=true` and configure the interval with `AGENTMESH_DAILY_MEMORY_WORKER_INTERVAL_SECONDS`. The worker only creates one `daily_summary` per active user/project/date and skips users without short-term source memory.

Project memory summaries use the configured LLM when available, then fall back to deterministic source rollups if the model is unavailable.
Project archives now include a recall-index section, and personal search can resolve the current user's layered memory items.
Uploaded documents are indexed for personal search, written to short-term document-summary memory, and can be used as chat evidence for relevant Brief/research requests.

## API Snapshot

- `POST /api/chat/messages`
- `POST /api/chat/threads`
- `GET /api/bootstrap`
- `GET /api/activity/today`
- `GET /api/audit?limit=50&action=...&target_type=...`
- `GET /api/inbox`
- `PATCH /api/inbox/{id}` with `status=open|snoozed|resolved`, optional `ttl_minutes`, or optional `snooze_until`
- `GET /api/memory`
- `GET /api/memory/user?layer=short_term|mid_term|long_term&project_id=...&memory_date=YYYY-MM-DD&memory_type=...`
- `POST /api/memory/user`
- `POST /api/memory/user/daily-summary`
- `POST /api/memory/user/group-summary`
- `POST /api/memory/user/daily-summary/run`
- `GET /api/memory/user/daily-summary/worker`
- `POST /api/memory/user/project-summary`
- `POST /api/memory/user/archive-project`
- `GET /api/users`
- `POST /api/users`
- `PATCH /api/users/{id}`
- `GET /api/search?q=关键词&workspace_id=...&project_id=...&visibility=personal`
- `GET /api/agents` with derived runtime status and current task fields
- `GET /api/blackboard`
- `GET /api/blackboard/task-cards`
- `POST /api/blackboard/posts`
- `PATCH /api/blackboard/posts/{id}/read`
- `POST /api/blackboard/posts/{id}/reply`
- `POST /api/blackboard/posts/{id}/handoff`
- `GET /api/blackboard/auto-posts`
- `POST /api/blackboard/auto-posts`
- `POST /api/blackboard/auto-posts/drain`
- `GET /api/blackboard/auto-posts/worker`
- `GET /api/workspaces`
- `POST /api/workspaces`
- `GET /api/projects`
- `POST /api/projects`
- `POST /api/auth/password`
- `POST /api/users/{id}/password`
- `POST /api/documents/upload`
- `GET /api/documents`
- `GET /api/data-sources`
- `POST /api/data-agent/query`
- `GET /api/integrations/o2/status`
- `POST /api/integrations/o2/sync`
- `GET /api/risk/policies`
- `POST /api/risk/policies`
- `PATCH /api/risk/policies/{id}`
