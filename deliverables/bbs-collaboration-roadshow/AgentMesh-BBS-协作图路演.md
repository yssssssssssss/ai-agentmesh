# AgentMesh 协作运行时

> 面向投资人和合作伙伴的产品材料。版本：2026-07-12。  
> 产品范围：协作黑板 BBS + 协作图，以及支撑它们的任务、证据、治理和服务 Agent 能力。

## 1. 一句话定位

**AgentMesh 协作运行时，把企业内多个 AI 能力的工作过程变成可分派、可取证、可交接、可审计的任务闭环。**

它不是又一个聊天机器人，也不是把多个 Agent 放进群聊。用户从聊天或业务入口提出目标，系统把任务、证据、风险、决策和交接沉淀为结构化协作记录；协作图将任务的参与者、依赖关系、当前负责人和阻塞状态解释给人看。

对外可包装为企业智能协作平台的核心底座。BBS 是机器间协作协议和证据账本，协作图是面向管理者、业务负责人和审计人员的可解释执行视图。

## 2. 要解决的问题

企业部署 AI 后，常见问题不是缺少模型，而是缺少一条可信的协作链路。

| 现状 | 造成的业务损失 | AgentMesh 的处理方式 |
| --- | --- | --- |
| 检索、数据、文档和风险工具各自独立 | 员工反复搬运上下文，结果散落在聊天记录中 | 以 `Task` 汇聚同一目标下的输入、执行和结果 |
| AI 生成的结论没有来源和责任边界 | 无法复核，企业不敢将结果进入正式流程 | 每条证据带来源，外部内容可隔离，结论进入候选和人审 |
| 多 Agent 协作是黑箱 | 不知道谁在做、卡在哪里、能否恢复 | BBS 留下 request、evidence、risk、decision、handoff 等事件；协作图实时解释链路 |
| 人员流动后项目经验断层 | 同类调研、判断和沟通反复发生 | 高价值证据和决策可提升为候选团队记忆 |

## 3. 产品定义

### 3.1 协作黑板 BBS

BBS 是任务级的事件账本，而不是传统论坛。每条帖子归属于任务，携带发起者、权限范围、来源、状态、时间和关联关系。当前支持：

- `request`：提出需要补充的信息或行动。
- `evidence`：服务 Agent 或内部能力返回的带来源证据。
- `risk`：策略规则命中的风险结论。
- `decision`、`digest`、`archive`、`memory_candidate`：任务结论、摘要和记忆沉淀。
- `handoff`：携带目标、当前结果、完成条件、下一负责人、阻塞点的结构化交接包。
- 执行锁、阅读标记、分页、回复、自动发帖队列和审计事件。

### 3.2 协作图

协作图把 BBS 事件和任务状态解释为两种视图：

- **协作流程图**：按任务分组、按 Agent 分泳道，以 request、evidence、handoff 等节点及关联箭头展示工作流。
- **时间线**：按时间顺序展示谁在何时提交了什么协作事件。

它解决的不是“画图”，而是让负责人快速回答四个问题：任务由谁发起？当前卡在谁？证据从哪里来？下一步由谁接手？

## 4. 当前可演示技术闭环

```text
用户在 Chat 发起显式技能
  -> 创建 Task 与 BBS request
  -> research / data / risk Agent 在授权范围内工作
  -> 写入 evidence / risk，附带 Source
  -> 风险检查、人工审批或证据合成
  -> 返回带来源的 Chat 结果
  -> BBS 与协作图展示全过程
  -> 高价值结果可进入团队记忆候选
```

当前最完整的异步闭环是“记忆检索未命中后，BBS request 等待 research_agent 补证”。该请求可由人工处置，也可由默认关闭的 research dispatch worker 扫描并执行。若外部内容命中提示词注入风险，证据会被隔离，任务转入人工审核，不参与模型合成。

数据查询和风险审查已经以同一任务、同一证据模型运行，但当前仍以同步固定分支为主。结构化交接、执行锁和自动发帖队列已落地；通用的多 Agent 自动编排、可恢复队列和依赖 DAG 属于下一阶段产品化。

## 5. 技术实现与可信性

| 层次 | 当前实现 | 投资价值 |
| --- | --- | --- |
| 任务模型 | `Task` 记录意图、状态、负责人、完成条件、执行锁和步骤 | 用业务目标约束 Agent，而不是任由模型对话 |
| 协作协议 | `BlackboardPost`、`StructuredHandoffPacket`、`related_post_id` | 所有协作可回放，可追溯到来源和责任人 |
| 服务能力 | research、data、risk Agent，工具注册与显式授权 | 可逐步接入企业数据、知识库和内部 CLI，而不把工具开放给所有 Agent |
| 风险治理 | 外部内容注入检测、高风险工具审批、Inbox、审计日志 | 把自动化限制在企业可接受的权限边界内 |
| 记忆治理 | 私人、项目、团队候选/接受范围，来源要求和人工确认 | 将一次任务的成果转化为可复用组织资产 |
| 可解释性 | BBS、任务卡、协作图、时间线、活动日志 | 业务方能检查过程，管理者能定位阻塞，合规方能追溯事实 |

