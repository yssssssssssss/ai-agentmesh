import type { ShareScope } from '../store/DemoContext'

/* ============ 当前用户与空间 ============ */
export const CURRENT_USER = {
  name: '林知夏',
  role: '体验设计师',
  space: '家电设计组',
  domains: ['营销会场', '首页体验', '导购场景'],
  project: '2026 年 618 家电会场首页改版',
}

/* ============ 首页：数字人身份 ============ */
export const DIGITAL_PROFILE = {
  personalKnowledge: 24,
  teamSkills: 6,
  monthlyCollab: 8,
}

/* ============ 首页：最近理解了我 ============ */
export interface Understanding {
  id: string
  text: string
}
export const UNDERSTANDINGS: Understanding[] = [
  { id: 'u-1', text: '你近期主要关注会场首屏入口效率。' },
  { id: 'u-2', text: '你更倾向使用数据和历史案例支持设计决策。' },
  { id: 'u-3', text: '你正在建立营销会场的项目启动方法。' },
]

/* ============ 首页：今日工作 ============ */
export interface TodoItem {
  id: string
  title: string
  status: 'done' | 'doing' | 'pending'
  to?: string
}
export const TODAY_WORK: TodoItem[] = [
  { id: 't-1', title: '618 家电会场首页设计 Brief', status: 'doing', to: '/workspace' },
  { id: 't-2', title: '补充 2025 年首屏入口数据', status: 'done' },
  { id: 't-3', title: '确认新提炼的项目经验', status: 'pending', to: '/knowledge' },
]

/* ============ 工作台：对话 ============ */
export interface Conversation {
  id: string
  title: string
  project: string
  status: '进行中' | '已完成' | '待确认'
  updated: string
  group: '进行中' | '今天' | '昨天' | '本周'
  active?: boolean
}
export const CONVERSATIONS: Conversation[] = [
  { id: 'conv-1', title: '618 家电会场首页改版', project: '2026 618 家电会场', status: '进行中', updated: '刚刚', group: '进行中', active: true },
  { id: 'conv-2', title: '首屏入口点击口径确认', project: '2026 618 家电会场', status: '已完成', updated: '今天 14:20', group: '今天' },
  { id: 'conv-3', title: '2024 品类日楼层结构梳理', project: '2024 超级品类日', status: '已完成', updated: '昨天 18:05', group: '昨天' },
  { id: 'conv-4', title: '导购卡首屏数量测试', project: '导购场景优化', status: '已完成', updated: '本周一', group: '本周' },
]

/** 数字人回答正文 */
export const WORKSPACE_ANSWER =
  '综合历史项目与近 90 天数据，我的建议是：2026 年 618 家电会场首屏应优先保证核心入口效率。沉浸式头图能增强氛围，但会下压重点商品与活动入口、拉低首屏点击。推荐采用效率型楼层结构，并把重点品类入口固定在首屏可视区。'

/** 分析过程摘要（折叠态一行展示的要点） */
export const WORKSPACE_ANALYSIS_SUMMARY = [
  '找到 3 个相似项目',
  '检索 2 条团队经验',
  '调用 1 个数据查询 Skill',
  '获得 2 位同事数字分身的补充',
]

/** 分析过程步骤（对话内展开，用户语言，不含底层命令） */
export const WORKSPACE_ANALYSIS_STEPS = [
  '正在理解当前任务',
  '正在检索相似项目',
  '正在读取团队经验',
  '正在请求相关数字分身补充',
  '正在整合数据和项目判断',
  '已形成设计建议',
]

/** 右侧面板：本次工作过程（结构化展开） */
export const WORKSPACE_ANALYSIS = {
  retrieved: '在团队 Wiki 与项目库检索「618 家电会场 首屏」，命中 3 个高相似度会场、2 条团队经验。',
  skill: '调用「数据查询 Skill」，取回首页营销入口近 90 天点击数据。',
  peers: [
    { name: '李明的数字人', contribution: '补充 2025 年复盘：沉浸式头图降低首屏核心入口可见性。' },
    { name: '王晨的数字人', contribution: '补充首屏入口点击数据，量化点击率下降约 11%。' },
  ],
  conclusion: '综合历史结论与近 90 天数据，判断入口型会场应优先保证首屏核心入口效率，并据此生成 2026 Brief。',
}

