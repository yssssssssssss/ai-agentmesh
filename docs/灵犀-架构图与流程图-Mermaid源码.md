# 灵犀 Lingxi · 架构图与流程图(Mermaid 源码)

> 说明:以下为 Mermaid 文本源码,可直接粘贴到支持 Mermaid 的编辑器(Typora、VS Code、语雀、飞书文档、mermaid.live 等)渲染。
> 节点内换行统一使用 `<br/>`(比 `\n` 兼容性更好)。

---

## 一、顶层架构图(flowchart)

> 优化说明:内容(节点/文字/连线)完全不变;仅通过 ① 每个子图内 `direction LR` 使同层节点横向成行、七层自上而下堆叠成整齐带状,② 为每层加浅色背景使其成为视觉整体,③ 统一连线样式,让整体更成体系。

```mermaid
flowchart TB
  subgraph EMP["员工侧"]
    direction LR
    U1["员工 A"]
    U2["员工 B"]
    U3["员工 C"]
  end

  subgraph TWIN["数字分身层 DigitalTwin Runtime"]
    direction LR
    T1["分身 A<br/>画像 + 个人记忆 + 授权"]
    T2["分身 B"]
    T3["分身 C"]
    A2A["分身间协同协议 A2A<br/>request / evidence / handoff / decision / risk<br/>(绑定 design_project · 可回放)"]
  end

  subgraph CAP["通用 Agent 能力层(注册 + 授权)"]
    direction LR
    Research["检索能力"]
    Data["数据能力"]
    Risk["风险能力"]
    Meeting["会议能力"]
    Author["生成能力"]
    MemCap["记忆能力"]
  end

  subgraph CTX["项目上下文层(DesignOS 核心)"]
    direction LR
    Project["design_projects<br/>项目上下文中心"]
    Timeline["项目时间线 / activity_logs"]
    Sources["sources / artifact_sources"]
  end

  subgraph MEM["三级记忆系统"]
    direction LR
    Personal["个人记忆<br/>user_memories"]
    ProjectMem["项目记忆<br/>project_memories"]
    Team["团队记忆<br/>team_memories"]
    Candidate["候选记忆<br/>candidate tables"]
  end

  subgraph GOV["治理与安全护栏"]
    direction LR
    Review["人审 review-items"]
    RiskRule["风险规则 risk_policy_rules"]
    Grant["能力授权 capability grants"]
  end

  subgraph EXT["外部与模型层(只读连接器)"]
    direction LR
    LLM["LLM Provider"]
    ASR["Realtime ASR"]
    O2["Oxygen / JoySpace / BI"]
  end

  U1 --> T1
  U2 --> T2
  U3 --> T3

  T1 --- A2A
  T2 --- A2A
  T3 --- A2A

  T1 --> CAP
  T2 --> CAP
  T3 --> CAP

  Research --> O2
  Data --> O2
  Author --> LLM
  Meeting --> ASR

  A2A --> Project
  CAP --> Project
  Project --> Timeline
  Project --> Sources

  T1 --> Personal
  Project --> ProjectMem
  CAP --> Candidate
  A2A --> Candidate
  Candidate --> Review
  Review --> ProjectMem
  Review --> Team
  ProjectMem --> Team

  Grant -.授权.-> CAP
  RiskRule -.拦截.-> A2A
  RiskRule -.拦截.-> CAP
  Review -.确认.-> Team

  Personal --> Project
  ProjectMem --> Project
  Team --> Project

  classDef emp fill:#eef2ff,stroke:#5e5ce6,color:#1d1d1f;
  classDef twin fill:#f5f3ff,stroke:#7c3aed,color:#1d1d1f;
  classDef cap fill:#eff6ff,stroke:#2563eb,color:#1d1d1f;
  classDef ctx fill:#fff7ed,stroke:#b45309,color:#1d1d1f;
  classDef mem fill:#ecfdf5,stroke:#0f766e,color:#1d1d1f;
  classDef gov fill:#fef2f2,stroke:#d92d20,color:#1d1d1f;
  classDef ext fill:#f8fafc,stroke:#475467,color:#1d1d1f;

  class U1,U2,U3 emp;
  class T1,T2,T3,A2A twin;
  class Research,Data,Risk,Meeting,Author,MemCap cap;
  class Project,Timeline,Sources ctx;
  class Personal,ProjectMem,Team,Candidate mem;
  class Review,RiskRule,Grant gov;
  class LLM,ASR,O2 ext;

  %% —— 子图背景(浅色带,使每层成为整体)——
  style EMP  fill:#f6f7ff,stroke:#c7d2fe,stroke-width:1px;
  style TWIN fill:#faf8ff,stroke:#ddd6fe,stroke-width:1px;
  style CAP  fill:#f5f9ff,stroke:#bfdbfe,stroke-width:1px;
  style CTX  fill:#fffbf4,stroke:#fde68a,stroke-width:1px;
  style MEM  fill:#f4fdf9,stroke:#a7f3d0,stroke-width:1px;
  style GOV  fill:#fff6f6,stroke:#fecaca,stroke-width:1px;
  style EXT  fill:#fbfcfd,stroke:#e2e8f0,stroke-width:1px;

  %% —— 统一连线样式 ——
  linkStyle default stroke:#94a3b8,stroke-width:1.4px;
```