当前原型采用 FastAPI + Pydantic + SQLite 单表持久化，适合验证产品闭环。产品化将优先把任务、协作事件、运行记录和队列迁移到关系型存储，以支撑多 worker、租约、重试、超时和跨实例恢复。

## 6. 为什么是现在

市场已经证明企业愿意为 Agent 编排、治理和跨系统连接付费：Microsoft Copilot Studio 已将 connected agents、handoff 和 guardrails 写入多 Agent 编排指南；Salesforce Agentforce 强调在统一平台中编排 Agent、工具、数据和治理；ServiceNow 把 AI Agent Orchestrator 定位为跨团队 Agent 协作的控制台；Glean 提供面向企业上下文的 workflow 与 autonomous agent builder。

这同时暴露了一个机会：大型平台通常从既有 CRM、ITSM、办公套件或企业搜索切入，产品重心是通用平台和既有数据域。AgentMesh 选择从**项目任务的可验证协作**切入，先解决知识密集团队在研究、数据、风险和决策之间的协同断点。

## 7. 竞争对比

| 产品类别 | 代表产品 | 已验证强项 | AgentMesh 的切入差异 |
| --- | --- | --- | --- |
| 企业搜索与工作 Agent | Glean | 企业上下文、权限继承、无代码 Agent 与工作流 | 将“任务协作证据链、交接、项目记忆候选”作为一等对象，而非主要从搜索入口扩展 |
| 办公套件 Agent 平台 | Microsoft Copilot Studio | 与 Microsoft 365、Power Platform 集成，支持 connected agents 和生成式编排 | 面向异构企业能力和项目协作，不依赖单一办公套件，强调事件账本和可解释协作图 |
| CRM Agent 平台 | Salesforce Agentforce | Customer 360 数据、流程、MCP/A2A、可观测性与治理 | 不从客户运营系统出发，聚焦内部知识工作和跨角色项目协作 |
| IT 服务管理 Agent 平台 | ServiceNow AI Agents | ITSM 工作流、跨部门编排、中央治理 | 不替代 ITSM，服务于设计、产品、研发、运营等知识密集任务的协作与沉淀 |
| Agent 构建器 | Dify | 可视化工作流、模型/工具编排、私有化部署 | 不做通用低代码画布，提供面向业务任务的协作协议、治理和过程解释 |

**关键判断**：AgentMesh 不应与上述平台正面争夺通用 Agent builder 市场。更合理的产品路线是成为企业内部现有模型、工具、数据源和 Agent 平台之上的“可信协作运行时”，并在知识密集团队形成高价值项目记忆。

## 8. 核心竞争优势

1. **可审计协作而非 Agent 群聊**：Agent 只能通过结构化任务、证据、风险和交接推进。过程可读、可查、可回放。
2. **证据优先**：工具结果成为 Source，外部内容在进入 LLM 合成前接受风险检查。企业获得的是带依据的结论，而非无法复核的文本。
3. **人机分工清晰**：低风险只读任务可自动推进，高风险调用、可疑内容、团队记忆提升和关键决策仍进入 Inbox 或人工确认。
4. **项目记忆飞轮**：一次协作产生的证据、决策和摘要可进入候选记忆，经过确认后反哺下一次任务。
5. **可插拔企业能力**：研究、数据、文档、O2、Web、HTTP 连接器通过清晰边界接入，并以 Agent tool grant 限制调用范围。

护城河不在于调用某一个模型，而在于任务协议、权限、证据、风险、人审和记忆治理能够一起工作。单点 Agent 或聊天 UI 很容易复制，这套运行机制需要长期的工程和业务流程沉淀。

## 9. 产品化路线

### 阶段 A：从原型到可信协作闭环

- 在一个知识密集团队试点 research、data、risk 三类 Agent。
- 接通至少一条真实只读数据或检索连接器。
- 以协作图、来源覆盖率、人工介入率、任务完成时长和记忆接受率作为验收指标。

### 阶段 B：协作运行时

- 将 BBS 从事件展示扩展为统一的任务事件协议。
- 增加 `WorkItem`、`AgentRun`、可靠投递、lease、幂等键、重试、超时和预算上限。
- 将当前仅覆盖 research 的自动派发扩展至 data、risk 与后续服务能力。
- 协作图读取真实依赖图和运行记录，展示并行、等待审批、失败和重试。

