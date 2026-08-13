import { useState } from 'react'
import {
  X,
  History,
  Lightbulb,
  BarChart3,
  UserRound,
  Workflow,
  FileText,
  ExternalLink,
  ChevronDown,
  ArrowUpRight,
  TrendingDown,
  TrendingUp,
  Sparkles,
} from 'lucide-react'
import {
  WORKSPACE_ANALYSIS,
  WORKSPACE_TECH_LOG,
  BRIEF,
  type WorkspaceRef,
} from '../../data/mockData'
import { useDemo } from '../../store/DemoContext'
import { cn } from '../../lib/cn'

export type DetailContent =
  | { kind: 'ref'; ref: WorkspaceRef }
  | { kind: 'process' }
  | { kind: 'brief' }

const KIND_META: Record<
  WorkspaceRef['kind'] | 'process' | 'brief',
  { icon: typeof History; label: string; tone: string }
> = {
  project: { icon: History, label: '历史项目', tone: 'text-knowledge' },
  experience: { icon: Lightbulb, label: '团队经验', tone: 'text-mint-300' },
  data: { icon: BarChart3, label: '数据来源', tone: 'text-remind' },
  peer: { icon: UserRound, label: '同事数字分身', tone: 'text-collab' },
  process: { icon: Workflow, label: '本次工作过程', tone: 'text-mint-300' },
  brief: { icon: FileText, label: '工作产物', tone: 'text-mint-300' },
}

export function DetailPanel({
  content,
  onClose,
}: {
  content: DetailContent | null
  onClose: () => void
}) {
  const meta = content
    ? KIND_META[content.kind === 'ref' ? content.ref.kind : content.kind]
    : null
  const Icon = meta?.icon ?? FileText

  const title =
    content?.kind === 'ref'
      ? content.ref.title
      : content?.kind === 'process'
        ? '本次工作过程'
        : content?.kind === 'brief'
          ? BRIEF.title
          : ''
  const chip =
    content?.kind === 'ref'
      ? content.ref.chip
      : content?.kind === 'process'
        ? '数字人如何完成这次任务'
        : content?.kind === 'brief'
          ? '数字人生成 · 项目启动 Brief'
          : ''

  return (
    <div
      className={cn(
        'absolute right-0 top-0 z-20 flex h-full w-[440px] flex-col border-l border-white/[0.08] bg-base shadow-[-24px_0_48px_-24px_rgba(0,0,0,0.6)] transition-transform duration-300 ease-out',
        content ? 'translate-x-0' : 'pointer-events-none translate-x-full',
      )}
    >
      {/* 头部 */}
      <div className="flex items-start gap-3 border-b border-white/[0.06] px-5 py-4">
        <div className={cn('mt-0.5 rounded-[10px] bg-white/[0.05] p-2', meta?.tone)}>
          <Icon className="h-4 w-4" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[13px] font-semibold leading-snug text-slate-100">{title}</div>
          {chip && <div className="mt-0.5 text-[11px] text-slate-500">{chip}</div>}
        </div>
        <button
          onClick={onClose}
          className="shrink-0 rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-white/[0.06] hover:text-slate-200"
          aria-label="关闭"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* 主体（独立滚动） */}
      <div className="flex-1 overflow-y-auto px-5 py-5">
        {content?.kind === 'ref' && <RefBody refItem={content.ref} />}
        {content?.kind === 'process' && <ProcessBody />}
        {content?.kind === 'brief' && <BriefBody />}
      </div>
    </div>
  )
}

/* ---------- 通用小组件 ---------- */

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="text-[13px] leading-relaxed text-slate-300">{children}</div>
    </div>
  )
}

function PanelAction({
  icon: ActionIcon,
  label,
  onClick,
}: {
  icon: typeof ExternalLink
  label: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="mt-1 flex w-full items-center justify-center gap-1.5 rounded-[10px] border border-white/[0.08] bg-surface-1 px-4 py-2.5 text-[13px] font-medium text-slate-200 transition-colors hover:border-white/[0.16] hover:bg-surface-2"
    >
      <ActionIcon className="h-3.5 w-3.5" />
      {label}
    </button>
  )
}

/* ---------- 引用详情：按 kind 分支 ---------- */

