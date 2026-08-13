import { useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Sparkles,
  ArrowRight,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Blocks,
  PlayCircle,
  Plus,
  BookMarked,
  Lightbulb,
  ClipboardList,
  Eye,
  Clock,
  Repeat,
  Workflow,
} from 'lucide-react'
import { PageHeader } from '../components/ui/PageHeader'
import { Card } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { SegmentedControl } from '../components/ui/SegmentedControl'
import { ProjectReviewDrawer } from '../components/insights/ProjectReviewDrawer'
import {
  INSIGHT_OVERVIEW,
  CURRENT_PROJECT_INSIGHT,
  REVIEW_PROJECT,
  RECURRING_PROBLEM,
  type InsightPeriod,
  type ReviewStatus,
  type KnowledgeCandidateStatus,
} from '../data/mockData'
import { useDemo } from '../store/DemoContext'
import { cn } from '../lib/cn'

const PERIODS = [
  { key: 'today', label: '今日' },
  { key: 'week', label: '本周' },
  { key: 'month', label: '本月' },
]

const PERIOD_LABEL: Record<InsightPeriod, string> = {
  today: '今日',
  week: '本周',
  month: '本月',
}

/** 需要在概览总结中加粗的关键词：项目名称与当前待办 */
const EMPHASIS_TERMS = ['2026 年 618 家电会场首页改版', '消息活动日历改版', '入口数据口径']

/**
 * 工作洞察：数字人主动提供的工作判断流（非数据看板）。
 * 纵向四模块：01 本期工作概览 → 02 当前项目洞察(618) → 03 值得复盘的历史项目 → 04 重复出现的工作问题。
 * 618 处于准备阶段，只产出项目建议/待验证判断；只有已完成的历史项目经复盘才产出知识候选，
 * 流入「我的知识·待我确认」。复盘状态机由本页本地持有（见修改文档 §13）。
 */
