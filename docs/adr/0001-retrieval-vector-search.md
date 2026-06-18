# ADR 0001: Retrieval Vector Search

## Status

Accepted.

## Context

AgentMesh currently retrieves from chat messages, activity logs, BBS evidence, team memory, user memory, and uploaded documents with permission-aware keyword search in the SQLite-backed store.

The remaining product risk is not vector math. It is whether the system has enough real, permissioned, source-attributed data from O2, uploaded documents, and business connectors.

## Decision

Do not add `pgvector` in the current MVP.

Keep the retrieval boundary explicit:

- Preserve `SQLiteStore.search(...)` as the current keyword implementation.
- Keep every result source-aware and permission-aware.
- Add vector search only after real documents and connector data make keyword recall insufficient.

## Triggers To Revisit

Re-open this decision when at least one of these is true:

- Uploaded and O2-backed documents exceed roughly 5,000 searchable chunks.
- Users frequently ask with wording that does not overlap source text.
- Evaluation shows citation coverage below 75% while relevant sources exist.
- Search latency or ranking quality becomes a top user complaint.

## Consequences

This avoids introducing PostgreSQL, embeddings, index migrations, and vector permission filtering before the MVP has enough real data to justify them.

The cost is that early retrieval remains lexical. That is acceptable while the product is still validating the chat workflow, memory governance, O2 integration, and production data connectors.
