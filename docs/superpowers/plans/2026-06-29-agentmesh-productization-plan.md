# AgentMesh Productization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn AgentMesh from a runnable MVP prototype into an independently productized enterprise team Agent collaboration platform.

**Architecture:** Keep the current FastAPI domain and route structure, but deepen the persistence, tenancy, auth, LLM governance, eventing, and observability modules before adding broad platform features. PostgreSQL becomes the production store, SQLite remains a local/dev adapter only. The single-file frontend is split after the production safety foundations are underway, not before.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic, PostgreSQL, SQLAlchemy/Alembic or a thin SQL adapter, pytest, ruff, server-sent events for realtime updates, Vite + React + TypeScript when the UI migration starts.

## Global Constraints

- AgentMesh is an independent product, not only a DesignOS reference module.
- Product positioning: enterprise team Agent collaboration, governed memory, source-tracked answers, and human approval workflows.
- Do not chase a generic Agent builder, workflow marketplace, or free-form autonomous multi-agent chat in the first productization phase.
- Preserve explicit `$` skills: natural chat remains private by default and must not silently create tasks, blackboard posts, or memories.
- Every shared artifact must keep actor, source, scope, permission, status, workspace/project context, and timestamp.
- Team memory must never be auto-accepted; AI output enters candidate/review flows first.
- Add pgvector only after ADR-0001 revisit triggers are met.
- Follow ADR-0002 for records-to-relational migration, but upgrade the decision from "after MVP" to "required before independent product launch".
- Keep changes incremental and testable; do not rewrite the whole stack in one branch.

---

## 1. Product Positioning

AgentMesh should be productized as:

```text
An enterprise team Agent collaboration and governance platform.
```

It should win on three things:

1. **Blackboard collaboration:** asynchronous Agent work with evidence, risk, decisions, handoff, and audit trails.
2. **Memory governance:** private, project, and team memory with source tracking and human confirmation.
3. **Enterprise safety:** workspace isolation, review workflows, risk policy, tool grants, LLM budget control, and auditability.

It should not compete head-on with Dify, Coze, CrewAI, AutoGen, or n8n as a generic visual workflow builder in the first release. That path is crowded and complexity-heavy.

## 2. Release Gates

### Gate A: Productization Alpha

Purpose: one trusted internal team can use AgentMesh without data loss, obvious auth holes, or model-cost surprises.

Required:

- PostgreSQL-backed relational tables for core entities.
- Workspace/project isolation enforced in data access.
- Production-safe auth bootstrap.
- CSRF and login rate limiting.
- LLM usage audit and budget enforcement.
- Structured logs and basic operational status.
- Current pytest suite passes.

### Gate B: Private Beta

Purpose: multiple teams can use the same deployment with controlled risk.

Required:

- SSE event stream for chat/task/blackboard/inbox updates.
- Worker state persisted and inspectable.
- Tool runs persisted and auditable.
- Frontend split out of `app.html` into maintainable files or a Vite app.
- API compatibility tests for current clients.
- Admin can invite users and manage team membership.

### Gate C: Product Launch Candidate

Purpose: product can be deployed and operated as a real enterprise app.

Required:

- PostgreSQL is the default production path.
- Data export and audit export are available.
- LLM budgets, errors, and usage are visible per workspace.
- Basic backup/restore runbook exists.
- Frontend is componentized.
- Observability covers request errors, DB errors, worker lag, LLM failures, and budget denials.

## 3. P0 Workstream: Persistence And Transactions

### Current Problem

`agentmesh/store.py` persists all entities in one SQLite `records(collection, id, payload, created_order)` table. That keeps prototypes simple but gives weak relation constraints, weak query performance, fragile filtering, and poor multi-tenant enforcement.

### Target Module

Create a production persistence module with a small stable interface:

```text
agentmesh/storage/
  __init__.py
  base.py
  sqlite_records.py
  postgres.py
  migrations/
```

The external interface should hide whether the adapter is SQLite records or PostgreSQL relational tables. Callers should stop depending on full-list properties such as `store.chat_messages` for request-time filtering.

### TODO

- [ ] Create a `Storage` protocol that names the actual access patterns used by routes and agents.
- [ ] Add PostgreSQL dependency and configuration variables:
  - `AGENTMESH_DATABASE_URL`
  - `AGENTMESH_STORAGE_BACKEND=sqlite|postgres`
