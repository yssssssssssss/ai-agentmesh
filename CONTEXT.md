# CONTEXT.md — Digital Twin × Agent Market

Glossary for the "digital twin / agent collaboration market" work. Each term maps to its
**code reality** as of 2026-08-09, so downstream work doesn't mistake the design doc's
aspiration for what is built. Source design: `docs/2026-08-08-数字分身-Agent协作市场-产品设计.md`.
MVP scope decisions: `docs/adr/0003-mvp-scope-answer-only-gateway.md`.

Legend: ✅ works · ⚠️ convention/partial · ❌ absent (design-only).

## 前端术语约定 / Frontend terminology

当前默认前端是 `agentmesh-demo/`：React 18 + Vite + Tailwind + TanStack Query 的
TypeScript 单页应用，由 FastAPI 从 `agentmesh-demo/dist` 同源托管。`/` 与产品
deep link 均返回 React index；业务状态和权限以 FastAPI/SQLite 为唯一真相。

项目根目录的 `app.html` 是已退役的单文件 UI，仅通过 `/legacy/app.html` 保留
一个发布周期作为回滚入口。它不再是默认入口，也不再承载新功能。完整替换设计见
`docs/superpowers/specs/2026-08-11-react-frontend-complete-replacement-design.md`。

运行边界：当前 MVP 仅支持单 Workspace、单应用进程和单 SQLite 数据库，并且只部署在可信内网。多 Workspace 租户、SQLite 多进程协调、水平扩容、高可用和公网加固均为 Post-MVP。发布前必须在具备授权凭证/CLI 的内网宿主机运行五类真实 Provider smoke；fallback 通过单元测试不等于真实 Provider 发布验收通过。

## Terms

- **数字分身 / Digital Twin (PersonalAgent)** — the single agent representing one person.
  ✅ `class PersonalAgent` `agents.py:87`; per-user `personal_agent_id` `models.py:124`,
  provisioned on signup. Currently one shared module-level instance acting *as the calling
  user*, not a per-user resident agent.

- **个人记忆 / Personal memory** — a person's private, layered memory, distinct from org
  memory. ✅ `UserMemoryItem` `models.py:441`; short/mid/long-term `MemoryLayer` `models.py:36`;
  routes `routes/memory.py`. Hard-scoped to `user_id` (`store.py:480`).

- **组织知识资产 / Org knowledge asset** — confirmed project/team memory. ✅ `MemoryItem`
  `models.py:427`, distinct store from personal memory.

- **确认闸门 / Confirmation gate** — policy-driven human confirmation before data crosses a
  boundary or writes to org memory. ✅ `RiskPolicyRule` `models.py:236` → engine `risk.py` →
  `InboxItem` `models.py:409` quarantine that halts the task (`agents.py:608`). Note: reviews
  ride on `InboxItem`; there is no separate `review_items` table.

- **溯源 / source-citation** — origin tracking on messages, posts, memory. ✅ `class Source`
  `models.py:270`, propagated through synthesis (`agents.py:653`).

- **BBS 协作市场 / Collaboration board** — where twins post signals and collaborate. ⚠️
  `blackboard.py` is a working *per-task* board (posts, task-cards, handoff, execution locks),
  **not** a signal-matching *marketplace* — no problem/need/offered-value matching algorithm.

- **数据不离境,只出答案 / Answer-only gateway** — other agents never touch raw data; they
  query a twin that returns an abstracted answer. ⚠️/❌ Visibility filtering exists as a
  *convention* (`blackboard.py:361`), but the cross-user execution path — B's twin triggers
  A's twin to answer from A's private memory — **does not exist** (`agents.py:496-497`,
  `store.py:587-592`; the only responder path `fulfill_research_request` `agents.py:769` fetches
  *external* evidence for the requester, touching no one's `UserMemoryItem`). **This is the
  MVP's single load-bearing build.** Caveat: even once built, an answer synthesized from A's
  private memory is derived data and is **not** a privacy guarantee. **Decision (2026-08-09):
  this is an internal-company project where cross-user data flow is permitted, so "只出答案"
  is a collaboration/UX pattern, not a privacy control — see ADR 0003 privacy-posture.**

- **血缘链 / memory lineage** — derived-from / cites edges between memory items. ❌ absent
  (zero code). MVP builds one `derived_from` edge as an extension of `source/citation`.

- **贡献度 / Contribution points** — points settled only when output is adopted, converted to
  employee rewards. ❌ absent (zero code). MVP does **shadow points only** (record, no
  redemption); redemption + anti-collusion is deferred.

- **会议双通道 / Meeting dual-channel** — mic=me, system-audio=others, for MVP meeting
  capture. ❌ absent from this repo — belongs to **designOS**, which is not checked in here
  (referenced only in `o2.py:21-28`). MVP replaces this entry point with pasted notes text.

## Not in this repo

- **designOS** — org-layer + meeting capture + business scenes. Referenced only; no source
  tree here.
- **PostgreSQL / EmployeeTwin fusion** — target of `docs/2026-07-10-...fusion-plan.md`.
  Current persistence is **SQLite** (`store.py:47`); Postgres/fusion are aspirational.