/* 工作台：技术详情（右侧面板过程视图内二级折叠，默认收起） */
export const WORKSPACE_TECH_LOG = [
  { label: '知识检索', detail: 'wiki.search(query="618家电会场 首屏", top_k=8) · 命中 3 项目 / 2 经验' },
  { label: 'Skill 调用', detail: 'skill.marketing_entry_metrics(scene="home", range="90d") · 200 OK · 1.2s' },
  { label: '分身协作', detail: 'peer.request(to=["李明","王晨"], type="evidence") · 2 responses' },
  { label: '生成', detail: 'compose_brief(evidence=6, template="project_kickoff") · tokens 3.1k' },
]

/* ============ 工作台：引用来源（内联引用 + 右侧详情面板） ============ */
export type RefKind = 'project' | 'experience' | 'data' | 'peer'

export interface ProjectDetail {
  background: string
  problem: string
  solution: string
  result: string
  relation: string
}
export interface ExperienceDetail {
  conclusion: string
  sourceProjects: string[]
  scope: string
  lastVerified: string
  citedBy: string[]
}
export interface DataMetric {
  label: string
  value: string
  delta?: string
}
export interface DataDetail {
  range: string
  metrics: DataMetric[]
  conclusion: string
  time: string
  caliber: string
}
export interface PeerDetail {
  field: string
  citedExperience: string
  contribution: string
  knowledgeSource: string
}

export type WorkspaceRef =
  | { id: string; kind: 'project'; title: string; chip: string; detail: ProjectDetail }
  | { id: string; kind: 'experience'; title: string; chip: string; detail: ExperienceDetail }
  | { id: string; kind: 'data'; title: string; chip: string; detail: DataDetail }
  | { id: string; kind: 'peer'; title: string; chip: string; detail: PeerDetail }

export const WORKSPACE_REFERENCES: WorkspaceRef[] = [
  {
    id: 'ref-2025',
    kind: 'project',
    title: '2025 年 618 家电会场复盘',
    chip: '历史项目 · 相似度 92%',
    detail: {
      background: '2025 年 618 家电会场首页采用沉浸式头图方案，强调品牌氛围与视觉冲击。',
      problem: '沉浸式头图占据首屏主要空间，重点商品与活动入口被下压到折叠线以下。',
      solution: '首屏以整屏头图 + 轮播为主，核心入口楼层排在头图之后。',
      result: '首屏核心入口点击率环比下降 11%，用户到达重点品类的路径变长。',
      relation: '直接对应本次「首屏是否沿用沉浸式头图」的核心决策，是最相似的历史样本。',
    },
  },
  {
    id: 'ref-2024',
    kind: 'project',
    title: '2024 年家电超级品类日',
    chip: '历史项目 · 相似度 78%',
    detail: {
      background: '2024 年家电超级品类日首页采用效率型楼层结构，头图精简。',
      problem: '需要在有限首屏内平衡氛围表达与多品类入口。',
      solution: '精简头图 + 核心品类入口楼层前置，氛围元素下沉到楼层背景。',
      result: '首屏入口点击率相比沉浸式方案高出约 9%，转化路径更短。',
      relation: '为「效率型楼层结构」提供正向历史依据。',
    },
  },
  {
    id: 'ref-data',
    kind: 'data',
    title: '首页营销入口点击数据',
    chip: '数据查询 Skill · 近 90 天',
    detail: {
      range: '家电会场首页营销入口（头图、重点品类、活动楼层）的曝光与点击。',
      metrics: [
        { label: '首屏核心入口点击率', value: '沉浸式头图方案', delta: '-11%' },
        { label: '效率型楼层首屏点击率', value: '对比沉浸式方案', delta: '+9%' },
        { label: '重点品类入口到达率', value: '效率型更优', delta: '+7%' },
      ],
      conclusion: '效率型楼层结构在首屏核心入口点击与重点品类到达上均优于沉浸式头图方案。',
      time: '统计区间：近 90 天（含 2025 618 大促期）。',
      caliber: '口径：首屏 = 进入页面首个可视区；点击率 = 入口点击 UV / 首屏曝光 UV。',
    },
  },
  {
    id: 'ref-liming',
    kind: 'peer',
    title: '李明数字分身贡献的项目判断',
    chip: '来自李明 · 会场复盘经验',
    detail: {
      field: '李明 · 家电设计组，擅长营销会场与数据复盘。',
      citedExperience: '引用了李明沉淀的「2025 618 会场复盘：沉浸式头图影响首屏入口」经验。',
      contribution: '判断本次改版应避免整屏沉浸式头图，优先保证核心入口首屏可见。',
      knowledgeSource: '来源：2025 618 家电会场复盘文档 + 李明本人确认的复盘结论。',
    },
  },
]