function RefBody({ refItem }: { refItem: WorkspaceRef }) {
  const { showToast } = useDemo()

  if (refItem.kind === 'project') {
    const d = refItem.detail
    return (
      <div className="space-y-5">
        <Field label="项目背景">{d.background}</Field>
        <Field label="核心问题">{d.problem}</Field>
        <Field label="设计方案">{d.solution}</Field>
        <Field label="结果数据">
          <span className="text-slate-200">{d.result}</span>
        </Field>
        <div className="rounded-[12px] border border-mint-400/20 bg-mint-400/[0.06] px-4 py-3">
          <div className="mb-1 flex items-center gap-1.5 text-[11px] font-medium text-mint-300">
            <Sparkles className="h-3 w-3" />
            与当前任务的关联
          </div>
          <div className="text-[13px] leading-relaxed text-slate-300">{d.relation}</div>
        </div>
        <PanelAction
          icon={ExternalLink}
          label="查看原始资料"
          onClick={() => showToast('已打开原始项目资料（演示）', 'info')}
        />
      </div>
    )
  }

  if (refItem.kind === 'experience') {
    const d = refItem.detail
    return (
      <div className="space-y-5">
        <div className="rounded-[12px] border border-mint-400/20 bg-mint-400/[0.06] px-4 py-3">
          <div className="mb-1 text-[11px] font-medium text-mint-300">经验结论</div>
          <div className="text-[13px] leading-relaxed text-slate-200">{d.conclusion}</div>
        </div>
        <Field label="来源项目">
          <div className="flex flex-wrap gap-1.5">
            {d.sourceProjects.map((p) => (
              <span
                key={p}
                className="rounded-pill bg-white/[0.05] px-2.5 py-1 text-[12px] text-slate-300"
              >
                {p}
              </span>
            ))}
          </div>
        </Field>
        <Field label="适用范围">{d.scope}</Field>
        <Field label="最近验证时间">{d.lastVerified}</Field>
        <Field label="哪些项目引用过">
          <ul className="space-y-1.5">
            {d.citedBy.map((c) => (
              <li key={c} className="flex items-center gap-2">
                <span className="h-1 w-1 rounded-full bg-mint-400/70" />
                {c}
              </li>
            ))}
          </ul>
        </Field>
      </div>
    )
  }

  if (refItem.kind === 'data') {
    const d = refItem.detail
    return (
      <div className="space-y-5">
        <Field label="数据范围">{d.range}</Field>
        <div>
          <div className="mb-2 text-[11px] font-medium uppercase tracking-wide text-slate-500">
            核心指标
          </div>
          <div className="space-y-2">
            {d.metrics.map((m) => (
              <div
                key={m.label}
                className="flex items-center justify-between rounded-[10px] border border-white/[0.06] bg-surface-1 px-3 py-2.5"
              >
                <div className="min-w-0">
                  <div className="text-[13px] text-slate-200">{m.label}</div>
                  <div className="text-[11px] text-slate-500">{m.value}</div>
                </div>
                {m.delta && (
                  <span
                    className={cn(
                      'flex shrink-0 items-center gap-1 rounded-pill px-2 py-1 text-[12px] font-semibold',
                      m.delta.startsWith('-')
                        ? 'bg-rose/10 text-rose'
                        : 'bg-mint-400/10 text-mint-300',
                    )}
                  >
                    {m.delta.startsWith('-') ? (
                      <TrendingDown className="h-3 w-3" />
                    ) : (
                      <TrendingUp className="h-3 w-3" />
                    )}
                    {m.delta}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-[12px] border border-mint-400/20 bg-mint-400/[0.06] px-4 py-3">
          <div className="mb-1 text-[11px] font-medium text-mint-300">关键结论</div>
          <div className="text-[13px] leading-relaxed text-slate-300">{d.conclusion}</div>
        </div>
        <Field label="数据时间">{d.time}</Field>
        <Field label="口径说明">{d.caliber}</Field>
        <PanelAction
          icon={ExternalLink}
          label="查看原始数据"
          onClick={() => showToast('已打开原始数据看板（演示）', 'info')}
        />
      </div>
    )
  }

  // peer
  const d = refItem.detail
  return (
    <div className="space-y-5">
      <Field label="角色和擅长领域">{d.field}</Field>
      <Field label="引用了哪条经验">{d.citedExperience}</Field>
      <div className="rounded-[12px] border border-collab/25 bg-collab/[0.06] px-4 py-3">
        <div className="mb-1 text-[11px] font-medium text-collab">具体贡献的判断</div>
        <div className="text-[13px] leading-relaxed text-slate-200">{d.contribution}</div>
      </div>
      <Field label="知识来源">{d.knowledgeSource}</Field>
      <PanelAction
        icon={ArrowUpRight}
        label="发起进一步协作"
        onClick={() => showToast('已向该数字分身发起协作邀请（演示）', 'info')}
      />
    </div>
  )
}

/* ---------- 本次工作过程 ---------- */

function ProcessBody() {
  const [showTech, setShowTech] = useState(false)
  const a = WORKSPACE_ANALYSIS
  return (
    <div className="space-y-5">
      <Field label="检索了什么">{a.retrieved}</Field>
      <Field label="调用了哪个 Skill">{a.skill}</Field>
      <div>
        <div className="mb-2 text-[11px] font-medium uppercase tracking-wide text-slate-500">
          向哪些数字分身发起协作 · 各自贡献
        </div>
        <div className="space-y-2">
          {a.peers.map((p) => (
            <div
              key={p.name}
              className="rounded-[10px] border border-white/[0.06] bg-surface-1 px-3 py-2.5"
            >
              <div className="mb-1 flex items-center gap-1.5 text-[13px] font-medium text-collab">
                <UserRound className="h-3.5 w-3.5" />
                {p.name}
              </div>
              <div className="text-[12px] leading-relaxed text-slate-300">{p.contribution}</div>
            </div>
          ))}
        </div>
      </div>
      <div className="rounded-[12px] border border-mint-400/20 bg-mint-400/[0.06] px-4 py-3">
        <div className="mb-1 text-[11px] font-medium text-mint-300">最终如何形成结论</div>
        <div className="text-[13px] leading-relaxed text-slate-300">{a.conclusion}</div>
      </div>

      {/* 技术细节：二级折叠，默认收起 */}
      <div className="rounded-[12px] border border-white/[0.06] bg-surface-1">
        <button
          onClick={() => setShowTech((v) => !v)}
          className="flex w-full items-center justify-between px-4 py-3 text-left"
        >
          <span className="text-[12px] font-medium text-slate-400">技术执行细节</span>
          <ChevronDown
            className={cn(
              'h-4 w-4 text-slate-500 transition-transform',
              showTech && 'rotate-180',
            )}
          />
        </button>
        {showTech && (
          <div className="space-y-2 border-t border-white/[0.06] px-4 py-3">
            {WORKSPACE_TECH_LOG.map((t) => (
              <div key={t.label}>
                <div className="text-[11px] font-medium text-slate-400">{t.label}</div>
                <div className="mt-0.5 font-mono text-[11px] leading-relaxed text-slate-500">
                  {t.detail}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

/* ---------- Brief 预览 ---------- */

function BriefBody() {
  const { showToast } = useDemo()
  return (
    <div className="space-y-5">
      <Field label="项目目标">{BRIEF.goal}</Field>
      <Field label="历史背景">
        <ul className="space-y-1.5">
          {BRIEF.history.map((h, i) => (
            <li key={i} className="flex gap-2">
              <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-slate-500" />
              {h}
            </li>
          ))}
        </ul>
      </Field>
      <Field label="核心问题">{BRIEF.problem}</Field>
      <Field label="设计原则">
        <ol className="space-y-1.5">
          {BRIEF.principles.map((p, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-mint-300">{i + 1}.</span>
              <span>{p}</span>
            </li>
          ))}
        </ol>
      </Field>
      <Field label="设计方向">
        <ul className="space-y-1.5">
          {BRIEF.direction.map((d, i) => (
            <li key={i} className="flex gap-2">
              <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-mint-400/70" />
              {d}
            </li>
          ))}
        </ul>
      </Field>
      <Field label="数据支撑">
        <ul className="space-y-1.5">
          {BRIEF.data.map((d, i) => (
            <li key={i} className="flex gap-2">
              <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-remind/70" />
              {d}
            </li>
          ))}
        </ul>
      </Field>
      <div className="flex gap-2">
        <PanelAction
          icon={FileText}
          label="导出 Brief"
          onClick={() => showToast('Brief 已导出（演示）', 'success')}
        />
      </div>
    </div>
  )
}