- [ ] Keep SQLite records as the default local adapter until PostgreSQL tests are stable.
- [ ] Add relational tables for:
  - workspaces
  - projects
  - users
  - teams
  - team_memberships
  - auth_credentials
  - auth_sessions
  - agents
  - tool_definitions
  - agent_tool_grants
  - model_definitions
  - chat_threads
  - chat_messages
  - tasks
  - blackboard_posts
  - auto_blackboard_post_requests
  - memory_items
  - user_memory_items
  - documents
  - sources
  - inbox_items
  - activity_logs
  - audit_events
  - risk_policy_rules
  - permission_policy_rules
  - llm_usage_events
  - event_outbox
  - worker_runs
- [ ] Add indexes from ADR-0002 plus:
  - `auth_sessions(token_hash, revoked_at, expires_at)`
  - `blackboard_posts(workspace_id, project_id, task_id, created_at)`
  - `inbox_items(workspace_id, assigned_to, status, snooze_until)`
  - `llm_usage_events(workspace_id, user_id, created_at)`
  - `event_outbox(workspace_id, created_at, delivered_at)`
- [ ] Implement dual-write for core entities behind a feature flag:
  - users
  - workspaces
  - projects
  - chat_threads
  - chat_messages
  - tasks
  - blackboard_posts
  - memory_items
  - inbox_items
  - audit_events
- [ ] Write a backfill script from SQLite records to PostgreSQL.
- [ ] Write a parity checker that reports count and sampled payload mismatches by collection/table.
- [ ] Switch reads table by table only after parity passes.
- [ ] Add transaction methods for multi-write workflows:
  - chat message + task + blackboard request + activity log
  - inbox update + audit event
  - memory acceptance + audit event
  - tool grant update + audit event
- [ ] Add optimistic update checks where user actions depend on current state.

### Tests

- [ ] Unit-test each adapter against the same storage contract test suite.
- [ ] Add migration tests for representative records from every collection.
- [ ] Add transaction tests that force an exception after the first write and assert no partial workflow is committed.
- [ ] Add workspace isolation tests at the storage level, not only the route level.

### Acceptance

- [ ] Current pytest suite passes with SQLite records.
- [ ] Core test subset passes with PostgreSQL.
- [ ] Backfill reports parity for all seeded data.
- [ ] Permission filters are implemented as storage predicates for PostgreSQL reads.
- [ ] No request path lists all rows and filters in Python for high-volume entities.

## 4. P0 Workstream: Workspace Isolation And Permission Locality

### Current Problem

Workspace and project exist as model fields, but the global store makes it easy for callers to read all records and filter late. That is a data leak waiting to happen.

### Target Module

Create one authorization seam:

```text
agentmesh/access.py
```

Routes should ask access functions for authorized workspace/project scopes. Storage queries should receive those scopes and enforce them in SQL.

### TODO

- [ ] Define `AccessContext` with:
  - user id
  - role
  - workspace ids
  - team ids
  - allowed project ids
- [ ] Build `AccessContext` once per request from session and membership data.
- [ ] Replace ad hoc role checks with named actions:
  - `read_project`
  - `write_project`
  - `manage_workspace`
  - `manage_users`
  - `manage_public_agent`
  - `accept_team_memory`
  - `run_tool`
  - `manage_tool_grants`
  - `view_audit`
- [ ] Ensure every list route requires an access context.
- [ ] Ensure every mutation verifies the target entity belongs to the caller's workspace.
- [ ] Add audit events for denied high-risk attempts.
- [ ] Make cross-workspace reads impossible in storage contract methods.

### Tests

- [ ] Add tests where two workspaces have similarly named projects and users.
- [ ] Assert user A cannot search, list, read, update, or accept memory from workspace B.
- [ ] Assert admin permissions are workspace-scoped unless explicitly global.
- [ ] Assert disabled users cannot continue existing sessions.

### Acceptance

- [ ] Every route that returns persisted records has an access test.
- [ ] Storage methods require workspace/project predicates for tenant data.
- [ ] A code search for broad list/filter patterns is reviewed and either removed or justified.

## 5. P0 Workstream: Production Auth

### Current Problem

The local auth layer is good enough for a prototype. It lacks CSRF protection, rate limiting, production-safe admin bootstrap, invitation flow, and strong separation between demo seed data and production data.

### Target Module

Create explicit modules:

```text
agentmesh/auth.py
agentmesh/routes/auth.py
agentmesh/security.py
agentmesh/routes/invitations.py
```

Keep the current cookie session model unless a real SSO rollout requires otherwise.

### TODO