/** 核心结论所依据的团队经验（单独引用，演示 experience 详情） */
export const CORE_EXPERIENCE_REF: WorkspaceRef = {
  id: 'ref-exp',
  kind: 'experience',
  title: '团队经验：首屏核心入口优先',
  chip: '家电设计组 · 团队经验',
  detail: {
    conclusion: '入口型营销会场首屏应优先保证核心入口的可见性与点击效率，氛围表达服从入口效率。',
    sourceProjects: ['2025 618 家电会场复盘', '2024 家电超级品类日'],
    scope: '入口型营销活动会场（会场首页、品类日首页）。',
    lastVerified: '最近验证：2025 年 618 大促，数据再次支持该结论。',
    citedBy: ['2024 家电超级品类日', 'PLUS 会员日活动页', '清凉家电会场（引用中）'],
  },
}

/* ============ 会场 Brief 内容 ============ */
export const BRIEF = {
  title: '2026 年 618 家电会场首页设计 Brief',
  goal: '在 618 大促期间提升家电会场首屏的核心入口效率，兼顾品牌氛围与转化路径。',
  history: [
    '2025 年 618 采用沉浸式头图，首屏视觉氛围强，但核心入口首屏可见性下降。',
    '2024 年家电超级品类日使用效率型楼层，核心入口点击表现更稳定。',
  ],
  problem: '沉浸式头图占据首屏后，重点商品与活动入口被下压，首屏核心入口点击率下滑。',
  principles: [
    '首屏优先保证核心入口的可见性与点击效率。',
    '沉浸式头图需结合入口点击数据谨慎使用，控制首屏占比。',
    '采用效率型楼层结构，保留重点商品入口在首屏可达。',
  ],
  direction: [
    '首屏采用「精简头图 + 核心入口楼层」组合。',
    '重点品类入口固定在首屏可视区，减少下滑成本。',
    '氛围表达迁移到二屏及楼层背景，避免挤占入口。',
  ],
  data: [
    '2025 年沉浸式头图方案首屏核心入口点击率环比下降 11%。',
    '效率型楼层在 2024 品类日首屏入口点击率高出 9%。',
  ],
}

/* ============ 待确认 / 已共享 知识 ============ */
export const NEW_KNOWLEDGE = {
  title: '入口型会场应优先保证首屏核心入口效率',
  conclusion:
    '入口型活动会场应优先保证首屏核心入口效率。沉浸式头图需要结合入口点击数据谨慎使用，推荐采用效率型楼层结构，并保留重点商品入口。',
  problem: '会场改版容易被视觉氛围主导，导致首屏核心入口被下压，点击效率下降。',
  sources: ['2025 年 618 家电会场复盘', '2026 年 618 家电会场首页设计 Brief', '首页入口点击数据'],
  evidence: [
    '2025 年沉浸式头图方案首屏核心入口点击率环比下降 11%。',
    '效率型楼层结构在历史项目中首屏入口点击更稳定。',
  ],
  scope: '入口型营销活动会场',
  recommendScope: 'group' as ShareScope,
}

/* 我的知识：各分类静态样例 */
export interface KnowledgeCardData {
  id: string
  title: string
  summary: string
  tags: string[]
  project: string
  updated: string
}