export function Insights() {
  const navigate = useNavigate()
  const { showToast } = useDemo()

  const [period, setPeriod] = useState<InsightPeriod>('week')
  const [reviewOpen, setReviewOpen] = useState(false)
  const [reviewStatus, setReviewStatus] = useState<ReviewStatus>('suggested')
  const [candidateStatus, setCandidateStatus] = useState<KnowledgeCandidateStatus>('none')

  const overview = INSIGHT_OVERVIEW[period]
  // 今日聚焦当天进展与阻塞，不强调历史复盘与长期问题（见修改文档 §12）
  const showReview = period !== 'today'

  const goWorkspace = () => navigate('/workspace')
  const viewBrief = () => {
    navigate('/workspace')
    showToast('已在 AI 工作台打开设计 Brief', 'info')
  }
  const goKnowledge = () => {
    setReviewOpen(false)
    navigate('/knowledge')
  }

  const candidateReady = reviewStatus === 'candidate_ready'
  const reviewBadge = REVIEW_BADGE[reviewStatus]

  return (
    <div className="mx-auto w-full max-w-[1240px] space-y-6">
      <PageHeader
        title="工作洞察"
        subtitle="数字人根据你的工作记录，主动判断当前进展、发现问题，并识别值得复盘、可能沉淀为新知识的项目。"
        actions={
          <SegmentedControl
            options={PERIODS}
            value={period}
            onChange={(k) => setPeriod(k as InsightPeriod)}
          />
        }
      />

      {/* ============ 01 本期工作概览 ============ */}
      <section>
        <ModuleHeading index="01" title={`${PERIOD_LABEL[period]}工作概览`} />
        <Card padding="lg">
          <div className="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div className="flex min-w-0 gap-3.5">
              <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] bg-mint-400/12 text-mint-300">
                <Sparkles className="h-[18px] w-[18px]" />
              </span>
              <div className="min-w-0">
                <p className="max-w-2xl text-[14px] leading-relaxed text-slate-200">
                  <Emphasized text={overview.summary} terms={EMPHASIS_TERMS} />
                </p>
                <div className="mt-3 text-[12px] text-slate-500">{overview.meta}</div>
              </div>
            </div>
            <div className="flex shrink-0 flex-wrap gap-2.5">
              <Button
                variant="secondary"
                iconRight={<ArrowRight className="h-4 w-4" />}
                onClick={goWorkspace}
              >
                继续当前项目
              </Button>
              <Button variant="subtle" icon={<FileText className="h-4 w-4" />} onClick={viewBrief}>
                查看 Brief
              </Button>
            </div>
          </div>
        </Card>
      </section>

      {/* ============ 02 当前项目洞察（618，准备阶段） ============ */}
      <section>
        <ModuleHeading index="02" title="当前项目洞察" />
        <section className="card-base p-6">
          <div className="flex flex-wrap items-center gap-3">
            <h3 className="text-[16px] font-semibold text-white">{CURRENT_PROJECT_INSIGHT.name}</h3>
            <Badge tone="mint" dot>
              {CURRENT_PROJECT_INSIGHT.stage}
            </Badge>
          </div>
          <p className="mt-1.5 text-[12.5px] text-slate-500">
            数字人正在用团队已有知识支持这个新项目的启动。
          </p>

          <div className="mt-5 grid gap-5 lg:grid-cols-2">
            {/* 当前进展 */}
            <div>
              <SubHeading>当前进展</SubHeading>
              <ul className="space-y-2">
                {CURRENT_PROJECT_INSIGHT.progress.map((p) => (
                  <li key={p} className="flex items-start gap-2.5 text-[13px] leading-relaxed text-slate-300">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-mint-300" />
                    {p}
                  </li>
                ))}
              </ul>
            </div>

            {/* 数字人发现的问题 + 轻量 Skill 推荐条 */}
            <div>
              <SubHeading>数字人发现的问题</SubHeading>
              <div className="rounded-[12px] border border-white/[0.06] bg-surface-1 p-4">
                <div className="flex items-start gap-2.5">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-remind" />
                  <div className="min-w-0">
                    <h4 className="text-[13.5px] font-semibold text-slate-100">
                      {CURRENT_PROJECT_INSIGHT.problem.title}
                    </h4>
                    <p className="mt-1 text-[12.5px] leading-relaxed text-slate-400">
                      {CURRENT_PROJECT_INSIGHT.problem.desc}
                    </p>
                  </div>
                </div>

                {/* Skill 作为具体解决建议内嵌，不再单独占用大模块 */}
                <div className="mt-3 flex items-start gap-2.5 rounded-[10px] border border-knowledge/20 bg-knowledge/[0.05] px-3.5 py-3">
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-knowledge/15 text-knowledge">
                    <Blocks className="h-3.5 w-3.5" />
                  </span>
                  <div className="min-w-0">
                    <div className="text-[12.5px] font-medium text-slate-200">
                      可用能力 · {CURRENT_PROJECT_INSIGHT.skill.name}
                    </div>
                    <p className="mt-0.5 text-[12px] leading-relaxed text-slate-500">
                      {CURRENT_PROJECT_INSIGHT.skill.desc}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* 待验证判断：可展示但明确不作为知识候选 */}
          <div className="mt-4 rounded-[10px] border border-white/[0.05] bg-white/[0.02] px-4 py-3">
            <div className="mb-1 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-slate-500">
              <Clock className="h-3 w-3" />
              待验证判断
            </div>
            <p className="text-[12.5px] leading-relaxed text-slate-400">
              {CURRENT_PROJECT_INSIGHT.pendingValidation}
            </p>
          </div>

          {/* 操作：均为次级 / 轻量，主按钮权重留给「开始项目复盘」 */}
          <div className="mt-5 flex flex-wrap gap-2.5">
            <Button variant="secondary" icon={<PlayCircle className="h-4 w-4" />} onClick={goWorkspace}>
              继续项目
            </Button>
            <Button
              variant="subtle"
              icon={<Sparkles className="h-4 w-4" />}
              onClick={() => showToast('已将「项目启动 Brief Skill」应用到当前项目（演示）')}
            >
              应用 Skill
            </Button>
            <Button
              variant="subtle"
              icon={<Plus className="h-4 w-4" />}
              onClick={() => showToast('已创建「入口数据口径确认」任务（演示）', 'info')}
            >
              创建数据确认任务
            </Button>
          </div>
        </section>
      </section>

      {/* ============ 03 值得复盘的历史项目（L1 最高权重） ============ */}
      {showReview && (
        <section>
          <ModuleHeading index="03" title="值得复盘的历史项目" hero />
          <section className="card-base border-knowledge/25 bg-knowledge/[0.035] p-6">
            {/* 已形成知识候选后的成功条（含唯一主按钮：前往我的知识） */}
            {candidateReady && (
              <div className="mb-5 flex flex-wrap items-center gap-3 rounded-[12px] border border-mint-400/25 bg-mint-400/[0.08] px-4 py-3 animate-fade-in">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-mint-300" />
                <span className="min-w-0 flex-1 text-[13px] font-medium text-slate-100">
                  已形成 1 条知识候选，等待你在「我的知识」中确认。
                </span>
                <Button
                  variant="primary"
                  size="sm"
                  icon={<BookMarked className="h-4 w-4" />}
                  onClick={goKnowledge}
                >
                  前往我的知识
                </Button>
              </div>
            )}

            {/* 头部：项目名 + 数字人判断 + 状态徽章 */}
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex min-w-0 gap-3.5">
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[12px] bg-knowledge/15 text-knowledge">
                  <BookMarked className="h-[22px] w-[22px]" />
                </span>
                <div className="min-w-0">
                  <h3 className="text-[18px] font-bold text-white">{REVIEW_PROJECT.name}</h3>
                  <p className="mt-1 max-w-2xl text-[13px] leading-relaxed text-slate-300">
                    {REVIEW_PROJECT.judgment}
                  </p>
                </div>
              </div>
              <Badge tone={reviewBadge.tone} dot>
                {reviewBadge.label}
              </Badge>
            </div>

            {/* 主体：左=已有材料，右=待补充 + 知识方向 */}
            <div className="mt-5 grid gap-6 lg:grid-cols-[1.15fr_1fr]">
              <div>
                <SubHeading>已有材料</SubHeading>
                <div className="grid gap-2 sm:grid-cols-2">
                  {REVIEW_PROJECT.materials.map((m) => (
                    <div
                      key={m.label}
                      className="flex items-center justify-between gap-2 rounded-[9px] border border-white/[0.06] bg-surface-1 px-3 py-2"
                    >
                      <span className="truncate text-[12.5px] text-slate-400">{m.label}</span>
                      <span className="shrink-0 text-[12.5px] font-semibold tabular-nums text-slate-200">
                        {m.value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <SubHeading>待补充材料</SubHeading>
                  <ul className="space-y-1.5">
                    {REVIEW_PROJECT.missing.map((m) => (
                      <li key={m} className="flex items-start gap-2 text-[13px] leading-relaxed text-slate-400">
                        <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-remind/60" />
                        {m}
                      </li>
                    ))}
                  </ul>
                </div>
                <div>
                  <SubHeading>可能形成的知识方向</SubHeading>
                  <ul className="space-y-1.5">
                    {REVIEW_PROJECT.directions.map((d) => (
                      <li key={d} className="flex items-start gap-2 text-[13px] leading-relaxed text-slate-300">
                        <Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0 text-knowledge/80" />
                        {d}
                      </li>
                    ))}
                  </ul>
                  <p className="mt-2.5 text-[12px] leading-relaxed text-slate-500">
                    {REVIEW_PROJECT.candidateHint}
                  </p>
                </div>
              </div>
            </div>

            {/* 操作：开始项目复盘 = 页面唯一主按钮 */}
            <div className="mt-6 flex flex-wrap items-center gap-2.5 border-t border-white/[0.06] pt-5">
              {candidateReady ? (
                <Button
                  variant="secondary"
                  icon={<ClipboardList className="h-4 w-4" />}
                  onClick={() => setReviewOpen(true)}
                >
                  继续查看复盘
                </Button>
              ) : (
                <Button
                  variant="primary"
                  size="lg"
                  icon={<ClipboardList className="h-[18px] w-[18px]" />}
                  onClick={() => setReviewOpen(true)}
                >
                  开始项目复盘
                </Button>
              )}
              <Button
                variant="subtle"
                icon={<Eye className="h-4 w-4" />}
                onClick={() => showToast('已打开「消息活动日历改版」项目材料（演示）', 'info')}
              >
                查看项目材料
              </Button>
              <Button
                variant="ghost"
                icon={<Clock className="h-4 w-4" />}
                onClick={() => showToast('已暂缓该项目复盘（演示）', 'info')}
              >
                暂后处理
              </Button>
            </div>
          </section>
        </section>
      )}

      {/* ============ 04 重复出现的工作问题（L4，权重最低） ============ */}
      {showReview && (
        <section>
          <ModuleHeading index="04" title="重复出现的工作问题" />
          <section className="card-base relative overflow-hidden p-5 pl-6">
            {/* 左侧色条替代大面积警告底色 */}
            <span className="absolute left-0 top-0 h-full w-[3px] bg-remind/40" />
            <div className="flex items-start gap-3">
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-remind/12 text-remind">
                <Repeat className="h-4 w-4" />
              </span>
              <div className="min-w-0 flex-1">
                <h3 className="text-[15px] font-semibold text-slate-100">{RECURRING_PROBLEM.title}</h3>
                <p className="mt-1.5 text-[13px] leading-relaxed text-slate-400">
                  {RECURRING_PROBLEM.desc}
                </p>

                <div className="mt-4">
                  <SubHeading>判断依据</SubHeading>
                  <ul className="space-y-1.5">
                    {RECURRING_PROBLEM.basis.map((b) => (
                      <li key={b} className="flex items-start gap-2 text-[12.5px] leading-relaxed text-slate-400">
                        <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-slate-600" />
                        {b}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="mt-4 flex items-start gap-2.5 rounded-[10px] border border-knowledge/15 bg-knowledge/[0.04] px-3.5 py-3">
                  <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-knowledge" />
                  <div className="min-w-0">
                    <div className="mb-0.5 text-[11px] font-medium uppercase tracking-wide text-knowledge/90">
                      推荐改进
                    </div>
                    <p className="text-[12.5px] leading-relaxed text-slate-300">
                      {RECURRING_PROBLEM.improve}
                    </p>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-2.5">
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={<Eye className="h-3.5 w-3.5" />}
                    onClick={() => showToast('已展开数据口径问题的判断依据（演示）', 'info')}
                  >
                    查看判断依据
                  </Button>
                  <Button
                    variant="subtle"
                    size="sm"
                    icon={<Workflow className="h-3.5 w-3.5" />}
                    onClick={() => showToast('已将数据口径检查加入项目启动流程（演示）')}
                  >
                    加入项目流程
                  </Button>
                </div>
              </div>
            </div>
          </section>
        </section>
      )}

      {/* 底部说明：解释工作洞察与我的知识的连接 */}
      <div className="flex items-start gap-2 pt-1 text-[12px] leading-relaxed text-slate-600">
        <FileText className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        洞察基于你的工作记录与 AI 协作日志自动生成。当前项目仅形成项目建议与待验证判断；
        只有已完成项目经过复盘、补充真实结果后，才会形成知识候选，进入「我的知识」等待你确认。
      </div>

      <ProjectReviewDrawer
        open={reviewOpen}
        onClose={() => setReviewOpen(false)}
        reviewStatus={reviewStatus}
        candidateStatus={candidateStatus}
        onStatusChange={(review, candidate) => {
          setReviewStatus(review)
          setCandidateStatus(candidate)
        }}
        onGoKnowledge={goKnowledge}
      />
    </div>
  )
}

/* ---------- 复盘状态 → 徽章文案与色调 ---------- */
const REVIEW_BADGE: Record<ReviewStatus, { label: string; tone: 'knowledge' | 'collab' | 'remind' | 'mint' }> = {
  suggested: { label: REVIEW_PROJECT.status, tone: 'knowledge' },
  in_progress: { label: '复盘中', tone: 'collab' },
  missing_evidence: { label: '复盘中 · 待补充结果', tone: 'remind' },
  candidate_ready: { label: '已形成知识候选', tone: 'mint' },
  completed: { label: '复盘完成', tone: 'mint' },
}

/* ---------- 模块序号标题（建立纵向阅读节奏，L1 复盘模块高亮序号） ---------- */
function ModuleHeading({ index, title, hero }: { index: string; title: string; hero?: boolean }) {
  return (
    <div className="mb-3 flex items-baseline gap-2.5">
      <span className={cn('text-[12px] font-semibold tabular-nums', hero ? 'text-knowledge' : 'text-slate-600')}>
        {index}
      </span>
      <h2 className={cn('font-semibold text-slate-100', hero ? 'text-[16px]' : 'text-[15px]')}>{title}</h2>
    </div>
  )
}

/* ---------- 卡内小节标题 ---------- */
function SubHeading({ children }: { children: ReactNode }) {
  return (
    <div className="mb-2.5 text-[11px] font-medium uppercase tracking-wide text-slate-500">{children}</div>
  )
}

/* ---------- 在自然语言总结中加粗关键词 ---------- */
function escapeRegExp(s: string) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}
function Emphasized({ text, terms }: { text: string; terms: string[] }) {
  const valid = terms.filter(Boolean)
  if (!valid.length) return <>{text}</>
  const re = new RegExp(`(${valid.map(escapeRegExp).join('|')})`, 'g')
  return (
    <>
      {text.split(re).map((part, i) =>
        valid.includes(part) ? (
          <strong key={i} className="font-semibold text-white">
            {part}
          </strong>
        ) : (
          <span key={i}>{part}</span>
        ),
      )}
    </>
  )
}