- [ ] Add `AGENTMESH_ENV=development|production`.
- [ ] In production, refuse to start if default demo accounts are enabled.
- [ ] Add `AGENTMESH_BOOTSTRAP_ADMIN_EMAIL` or a one-time bootstrap command.
- [ ] Add invitation tokens:
  - token hash stored server-side
  - workspace id
  - role
  - expiry
  - accepted_at
- [ ] Add CSRF token cookie plus `X-AgentMesh-CSRF` header for unsafe methods.
- [ ] Exempt only login and OAuth callback where appropriate.
- [ ] Add login rate limiting by IP and user id.
- [ ] Add password policy:
  - minimum length 12 in production
  - reject known demo passwords in production
- [ ] Add session list and revoke-all-sessions endpoint for current user.
- [ ] Add audit events:
  - login success
  - login failure threshold
  - logout
  - password change
  - invite created
  - invite accepted
  - session revoked

### Tests

- [ ] Login rate limit returns 429 after configured threshold.
- [ ] Unsafe POST/PATCH/DELETE without CSRF header returns 403.
- [ ] Production startup fails with demo seed accounts enabled.
- [ ] Invitation token can be used once and expires.
- [ ] Session revoke invalidates existing cookies.

### Acceptance

- [ ] No production environment can accidentally expose seeded demo credentials.
- [ ] Browser cookie session has CSRF defense.
- [ ] Auth failures are visible in audit logs without leaking password details.

## 6. P0 Workstream: LLM Cost, Concurrency, And Circuit Breakers

### Current Problem

LLM calls have timeouts and fallback, but no usage accounting, budgets, per-workspace limits, concurrency control, or circuit breaker. That can create cost spikes and cascading failures.

### Target Module

Create:

```text
agentmesh/llm_governance.py
agentmesh/routes/llm_usage.py
```

LLM clients should be called through this module, not directly from workflows.

### TODO

- [ ] Add `LLMUsageEvent` model/table:
  - workspace_id
  - project_id
  - user_id
  - agent_id
  - model_id
  - operation
  - prompt_chars
  - response_chars
  - estimated_tokens
  - estimated_cost
  - status
  - fallback_reason
  - latency_ms
  - created_at
- [ ] Add configurable budgets:
  - per workspace daily call count
  - per workspace daily estimated token count
  - per user daily call count
  - per operation max prompt chars
- [ ] Add process-local semaphores for concurrent calls by workspace and global deployment.
- [ ] Add circuit breaker by model id:
  - opens after repeated timeout/http errors
  - returns deterministic fallback while open
  - half-open after cooldown
- [ ] Add admin endpoint for workspace usage.
- [ ] Add UI surface in admin/system panel.
- [ ] Include budget denial and circuit breaker reason in workflow trace.

### Tests

- [ ] Budget exceeded blocks LLM call and returns fallback.
- [ ] Failed model calls increment circuit breaker state.
- [ ] Open circuit breaker prevents downstream HTTP call.
- [ ] Usage event is written for success, timeout, budget denial, and fallback.
- [ ] Long user prompt is truncated or rejected before model call.

### Acceptance

- [ ] A bad model endpoint cannot stall the whole app.
- [ ] An individual workspace cannot burn unlimited calls.
- [ ] Admin can answer "who spent how much today" at least approximately.

## 7. P0 Workstream: Observability And Error Discipline

### Current Problem

There are defensive `except Exception` blocks and status dictionaries, but no consistent structured logging, error counters, or operational view beyond basic health endpoints.

### Target Module

Create:

```text
agentmesh/observability.py
agentmesh/routes/ops.py
```

Do not introduce a full tracing stack first. Start with logs, counters, and explicit status endpoints.

### TODO

- [ ] Configure JSON structured logs.
- [ ] Add request id middleware.
- [ ] Add request log middleware with:
  - request id
  - method
  - path
  - status code
  - latency
  - user id when available
  - workspace id when available
- [ ] Replace silent broad exceptions with one of:
  - logged fallback
  - explicit retryable error
  - explicit user-facing error
  - re-raised exception handled by route middleware
- [ ] Add process counters:
  - request count
  - error count
  - DB error count
  - LLM timeout count
  - budget denial count
  - worker error count
  - queue depth by worker type
- [ ] Add `/api/ops/status` for admins.
- [ ] Add `/api/ops/metrics` as plain text or JSON.
- [ ] Add health checks for:
  - DB connectivity
  - storage backend
  - worker status
  - configured model status

### Tests