export const PERSONAL_KNOWLEDGE: KnowledgeCardData[] = [
  {
    id: 'p-1',
    title: '活动标签信息层级规范',
    summary: '活动标签按「利益点 > 品类 > 时间」排序，弱化次要信息，保证扫读效率。',
    tags: ['信息层级', '标签'],
    project: '618 家电会场',
    updated: '3 天前',
  },
  {
    id: 'p-2',
    title: '会场楼层优先级模型',
    summary: '按转化贡献与入口价值排列楼层顺序，核心品类楼层前置。',
    tags: ['楼层结构', '转化'],
    project: '2024 超级品类日',
    updated: '1 周前',
  },
  {
    id: 'p-3',
    title: '导购卡片的首屏承载数量',
    summary: '首屏导购卡控制在 4–6 个，超出后点击分散、决策成本升高。',
    tags: ['导购', '首屏'],
    project: '导购场景优化',
    updated: '2 周前',
  },
  {
    id: 'p-4',
    title: '大促氛围与效率的平衡区间',
    summary: '氛围元素占首屏比例建议控制在 35% 以内，避免挤压入口。',
    tags: ['大促', '首屏'],
    project: '618 家电会场',
    updated: '2 周前',
  },
]

export const PROJECT_KNOWLEDGE: KnowledgeCardData[] = [
  {
    id: 'pr-1',
    title: '618 家电会场首屏入口策略',
    summary: '首屏优先核心入口效率，头图精简，重点商品入口固定可达。',
    tags: ['618', '首屏'],
    project: '2026 618 家电会场',
    updated: '刚刚',
  },
  {
    id: 'pr-2',
    title: '会场项目启动检查清单',
    summary: '启动前必做：历史项目检索、数据口径确认、风险提醒对齐。',
    tags: ['项目启动', '流程'],
    project: '家电设计组',
    updated: '5 天前',
  },
]

export const SHARED_KNOWLEDGE: KnowledgeCardData[] = [
  {
    id: 'sh-1',
    title: '活动标签信息层级规范',
    summary: '已共享给家电设计组，本周被 4 位同事引用。',
    tags: ['信息层级', '已复用'],
    project: '618 家电会场',
    updated: '本周',
  },
  {
    id: 'sh-2',
    title: '会场楼层优先级模型',
    summary: '已共享给家电设计组，应用于 2 个会场项目。',
    tags: ['楼层结构'],
    project: '2024 超级品类日',
    updated: '1 周前',
  },
  {
    id: 'sh-3',
    title: '大促氛围与效率的平衡区间',
    summary: '已共享给家电设计组，作为首屏评审参考。',
    tags: ['大促'],
    project: '618 家电会场',
    updated: '2 周前',
  },
]

/* 被复用详情 */
export const REUSE_DETAIL = {
  title: '活动标签信息层级规范',
  citedBy: 4,
  projects: 3,
  recent: 'PLUS 会员日活动页',
  addedCondition: '当标签超过 3 个时，隐藏次要标签到「更多」浮层。',
  timeline: [
    { who: '周然的数字人', project: 'PLUS 会员日活动页', note: '直接复用，扫读效率提升' },
    { who: '赵敏的数字人', project: '小家电专场', note: '结合品类做了排序微调' },
    { who: '孙浩的数字人', project: '清凉家电会场', note: '新增「超过 3 个标签折叠」条件' },
  ],
}

/* ============ 工作洞察 ============ */

/**
 * 复盘 / 知识候选状态机（预留类型）
 * 本轮「我的知识」不改 UI，但知识候选流转的状态类型在此统一定义，供后续页面联动复用。
 * 理想流转：建议复盘 → 复盘中 → 待补充结果 → 已形成知识候选 → 我的知识·待我确认。
 */
export type ReviewStatus =
  | 'suggested' // 建议复盘
  | 'in_progress' // 复盘中
  | 'missing_evidence' // 待补充结果
  | 'candidate_ready' // 已形成知识候选
  | 'completed' // 复盘完成

export type KnowledgeCandidateStatus = 'none' | 'draft' | 'pending_confirmation' | 'confirmed'

export type InsightPeriod = 'today' | 'week' | 'month'

