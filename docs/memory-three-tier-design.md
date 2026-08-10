# AgentMesh 三层记忆设计（个人 / 项目 / 团队）

> 本文以"意图设计"视角，把 AgentMesh 的记忆体系拆解为**个人记忆 · 项目记忆 · 团队记忆**三层，给出：
> 一、架构设计；二、信息流转设计；三、功能设计。并在末尾诚实标注当前实现与意图之间的张力。
>
> 代码锚点：`agentmesh/models.py`、`agentmesh/routes/memory.py`、`agentmesh/agents.py`、`agentmesh/store.py`、`agentmesh/seed.py`。

---

# 一、架构设计

## 1.1 三层定义

三层的划分标准是**共享与治理级别**（谁拥有、谁能看、如何晋升），而不是时间。时间分层(short/mid/long)是"个人/项目"层内部的子结构。

| 维度 | 个人记忆 | 项目记忆 | 团队记忆 |
|---|---|---|---|
| **目的** | 个人工作上下文、私有笔记、对话结果 | 围绕某项目的阶段沉淀与共享结论 | 可复用、经审核的团队级知识资产 |
| **拥有者** | 单个用户 | 项目参与者 | 工作区/团队 |
| **隔离键** | `user_id` | `user_id + project_id`（个人视角）/ `project_id`（共享视角） | `workspace_id` |
| **底层模型** | `UserMemoryItem` | `UserMemoryItem`(mid/long) + `MemoryItem`(scope=PROJECT) | `MemoryItem`(scope=TEAM_*) |
| **可见性 Scope** | `PRIVATE` | `PRIVATE`(个人项目沉淀) / `PROJECT`(共享) | `TEAM_CANDIDATE` → `TEAM_ACCEPTED` |
| **时间分层 Layer** | `short_term` 为主 | `mid_term` / `long_term` | 不分层（以状态治理） |
| **写入方式** | 自动（workflow 结果）+ 手动笔记 | 汇总生成 + 手动晋升 | 候选提炼 → 审核接受 |
| **治理门** | 无（本人可写） | 弱（本人/项目内） | 强（`lead/admin` + 权限策略表） |
| **典型 memory_type** | `note` `data` `method` `chat_workflow:*` | `project_summary` `project_archive` | `decision` `brief_decision` `risk` `bbs_evidence` |

## 1.2 架构图（组件与归属）

```mermaid
flowchart TB
    subgraph P["① 个人记忆 (user_id)"]
        direction TB
        PN["私有笔记 / 对话结果<br/>UserMemoryItem · short_term · PRIVATE"]
        PD["每日/群聊摘要<br/>daily_summary · group_chat_summary"]
        PN --> PD
    end

    subgraph J["② 项目记忆 (user_id + project_id)"]
        direction TB
        JM["项目中期摘要<br/>UserMemoryItem · mid_term · project_summary"]
        JA["项目长期归档 + 召回索引<br/>UserMemoryItem · long_term · project_archive"]
        JS["项目共享记忆<br/>MemoryItem · scope=PROJECT"]
        JM --> JA
    end

    subgraph T["③ 团队记忆 (workspace)"]
        direction TB
        TC["候选团队记忆<br/>MemoryItem · TEAM_CANDIDATE · PROPOSED"]
        TA["已接受团队记忆<br/>MemoryItem · TEAM_ACCEPTED · ACCEPTED"]
        TC --> TA
    end

    PD -->|每日 rollup| JM
    JA -.可复用结论晋升.-> TC
    JS -.晋升.-> TC

    subgraph INFRA["共享基础设施"]
        Store["Store (SQLite)"]
        LLM["LLMClient (摘要, 可回退)"]
        Perm["权限策略表<br/>ensure_can_update_memory"]
        Search["检索融合 store.search"]
    end

    P --> Store
    J --> Store
    T --> Store
    JM -.LLM.-> LLM
    JA -.LLM.-> LLM
    TC --> Perm
    Store --> Search

    style P fill:#eef6ff,stroke:#4a90d9
    style J fill:#e6f7ec,stroke:#3fae6b
    style T fill:#fff4e6,stroke:#e0912f
```