- [ ] Middleware attaches request id.
- [ ] Failed route increments error counter.
- [ ] Worker exception is logged and visible in ops status.
- [ ] Ops endpoints require admin role.

### Acceptance

- [ ] Operators can see if DB, workers, and LLM calls are healthy.
- [ ] No broad exception silently disappears without a log or status field.

## 8. P1 Workstream: Realtime Event Stream

### Current Problem

The frontend depends on refresh or polling. A chat-first Agent product needs visible progress for tasks, blackboard evidence, inbox items, and worker updates.

### Target Module

Start with SSE:

```text
agentmesh/events.py
agentmesh/routes/events.py
```

SSE is simpler than WebSocket and fits server-to-client updates.

### TODO

- [ ] Add `event_outbox` table.
- [ ] Write events when these happen:
  - chat message created
  - task status changed
  - blackboard post created
  - inbox item created/updated
  - memory candidate created/accepted
  - tool run status changed
  - worker error
- [ ] Add authenticated `GET /api/events/stream`.
- [ ] Support `Last-Event-ID`.
- [ ] Filter events by access context.
- [ ] Add frontend event client.
- [ ] Replace key manual refresh points with event-driven updates.

### Tests

- [ ] User receives only workspace-authorized events.
- [ ] `Last-Event-ID` replays missed events.
- [ ] Event stream closes on invalid session.

### Acceptance

- [ ] Chat/task/BBS/Inbox updates appear without manual refresh.
- [ ] Refresh still works as a fallback.

## 9. P1 Workstream: Worker Durability

### Current Problem

Worker state is mostly process memory. Restarts erase runtime status and can leave queued work ambiguous.

### Target Module

Create:

```text
agentmesh/workers/
  __init__.py
  auto_posts.py
  daily_memory.py
  research_dispatch.py
  leases.py
```

### TODO

- [ ] Add `worker_runs` table.
- [ ] Add queue item leases with:
  - leased_by
  - leased_until
  - attempts
  - last_error
- [ ] Make auto-post drain idempotent.
- [ ] Make daily memory summary idempotent by user/project/date.
- [ ] Make research dispatch idempotent by blackboard post/request id.
- [ ] Add manual retry endpoint.
- [ ] Add admin worker status page.

### Tests

- [ ] Restart simulation does not duplicate completed worker output.
- [ ] Expired lease can be picked up by another worker.
- [ ] Failed job records last error and attempt count.

### Acceptance

- [ ] A service restart does not lose worker state.
- [ ] Operators can inspect stuck jobs.

## 10. P1 Workstream: Tool Runs And Approval

### Current Problem

Tools are registered and granted, but productized tools need durable execution records, approval state, inputs, outputs, risk, and source links.

### Target Module

Create:

```text
agentmesh/tool_runs.py
agentmesh/routes/tool_runs.py
```

### TODO

- [ ] Add `tool_runs` table:
  - workspace_id
  - project_id
  - user_id
  - agent_id
  - tool_id
  - status
  - input_payload
  - output_payload
  - risk_decision
  - approval_inbox_item_id
  - started_at
  - completed_at
  - failed_at
- [ ] Require explicit tool grants before run.
- [ ] Run risk policy before high-risk tools.
- [ ] Create Inbox item when approval is required.
- [ ] Store normalized output as Source where appropriate.
- [ ] Add UI list/detail for tool runs.

### Tests

- [ ] Ungranted tool run is rejected.
- [ ] High-risk tool creates Inbox approval instead of executing.
- [ ] Approved tool run creates audit event and source.

### Acceptance

- [ ] Every tool execution is explainable after the fact.

## 11. P1 Workstream: Frontend Engineering

### Current Problem

`app.html` is around 6,700 lines. It blocks parallel frontend work and makes regressions hard to review.

### Target

Do not mix this with the PostgreSQL cutover in the same branch. Use a bridge phase first.

### Phase 1: Split Static Assets

- [ ] Move CSS to `static/app.css`.
- [ ] Move JavaScript to `static/app.js`.
- [ ] Keep HTML shell minimal.
- [ ] Preserve all existing API calls.
- [ ] Add smoke test for app shell load.

### Phase 2: Vite React Migration

- [ ] Add `frontend/` Vite + React + TypeScript app.
- [ ] Add API client module.
- [ ] Add auth store.
- [ ] Add routes:
  - Chat
  - Blackboard
  - Inbox
  - Memory
  - Agents
  - Users
  - Audit/Ops