---

## 二、运行时执行流(sequenceDiagram)

```mermaid
sequenceDiagram
  autonumber
  participant U as 员工 / 其他分身
  participant TR as twinRuntimeService
  participant CR as capabilityRegistry
  participant CAP as 通用能力
  participant RV as reviewInbox / risk
  participant MEM as memoryEngine

  U->>TR: 下达任务 / 发来 A2A 请求
  TR->>MEM: 检索分层上下文(会话/项目/个人/团队)
  TR->>TR: 规划能力调用序列(受 autonomy_level 限制)

  loop 每个能力调用
    TR->>CR: 请求能力(附 twin 身份)
    CR->>CR: 检查 capability grant + 风险规则
    alt 授权且低风险
      CR->>CAP: 执行(tool_run / ai_job / connector_run)
      CAP-->>TR: 结果归一化为 sources
    else 高风险 / 无授权
      CR->>RV: 生成 review-item,阻断执行
    end
  end

  TR->>MEM: 产出写入会话记忆 + 生成候选记忆
  TR->>RV: 高影响结论 → review-item 待人确认
  TR-->>U: 返回候选结论 + 来源 + twin_run 追踪
```

---

## 三、A2A 分身间协同时序(sequenceDiagram · 强调 Agent 沟通)

```mermaid
sequenceDiagram
  autonumber
  participant TA as 分身 A(设计师)
  participant BUS as a2aBus(a2a_messages)
  participant TB as 分身 B(数据 / 需求方)
  participant CAP as 通用能力
  participant RV as 风险 / 人审
  participant MEM as 三级记忆

  TA->>BUS: request 请求(绑定 design_project)
  Note over BUS: INSERT status=open<br/>setImmediate 异步投递
  BUS->>TB: 投递 request
  TB->>CAP: 调用检索 / 数据能力(授权 + 风险闸门)
  CAP-->>TB: 结果归一化为 sources
  TB->>BUS: evidence 证据(带来源)
  BUS->>TA: 回传 evidence
  TA->>CAP: handoff 交生成能力产出草案
  CAP-->>TA: 设计策略草案(候选)
  TA->>RV: decision_proposal → review-item
  RV->>MEM: 人确认后沉淀为项目记忆
  Note over TA,MEM: 全程绑定项目 · 进时间线 · 可回放 · 可审计
```

---

## 四、(可选)三级记忆治理流(flowchart)

```mermaid
flowchart TD
  A["来源层<br/>Chat / 工具 / 会议 / 文档 / A2A"] --> B["原始事件<br/>memory_source_events"]
  B --> C["抽取<br/>MemoryExtractor"]
  C --> D["策略<br/>MemoryPolicyEngine"]
  D --> E["会话短期记忆<br/>chat_session_memories"]
  D --> F["个人记忆<br/>user_memories"]
  D --> G["项目记忆<br/>project_memories"]
  D --> H["候选记忆<br/>candidate tables"]
  H --> I["治理:确认 / 忽略 / 改写 / 归档"]
  I --> F
  I --> G
  F --> J["团队候选<br/>team_memory_candidates"]
  G --> J
  J --> K["负责人确认"]
  K --> L["团队记忆<br/>team_memories"]
  E --> M["检索层<br/>MemoryRetriever"]
  F --> M
  G --> M
  L --> M
  M --> N["消费:分身 / 能力 / 会议 / 复盘"]
```