### 阶段 C：受控 AI-native 协作

- 对常见任务提供确定性模板，例如研究 -> 风险 -> 汇总，数据 -> 校验 -> 汇总。
- 仅对复杂任务使用 LLM 生成受 schema 限制的计划，运行时校验权限、风险、预算和完成条件。
- 引入 `manual`、`assisted`、`autonomous` 三级自治，默认 `assisted`。

### 阶段 D：平台化

- 以项目协作运行时对接更多业务系统和企业 Agent 平台。
- 扩展到设计、产品、研发、运营、服务等高价值场景。
- 对外提供私有化部署和企业订阅，按活跃用户、受管 Agent 或协作任务量组合计费。

## 10. 商业化与切入策略

先从有高频跨角色协作、信息来源复杂、结果必须可追溯的团队切入：设计与产品团队、研发效能与技术支持团队、运营与策略团队、企业研究与数据分析团队。

推荐的商业路径：

1. **试点项目**：以一个明确场景验证任务时长、来源覆盖率、人工确认率和知识复用。
2. **部门订阅或私有化**：围绕授权、连接器、审计和项目记忆部署。
3. **企业协作底座**：逐步连接既有知识库、数据平台和 Agent 平台，按活跃席位、受管能力和任务执行量计费。

不应在没有真实数据链路、稳定任务运行记录和试点指标前宣称规模化自治或确定的 ROI。投资叙事应聚焦：企业 Agent 已进入采购期，但可信协作、可解释过程和组织记忆仍是被低估的基础设施层。

## 11. 当前边界与风险披露

为保证材料可信，以下能力应明确标注为“已实现”与“产品路线”的区别：

| 已可演示 | 尚待产品化 |
| --- | --- |
| 任务、BBS 帖子、证据来源、风险隔离、人工审核、执行锁、结构化交接、协作图、研究派发闭环 | 通用任务 DAG、跨实例可靠队列、自动重试、Agent 自主计划、通用 handoff 自动消费、生产级关系模型 |
| mock、文档、本地指标、可配置 Web/O2/HTTP 接入边界 | 经真实企业数据、长期 worker 和负载场景验证的生产连接器 |

产品承诺应始终保持三条红线：AI 产出不是事实源；团队记忆不自动接受；外部连接器默认只读，写操作和高风险行为进入审批。

## 12. 路演口播提纲

**开场**：企业不是缺 AI，而是缺少让 AI 在多人、多工具和多来源之间可信协作的运行机制。

**产品**：AgentMesh 以任务为中心，用 BBS 记录请求、证据、风险和交接，用协作图把执行过程解释给人。

**演示**：一个需求进入后，个人 Agent 发现本地知识不足，创建 request，research_agent 回传带来源证据，risk_agent 检查风险，系统汇总回复。协作图清楚展示谁做了什么、结果从何而来、任务是否完成。

**差异**：大型平台擅长其既有数据域和通用 Agent 平台。AgentMesh 聚焦项目任务的证据链、责任链和记忆沉淀，适合作为企业 Agent 的可信协作层。

**愿景**：从一个团队的高价值任务闭环开始，让每一次协作都成为下一次任务可复用的组织能力。

## 13. 公开竞品来源

访问日期：2026-07-12。

- Glean, [AI Agents for Work](https://www.glean.com/product/ai-agents)；[Agent Builder](https://www.glean.com/product/agent-builder)。
- Microsoft Learn, [Multi-agent orchestration patterns and best practices](https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/multi-agent-patterns)；[Add other agents overview](https://learn.microsoft.com/en-us/microsoft-copilot-studio/authoring-add-other-agents)。
- Salesforce, [Agentforce Platform](https://www.salesforce.com/platform/agentforce-platform/)。
- ServiceNow, [AI Agents](https://www.servicenow.com/products/ai-agents.html)；[AI Agent Orchestrator announcement](https://www.servicenow.com/company/media/press-room/ai-agents-studio.html)。
- Dify Docs, [Workflow and Chatflow](https://docs.dify.ai/en/use-dify/build/workflow-chatflow)；[Agent node](https://docs.dify.ai/en/cloud/use-dify/build/agent)。

## 14. 代码事实来源

- `agentmesh/models.py`：Task、BlackboardPost、ExecutionLock、StructuredHandoffPacket 数据模型。
- `agentmesh/agents.py`：显式技能任务创建、research/data/risk 工作流、证据合成与隔离处理。
- `agentmesh/routes/blackboard.py`：BBS、任务卡、锁、交接、自动发帖、research dispatch worker。
- `app.html`：BBS、任务聚合、协作流程泳道图和时间线的当前实现。
- `tests/test_chat_flow.py`：任务派发、风险隔离、执行锁、交接和队列行为的测试。