- [ ] Migrate one page at a time behind a route flag.
- [ ] Remove `app.html` only after feature parity.

### Tests

- [ ] Add typecheck.
- [ ] Add frontend build.
- [ ] Add route smoke tests.
- [ ] Add API client contract tests for major endpoints.

### Acceptance

- [ ] New UI work no longer requires editing a 6,000+ line file.
- [ ] Existing product flows remain available during migration.

## 12. P2 Workstream: Retrieval And Knowledge Quality

### TODO

- [ ] Build a retrieval evaluation fixture with real uploaded documents and O2-backed sources.
- [ ] Track citation coverage by query type.
- [ ] Track "relevant source existed but answer missed it".
- [ ] Revisit pgvector only when ADR-0001 triggers are met.
- [ ] Add source quality states:
  - trusted_internal
  - uploaded_by_user
  - external_untrusted
  - needs_review
  - blocked

### Acceptance

- [ ] Retrieval improvements are driven by measured misses, not guesswork.

## 13. P2 Workstream: API Versioning And Compatibility

### TODO

- [ ] Add `/api/v1` prefix for new production endpoints.
- [ ] Keep existing `/api` aliases during transition.
- [ ] Add response schema snapshot tests for key endpoints.
- [ ] Document deprecation policy.

### Acceptance

- [ ] Frontend and external clients have a stable migration path.

## 14. P2 Workstream: Workflow Configuration

### Constraint

Do not build a visual workflow editor yet.

### TODO

- [ ] Extract built-in workflows into simple declarative Python/JSON definitions.
- [ ] Support admin-visible workflow config read-only first.
- [ ] Add enable/disable per workflow.
- [ ] Add tests that workflow definitions map to expected task and blackboard actions.

### Acceptance

- [ ] Product team can reason about workflows without editing a giant branch function.

## 15. Explicit Non-Goals For The Next 90 Days

- [ ] No generic visual Agent builder.
- [ ] No plugin marketplace.
- [ ] No cross-workspace Agent federation.
- [ ] No automatic private activity sharing.
- [ ] No team memory auto-accept.
- [ ] No free-form Agent-to-Agent chat.
- [ ] No pgvector unless ADR-0001 triggers are met.
- [ ] No frontend framework rewrite in the same branch as storage cutover.
- [ ] No broad ABAC policy language before RBAC and workspace isolation are solid.

## 16. 90-Day Execution Roadmap

### Weeks 1-2: Production Safety Foundations

- [ ] Implement PostgreSQL configuration and storage contract.
- [ ] Add first relational tables and migration runner.
- [ ] Add CSRF and login rate limiting.
- [ ] Add production seed guard.
- [ ] Add LLM usage event model and budget checks.
- [ ] Add structured request logs.

### Weeks 3-4: Core Data Cutover

- [ ] Dual-write core entities.
- [ ] Backfill SQLite records to PostgreSQL.
- [ ] Add parity checker.
- [ ] Switch reads for users, workspaces, projects, sessions, and chat.
- [ ] Add workspace isolation tests.

### Weeks 5-6: Collaboration Durability

- [ ] Switch tasks and blackboard reads to PostgreSQL.
- [ ] Add transaction wrappers for chat skill workflows.
- [ ] Add event outbox.
- [ ] Add SSE stream.
- [ ] Add persistent worker leases.

### Weeks 7-8: Governance And Tooling

- [ ] Switch memory, inbox, sources, documents, and audit reads to PostgreSQL.
- [ ] Add tool_runs.
- [ ] Add tool approval flow.
- [ ] Add admin ops status.
- [ ] Add LLM usage admin view.

### Weeks 9-10: Frontend Maintainability

- [ ] Split `app.html` into HTML/CSS/JS.
- [ ] Start Vite React app scaffold.
- [ ] Migrate Chat page or Ops page first.
- [ ] Add frontend build/typecheck.

### Weeks 11-12: Private Beta Hardening

- [ ] Run full test suite on SQLite and PostgreSQL backends.
- [ ] Run load-ish smoke for chat, BBS, memory, and LLM budget denial.
- [ ] Write backup/restore runbook.
- [ ] Write deployment checklist.
- [ ] Run 3-5 user private beta and log findings.

## 17. Immediate Issue Backlog

### Issue 1: Create Storage Contract And PostgreSQL Skeleton

**Files:**

- Create: `agentmesh/storage/base.py`
- Create: `agentmesh/storage/sqlite_records.py`
- Create: `agentmesh/storage/postgres.py`
- Create: `agentmesh/storage/migrations/0001_initial.sql`
- Modify: `agentmesh/store.py`
- Test: `tests/test_storage_contract.py`