---

# 二、信息流转设计

## 2.1 向上沉淀（越高越精、越共享）

信息从"个人即时"逐级浓缩、逐级升高共享级别；每次跨层都是**收敛 + 提权**，且高层跨越需要治理确认。

```mermaid
flowchart LR
    A(["对话 / $skill 结果"]) --> B["个人短期<br/>short_term · PRIVATE"]
    B -->|按天幂等汇总| C["个人每日摘要<br/>daily_summary"]
    C -->|项目维度汇总| D["项目中期<br/>mid_term · project_summary"]
    D -->|项目结束归档| E["项目长期<br/>long_term · project_archive<br/>+ 召回索引"]
    E -->|提炼可复用结论| F{"治理门<br/>lead/admin?"}
    F -->|通过| G["团队候选<br/>TEAM_CANDIDATE"]
    G -->|审核接受| H["团队记忆<br/>TEAM_ACCEPTED"]

    style B fill:#eef6ff
    style C fill:#eef6ff
    style D fill:#e6f7ec
    style E fill:#e6f7ec
    style G fill:#fff4e6
    style H fill:#fdeaea
```

**关键流转规则**
- 普通闲聊 / `ASK_SYSTEM_INFO` / 待审批 **不进入**个人记忆（防污染）。
- 每级 rollup 排除上一轮自身产物（`daily_summary` / `short_term_rollup` / `project_archive`），防自我循环汇总。
- 归档强制含"召回索引"关键词段，供跨项目检索。
- 个人 → 团队的跨越**必须过权限门**（`ensure_can_update_memory` + 权限策略表），绝不自动写团队记忆。

## 2.2 向下召回（记忆如何反哺对话）

```mermaid
sequenceDiagram
    autonumber
    participant U as 用户
    participant A as PersonalAgent
    participant S as store.search
    participant L as LLM 合成

    U->>A: $memory.search / 提问
    A->>S: 按 workspace/project/visibility 检索
    S->>S: 融合 个人(PRIVATE) + 项目 + 团队(可见 scope)
    S-->>A: 来源感知结果 (result_type + scope)
    alt 命中足够
        A->>L: 带来源合成答案
        L-->>U: 回答 + 引用来源
    else 命中不足
        A->>A: 在项目 BBS 发帖求助
        A-->>U: 已发帖等待补充
    end
```

## 2.3 三层可见性矩阵（谁能看到哪层）

```mermaid
flowchart TB
    subgraph Roles["角色"]
        M["普通成员"]
        Lead["组长 TEAM_LEAD"]
        Adm["管理员 ADMIN"]
    end

    P1["个人记忆 (本人)"]
    J1["项目记忆 (项目内)"]
    Tc["团队候选"]
    Ta["团队已接受"]

    M --> P1
    M --> J1
    M --> Ta
    Lead --> P1
    Lead --> J1
    Lead --> Tc
    Lead --> Ta
    Adm --> P1
    Adm --> J1
    Adm --> Tc
    Adm --> Ta

    M -.看不到.-x Tc

    style Tc fill:#fff4e6
    style Ta fill:#fdeaea
```

- 个人记忆：仅本人（`user_id` 隔离 + `PRIVATE`）。
- 团队候选：仅 `lead/admin` 可见（`_visible_memory_items` 过滤）。
- 团队已接受：全员可见（工作区内）。
- 跨工作区：仅 `ADMIN` 可越界。

---

# 三、功能设计

## 3.1 分层功能清单

