# ADR 0003: MVP Scope — Answer-Only Cross-Person Gateway Is The Load-Bearing Build

## Status

Accepted as MVP scope. Derived from a grilling review (2026-08-09) of
`docs/2026-08-08-数字分身-Agent协作市场-产品设计.md` against the current codebase.

## Context

The product design doc proposes a "digital twin × agent collaboration market". A
feasibility review was scoped (decision Q1) to **only the Section 7 MVP loop**, not
the three-year vision. The MVP loop is:

```
① 一场会议(双通道认"我") → ② 分身沉淀个人记忆 → ③ 提炼信号+确认后发 BBS
→ ④ 别人分身提问,数据不离境只回答案 → ⑤ 采纳/沉淀组织(过闸门)
→ ⑥ 结算贡献度 + 血缘链标注出处
```

A read-only codebase audit mapped each step to what actually exists:

| Step | Reality | Evidence |
| --- | --- | --- |
| ① 会议入口 | absent (designOS not in this repo, no audio capture) | — |
| ② 个人记忆 | **works** | `UserMemoryItem` `models.py:441`; `routes/memory.py` |
| ③ 信号 + 确认闸门 | **works** | BBS post `blackboard.py:236`; risk→Inbox gate `agents.py:608` |
| ④ 跨人只回答案 | **entirely absent** | see below |
| ⑤ 采纳/沉淀组织 | **works** | brief→team-memory promotion gated `routes/inbox.py:89` |
| ⑥ 贡献度 / 血缘链 | absent (贡献度 zero; lineage zero) | no `contribution`/`memory_relation` in code |

**The critical finding is ④.** There is no execution path for user B's PersonalAgent to
query user A's PersonalAgent and have A's agent compute an answer against A's own private
memory. All memory retrieval is hard-scoped to the calling/logged-in user
(`agents.py:496-497`, `store.py:587-592`). The only "responder" flow,
`fulfill_research_request` (`agents.py:741,769`), is a service/acquisition agent fetching
*external* evidence *for the requester* — it never runs a second user's agent and never
touches anyone's `UserMemoryItem`. The data model distinguishes users and isolates memory,
but the cross-user "answer as user A" call path does not exist.

## Decision

Ship the MVP with these per-step scope decisions (settled during grilling):

- **① Entry (Q2 → b):** replace the designOS meeting with a pasted meeting-notes text
  fed into personal-memory ingestion. Do not build audio/dual-channel for the MVP.
- **④ Matching (Q4 → a):** hard-coded / manual trigger between two seed users. No
  signal-matching engine. Build ④ as a minimal "delegated answer" path: B's twin asks →
  system runs A's twin scoped to A's `UserMemoryItem` → returns an abstracted text answer
  to B, with B never touching raw data.
- **⑥ Settlement (Q3 → a):** shadow contribution points (record-only, no redemption) plus
  a single `derived_from` lineage edge (a direct extension of the existing
  `source/citation` model). No reward conversion — that carries the anti-collusion
  landmines and is out of MVP scope.

**Focus all engineering on ④.** ②③⑤ are free; ①⑥ are cheap. ④ is the product's reason to
exist: build it and the core thesis is proven; skip it and the demo is only single-user
memory plus a faked hand-off.

## Consequences

- MVP is feasible, but ~90% of its feasibility rests on building ④.
- ④ is a bounded backend addition (a new authorized "answer as user A" call path + memory
  scope switch), not a data-model redesign — the isolation primitives already exist.
- **Do not oversell "只出答案" as a privacy/IP guarantee.** An LLM answer synthesized from
  A's private memory is itself derived data and can leak/infer the source. This is a
  vision-layer hard problem, explicitly out of the A-scope MVP judgment, and must not be
  marketed as a moat on the strength of the MVP.
- Deferred to later phases: real signal-matching engine, contribution redemption +
  anti-collusion (Open Questions #1–4), strict per-speaker meeting attribution (#6), and
  raw-data residency/compliance (#7).

## Prototype validation (2026-08-09)

A throwaway logic prototype of ④ was built and driven to answer: "can B's twin get an
abstracted answer from A's twin without ever touching A's raw data?"

- **Verdict:** the ④ **happy-path state model is confirmed sound** — authorization check →
  scope-hard-bound-to-A retrieval → citation-title-only crossing → boundary invariant holds.
  Each transition maps onto existing primitives (PersonalAgent, `UserMemoryItem` user_id
  filter, risk/Inbox gate, `Source`). No architectural blocker; ④ is a new call path, not a
  redesign.
- **Captured on branch** `prototype/delegated-answer` (out of main). Recover with
  `git checkout prototype/delegated-answer -- agentmesh/PROTOTYPE_delegated_answer.html`.
- **Prototype did NOT prove** (carried into the spec as build-time gates, not blockers):
  (1) answer quality on real/sparse memory — needs a real LLM + real store spike; (2) the
  real enforcement strength of the boundary — depends on the caller being unable to tamper
  with the retrieval scope server-side.
- **Open design fork for the spec:** the standing-consent model — how A grants B the right
  to query, at what granularity (person / topic / project), and how it is revoked.

## Privacy-posture decision (2026-08-09)

A follow-up spike (Issue #2, branch `prototype/llm-synthesis-quality`) ran real-LLM
synthesis and found that an LLM answer reproduces the target's specific facts in reworded
form — a **semantic leak** that the verbatim-substring boundary test cannot catch. This
raised whether "数据不离境，只出答案" holds as a privacy guarantee.

**Decision: it does not need to.** This is an **internal-company project where data is
permitted to flow between users.** Therefore:

- "数据不离境，只出答案" is a **collaboration/UX pattern** (twin-mediated answering is
  cleaner than dumping raw data), **not a privacy control.** Do not market it as a moat.
- The **high-sensitivity confirmation gate** stays, but its role is **UX + accountability**
  ("ask A before answering", auditable), not privacy enforcement.
- The verbatim boundary test remains as a **cheap backstop**, reframed as a "verbatim
  guard" — it does not claim to prevent semantic leakage, and none is required here.
- The ④ synthesis can be hardened directly to a real LLM (spike showed quality is good and
  the model self-reports 信息不足 on thin memory); the semantic-leak concern is out of scope
  given cross-user flow is allowed.