/* 模块一：本期工作概览（自然语言总结 + 一行辅助数据，不再是数据看板） */
export const INSIGHT_OVERVIEW: Record<InsightPeriod, { summary: string; meta: string }> = {
  today: {
    summary:
      '今天你主要在推进「2026 年 618 家电会场首页改版」，完成了设计 Brief 初稿并确认首屏核心入口策略。目前有一项入口数据口径还在等待确认，暂时阻塞 Brief 定稿。',
    meta: '2 次 AI 协作 · 1 份设计 Brief 初稿 · 1 项待确认',
  },
  week: {
    summary:
      '本周你主要在推进「2026 年 618 家电会场首页改版」，已经完成历史项目检索、首屏策略分析和设计 Brief 初稿。目前还有一项入口数据口径需要确认。',
    meta: '2 次 AI 协作 · 1 份设计 Brief · 2 位同事数字分身参与',
  },
  month: {
    summary:
      '本月你完成了 3 个会场项目的历史整理，持续推进「2026 年 618 家电会场首页改版」，并注意到已完成的「消息活动日历改版」具备复盘和知识沉淀价值。',
    meta: '3 个项目推进 · 1 份设计 Brief · 1 个历史项目建议复盘',
  },
}

/* 模块二：当前项目洞察（618 仍处于项目准备阶段，只产出项目建议与待验证判断，不产出知识） */
export const CURRENT_PROJECT_INSIGHT = {
  name: '2026 年 618 家电会场首页改版',
  stage: '项目准备阶段',
  progress: [
    '找到 3 个相似历史项目',
    '引用了 2 条团队历史经验',
    '获得 2 位同事数字分身的补充',
    '已生成首页设计 Brief',
    '当前建议优先保证首屏核心入口效率',
  ],
  problem: {
    title: '入口数据口径确认耗时偏高',
    desc: '本周 2 次相关协作中，有 1 次用于反复确认入口点击口径，影响 Brief 定稿速度。',
  },
  // Skill 作为问题的轻量解决建议内嵌展示，不再单独占用一个大模块
  skill: {
    name: '项目启动 Brief Skill',
    desc: '可以在后续项目启动时自动完成历史项目检索、数据口径检查和标准 Brief 生成。',
  },
  // 待验证判断：可以展示，但明确不作为知识候选
  pendingValidation:
    '「首屏优先效率型结构」目前是待验证判断，需要在 618 项目上线后结合真实点击数据验证，暂不作为知识候选。',
}

/* 模块三：值得复盘的历史项目（已完成 · 建议复盘，本页与「我的知识」连接的核心模块） */
export const REVIEW_PROJECT = {
  name: '消息活动日历改版',
  status: '已完成 · 建议复盘',
  judgment:
    '该项目包含明确的问题诊断、模块 CTR、设计调整和项目决策记录，可能形成可复用的页面资源分配经验。',
  materials: [
    { label: '消息卡片 CTR', value: '10.53%' },
    { label: '活动日历 CTR', value: '0.50%' },
    { label: 'Feeds 大包裹 CTR', value: '2.01%' },
    { label: '改版设计方案', value: '已归档' },
    { label: '项目决策记录', value: '已归档' },
  ],
  missing: ['改版后的实际效果', '产品或业务反馈', '最终上线范围', '是否存在未达到预期的部分'],
  // 只展示可能的知识方向，不直接生成知识
  directions: [
    '页面资源如何根据用户使用价值分配',
    '低频但必要模块如何保留基础可达性',
    '模块 CTR、首屏占用与展示权重如何共同用于决策',
  ],
  candidateHint: '完成复盘后，数字人预计可以从该项目中提炼 1–3 条知识候选。',
}