| 层 | 功能 | API / 触发 | 代码位置 |
|---|---|---|---|
| 个人 | 自动写短期记忆 | workflow 结束自动 | `agents.py:_record_short_term_memory` |
| 个人 | 手动写记忆/笔记 | `POST /api/memory/user` | `routes/memory.py:139` |
| 个人 | 每日汇总（幂等） | `POST /user/daily-summary` | `routes/memory.py:155` |
| 个人 | 群聊摘要 | `POST /user/group-summary` | `routes/memory.py:168` |
| 个人 | 每日汇总 Worker（默认关） | 后台 · env-gated | `routes/memory.py:315` |
| 项目 | 中期摘要（LLM优先） | `POST /user/project-summary` | `routes/memory.py:190` |
| 项目 | 长期归档 + 召回索引 | `POST /user/archive-project` | `routes/memory.py:216` |
| 项目 | 分层视图/计数 | `GET /user`、`GET /overview` | `routes/memory.py:88,99` |
| 团队 | 创建候选团队记忆 | `$memory.propose` / BBS 晋升 / 文档确认 | `agents.py`、`blackboard.py:416`、`inbox.py:108` |
| 团队 | 接受候选（提权） | `PATCH /api/memory/{id}` status=ACCEPTED | `routes/memory.py:242` |
| 团队 | 权限门校验 | 内嵌于接受流程 | `permissions.py:ensure_can_update_memory` |
| 全层 | 检索融合 | `GET /api/search?visibility=...` | `store.py:search` |

## 3.2 各层功能职责（单一职责）

```mermaid
flowchart LR
    subgraph 个人["个人记忆 · 快而全"]
        F1["捕获: 自动+手动"]
        F2["降噪: 闲聊不入"]
        F3["按天收敛"]
    end
    subgraph 项目["项目记忆 · 精而聚"]
        F4["项目维度汇总"]
        F5["归档+召回索引"]
        F6["LLM优先/回退"]
    end
    subgraph 团队["团队记忆 · 稳而权威"]
        F7["候选提炼"]
        F8["审核接受"]
        F9["状态治理"]
    end
    个人 --> 项目 --> 团队
```

## 3.3 记忆状态治理（团队层）

```mermaid
stateDiagram-v2
    [*] --> proposed: 提炼候选
    proposed --> accepted: lead/admin 接受(→TEAM_ACCEPTED)
    proposed --> disputed: 存疑
    proposed --> expired: 超期
    accepted --> disputed: 事后争议
    disputed --> accepted: 复核通过
    accepted --> deprecated: 过时
    deprecated --> [*]
    expired --> [*]
```

---

# 四、实现张力（诚实标注，供后续收敛）

三层是清晰的**意图**，但当前实现有三处偏差，建议后续对齐：

1. **"项目记忆"身份分裂**：项目层同时由两种东西承担——`UserMemoryItem(mid/long, PRIVATE)` 是"个人的项目沉淀"（仍私有），而 `MemoryItem(scope=PROJECT)` 才是"项目共享记忆"。两者未打通，`seed.py:326` 有"项目记忆"示例但缺少从个人项目沉淀 → 项目共享的自动/半自动通道。
2. **向上流转半自动**：个人→每日→中期→归档→团队 这条链，除每日 Worker（默认关）外，中期/归档/候选大多需**显式 API 触发**，"记忆自动越沉越精"目前更多是接口就绪而非常驻运行。
3. **向下召回偏弱**：检索能融合三层，但"召回结果如何结构化注入下一轮 LLM 合成、并影响答案质量"这一闭环较薄，缺少可度量的召回命中率/引用覆盖率反馈。

> 建议收敛方向：把"项目共享记忆"确立为项目层唯一权威载体（个人项目沉淀作为其来源候选）；把 rollup 管线在真实环境常驻并幂等运行；把召回作为一等公民接入 chat 合成并度量。

---

## 图例

| 色 | 层 |
|---|---|
| 蓝 | 个人记忆 |
| 绿 | 项目记忆 |
| 橙 | 团队候选 |
| 红 | 团队已接受 / 高治理 |
