# ADR 0002: Records Store To Relational Tables

## Status

Accepted as a migration plan. Not implemented in the MVP.

## Context

The current SQLite store persists every model in one `records(collection, id, payload, created_order)` table. This is simple and useful while domain models still change quickly.

The downside is predictable:

- Filtering requires loading and parsing JSON payloads.
- There are no relation-level constraints between users, tasks, posts, memory, and documents.
- Indexing by workspace, project, user, scope, status, and timestamp is limited.

## Decision

Keep the single records table for the current MVP, but migrate to relational tables after production schemas stabilize.

Use a two-phase migration:

1. Add relational tables while continuing to read/write the existing records table.
2. Backfill relational tables from records, verify parity, then switch reads table by table.

## Initial Table Set

- `workspaces`
- `projects`
- `users`
- `teams`
- `team_memberships`
- `agents`
- `tool_definitions`
- `agent_tool_grants`
- `model_definitions`
- `chat_threads`
- `chat_messages`
- `tasks`
- `blackboard_posts`
- `auto_blackboard_post_requests`
- `memory_items`
- `user_memory_items`
- `documents`
- `sources`
- `inbox_items`
- `activity_logs`
- `audit_events`
- `risk_policy_rules`
- `scheduled_agent_task_definitions`

## Index Priorities

- `users(workspace_id, role, status)`
- `projects(workspace_id, status)`
- `chat_threads(user_id, project_id, updated_at)`
- `tasks(thread_id, status, updated_at)`
- `blackboard_posts(task_id, post_type, created_at)`
- `user_memory_items(user_id, layer, project_id, memory_date, memory_type)`
- `memory_items(workspace_id, project_id, scope, status)`
- `documents(uploaded_by, workspace_id, project_id, created_at)`
- `audit_events(action, target_type, created_at)`

## Cutover Criteria

- All current tests pass against both records and relational reads.
- Backfill script reports row-count parity per collection.
- API response payloads remain unchanged.
- Permission filters move into SQL predicates without broadening visibility.

## Consequences

This avoids premature schema churn while giving the team a concrete path out of the KV table once data volume and product shape justify it.