/* 项目复盘四步内容（均为演示 Mock；上线结果类材料默认缺失，需用户补充后才能生成知识候选） */
export const REVIEW_FLOW = {
  // 步骤一：确认项目背景
  background: [
    { label: '项目目标', value: '优化消息页资源分配，让高频、高价值模块获得更合理的曝光与首屏可达性。' },
    {
      label: '原始问题',
      value: '活动日历模块占据消息页显著位置，但点击率仅 0.50%，挤压了高频消息卡片与 Feeds 的展示效率。',
    },
    { label: '参与人员', value: '林知夏（体验设计）、消息业务产品、前端开发' },
    { label: '项目时间', value: '2024 年 Q3' },
    { label: '最终上线方案', value: '活动日历收起为二级入口，消息卡片与 Feeds 大包裹前置到首屏可视区。' },
  ],
  // 步骤二：检查已有证据（上线结果、业务反馈默认缺失）
  evidence: [
    { label: '原始 CTR 数据', ready: true, note: '消息卡片 10.53% / 活动日历 0.50% / Feeds 2.01%' },
    { label: '改版方案', ready: true, note: '已归档设计稿' },
    { label: '设计决策', ready: true, note: '项目决策记录完整' },
    { label: '上线结果', ready: false, note: '缺少改版后的实际效果数据' },
    { label: '业务反馈', ready: false, note: '缺少产品或业务侧反馈' },
  ],
  // 步骤三：补充缺失结果
  missingHint: '当前材料不足以形成经过验证的知识，请补充项目实际结果。',
  resultPlaceholder:
    '例如：改版上线后活动日历入口点击占比、消息卡片与 Feeds 的点击变化、业务侧对本次改版的评价……',
  // 步骤四：生成知识候选（仅材料完整后可执行）
  candidateReadyHint: '已形成 1 条知识候选，等待你在「我的知识」中确认。',
  candidateTitle: '页面资源应按用户使用价值分配曝光与首屏位置',
}

/* 模块四：重复出现的工作问题（权重低于历史项目复盘机会，不使用大面积警告底色） */
export const RECURRING_PROBLEM = {
  title: '数据口径确认在多个项目中反复发生',
  desc: '最近 3 个项目都出现了入口或转化数据口径反复确认，导致项目启动阶段需要多轮沟通。',
  basis: [
    '2026 年 618 家电会场：首页入口点击口径',
    '2024 年超级品类日：楼层转化口径',
    '导购卡首屏数量测试：曝光与点击口径',
  ],
  improve:
    '将数据口径检查加入项目启动 Brief Skill，在项目启动时提前确认指标定义、时间范围和数据来源。',
}

/* ============ 协作网络 ============ */
export const COLLAB_OVERVIEW = {
  ongoing: 2,
  pendingRequests: 3,
  monthlyHelped: 9,
  receivedSupport: 6,
}

export interface HelpRequest {
  id: string
  from: string
  project: string
  knowledge: string
  expect: string
  scope: string
  risk: string
}

export const HELP_REQUESTS: HelpRequest[] = [
  {
    id: 'req-wangchen',
    from: '王晨的数字分身',
    project: '家电暑期会场改版',
    knowledge: '首屏核心入口效率',
    expect: '参考 618 项目结论，确定暑期会场首屏是否沿用效率型楼层结构。',
    scope: '家电设计组',
    risk: '两次活动的品类结构不同，建议结合暑期主推品类校准入口顺序。',
  },
  {
    id: 'req-zhaomin',
    from: '赵敏的数字分身',
    project: '小家电专场页',
    knowledge: '导购卡片首屏承载数量',
    expect: '确认小家电专场首屏导购卡数量上限。',
    scope: '家电设计组',
    risk: '小家电品类决策链更短，可适度放宽卡片数量。',
  },
  {
    id: 'req-sunhao',
    from: '孙浩的数字分身',
    project: '清凉家电会场',
    knowledge: '活动标签信息层级规范',
    expect: '希望复用标签层级规范，减少扫读成本。',
    scope: '家电设计组',
    risk: '注意暑期标签数量偏多，需启用折叠策略。',
  },
]

export const MY_COLLAB = {
  title: '查找 618 家电会场历史经验',
  participants: [
    { name: '林知夏的数字人', role: '发起', tone: 'mint' as const },
    { name: '李明的数字人', role: '会场复盘', tone: 'knowledge' as const },
    { name: '王晨的数字人', role: '首屏入口数据', tone: 'collab' as const },
    { name: '数据查询 Skill', role: '数据支持', tone: 'remind' as const },
  ],
  results: ['获得 2 个历史案例', '补充 1 条数据依据', '发现 1 项风险', '已生成项目 Brief'],
}