**Deliverable:** The app can select `sqlite` or `postgres` backend by env, with SQLite preserving current behavior and PostgreSQL supporting at least workspaces, projects, users, and auth sessions.

### Issue 2: Enforce Workspace Isolation At Storage Interface

**Files:**

- Create: `agentmesh/access.py`
- Modify: `agentmesh/routes/deps.py`
- Modify: `agentmesh/routes/workspace.py`
- Modify: `agentmesh/routes/chat.py`
- Test: `tests/test_workspace_isolation.py`

**Deliverable:** Cross-workspace list/read/search attempts fail in tests.

### Issue 3: Add CSRF And Login Rate Limit

**Files:**

- Create: `agentmesh/security.py`
- Modify: `agentmesh/app.py`
- Modify: `agentmesh/auth.py`
- Modify: `agentmesh/routes/auth.py`
- Test: `tests/test_security.py`

**Deliverable:** Unsafe browser requests require CSRF token and repeated failed login returns 429.

### Issue 4: Add LLM Usage Budget

**Files:**

- Create: `agentmesh/llm_governance.py`
- Modify: `agentmesh/llm.py`
- Modify: `agentmesh/synthesis.py`
- Create: `agentmesh/routes/llm_usage.py`
- Test: `tests/test_llm_governance.py`

**Deliverable:** Budget denial produces deterministic fallback and a usage event.

### Issue 5: Add Structured Logs And Ops Status

**Files:**

- Create: `agentmesh/observability.py`
- Create: `agentmesh/routes/ops.py`
- Modify: `agentmesh/app.py`
- Test: `tests/test_ops.py`

**Deliverable:** Admin can inspect DB/model/worker health and request failures are logged with request id.

### Issue 6: Add SSE Event Stream

**Files:**

- Create: `agentmesh/events.py`
- Create: `agentmesh/routes/events.py`
- Modify: `agentmesh/app.py`
- Modify: `agentmesh/routes/chat.py`
- Modify: `agentmesh/routes/blackboard.py`
- Test: `tests/test_events.py`

**Deliverable:** Authorized users receive chat/task/blackboard/inbox events without polling.

### Issue 7: Make Workers Durable

**Files:**

- Create: `agentmesh/workers/leases.py`
- Create: `agentmesh/workers/auto_posts.py`
- Create: `agentmesh/workers/daily_memory.py`
- Create: `agentmesh/workers/research_dispatch.py`
- Modify: `agentmesh/routes/blackboard.py`
- Modify: `agentmesh/routes/memory.py`
- Test: `tests/test_workers.py`

**Deliverable:** Worker leases survive restart and failed work is inspectable/retryable.

### Issue 8: Split Static Frontend

**Files:**

- Modify: `app.html`
- Create: `static/app.css`
- Create: `static/app.js`
- Test: `tests/test_static_app.py`

**Deliverable:** Current UI still loads, but CSS and JS are no longer embedded in one huge HTML file.

## 18. Verification Commands

Run these after each task unless the task explicitly narrows the check:

```bash
.venv/bin/python -m pytest
.venv/bin/ruff check .
```

For server smoke:

```bash
.venv/bin/uvicorn agentmesh.app:app --reload --port 8010
curl http://127.0.0.1:8010/api/health
```

For PostgreSQL tasks, add:

```bash
AGENTMESH_STORAGE_BACKEND=postgres AGENTMESH_DATABASE_URL=postgresql://... .venv/bin/python -m pytest tests/test_storage_contract.py
```

## 19. Open Decisions

- [ ] Use SQLAlchemy + Alembic, or keep a thin SQL adapter with plain migrations?
- [ ] Should production require PostgreSQL immediately, or allow SQLite WAL for single-team self-hosted deployments?
- [ ] Is SSO required for the first independent customer, or is invitation-based local auth acceptable?
- [ ] Which frontend migration path is preferred: static split first, then React, or direct Vite migration?
- [ ] What is the first paid/real deployment shape: single tenant per deployment, or true multi-tenant shared deployment?

## 20. Recommended First Move

Start with **Issue 1: Create Storage Contract And PostgreSQL Skeleton**.

Reason: nearly every serious productization problem depends on persistence locality. Auth, tenancy, worker durability, LLM usage, events, and audit all become cleaner once core reads and writes go through a real storage interface instead of a global records table.