/* 协作时间线（技术词 → 用户语言） */
export interface TimelineNode {
  id: string
  who: string
  action: string // 用户语言
  rawType: string // 技术词，仅在详情次级展示
  detail: string
  tone: 'mint' | 'knowledge' | 'collab' | 'remind' | 'rose'
}
export const COLLAB_TIMELINE: TimelineNode[] = [
  {
    id: 'tl-1',
    who: '林知夏的数字人',
    action: '发起求助',
    rawType: 'request',
    detail: '发起 618 家电会场历史经验查询。',
    tone: 'mint',
  },
  {
    id: 'tl-2',
    who: '李明的数字人',
    action: '补充经验',
    rawType: 'evidence',
    detail: '补充 2025 年项目复盘：沉浸式头图降低首屏入口可见性。',
    tone: 'knowledge',
  },
  {
    id: 'tl-3',
    who: '王晨的数字人',
    action: '补充经验',
    rawType: 'evidence',
    detail: '补充首屏入口点击数据，量化点击下降幅度。',
    tone: 'knowledge',
  },
  {
    id: 'tl-4',
    who: '风险提醒能力',
    action: '提醒限制条件',
    rawType: 'correction',
    detail: '提醒两份数据的时间范围存在差异，需统一口径。',
    tone: 'rose',
  },
  {
    id: 'tl-5',
    who: '林知夏的数字人',
    action: '确认方案',
    rawType: 'decision',
    detail: '确认优先采用效率型首屏结构的方案方向。',
    tone: 'collab',
  },
  {
    id: 'tl-6',
    who: '林知夏的数字人',
    action: '形成新经验',
    rawType: 'memory_candidate',
    detail: '将结果提炼为「首屏核心入口效率」新经验，待本人确认。',
    tone: 'mint',
  },
]

export interface CompletedCollab {
  id: string
  title: string
  peer: string
  result: string
  time: string
}
export const COMPLETED_COLLAB: CompletedCollab[] = [
  { id: 'c-1', title: '首屏入口点击口径对齐', peer: '王晨的数字人', result: '统一近 90 天口径', time: '2 天前' },
  { id: 'c-2', title: '2025 会场复盘要点补充', peer: '李明的数字人', result: '补充 3 条复盘结论', time: '3 天前' },
  { id: 'c-3', title: '标签层级规范复用', peer: '周然的数字人', result: '应用于 PLUS 会员日', time: '5 天前' },
  { id: 'c-4', title: '导购卡数量建议', peer: '赵敏的数字人', result: '确定首屏 4–6 个', time: '1 周前' },
]

export interface RecommendedPeer {
  id: string
  name: string
  domain: string
  shareable: number
  recentProject: string
  tone: 'knowledge' | 'collab' | 'remind'
}
export const RECOMMENDED_PEERS: RecommendedPeer[] = [
  {
    id: 'peer-liming',
    name: '李明的数字人',
    domain: '营销会场、数据复盘',
    shareable: 15,
    recentProject: '2025 618 家电会场复盘',
    tone: 'knowledge',
  },
  {
    id: 'peer-wangchen',
    name: '王晨的数字人',
    domain: '首页体验、活动入口',
    shareable: 11,
    recentProject: '家电暑期会场改版',
    tone: 'collab',
  },
  {
    id: 'peer-zhouran',
    name: '周然的数字人',
    domain: '导购场景、内容策略',
    shareable: 9,
    recentProject: 'PLUS 会员日活动页',
    tone: 'remind',
  },
]

/* 数字人档案 Skill 列表 */
export const CONFIGURED_SKILLS = [
  { name: '数据查询 Skill', desc: '按场景取回首页 / 会场入口的点击与转化数据。' },
  { name: '历史项目检索 Skill', desc: '在团队 Wiki 与项目库中检索相似会场案例。' },
  { name: '复盘要点提炼 Skill', desc: '从项目复盘文档中提取关键结论与风险。' },
  { name: '设计走查 Skill', desc: '按信息层级与对比度规范检查页面稿件。' },
  { name: '会场楼层结构 Skill', desc: '根据品类与转化目标推荐楼层顺序。' },
  { name: '标签规范校验 Skill', desc: '校验活动标签的信息层级与数量。' },
]
