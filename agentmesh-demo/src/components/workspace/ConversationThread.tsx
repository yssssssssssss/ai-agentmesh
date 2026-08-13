import { useState } from 'react'
import { Sparkles, ChevronDown, FileText, ArrowRight } from 'lucide-react'
import { Avatar } from '../ui/Avatar'
import { DigitalHumanMark } from '../ui/DigitalHumanMark'
import { BRIEF, WORKSPACE_REFERENCES, type WorkspaceRef } from '../../data/mockData'
import { useDemo } from '../../store/DemoContext'
import { cn } from '../../lib/cn'

interface ConversationThreadProps {
  onOpenRef: (ref: WorkspaceRef) => void
  onOpenProcess: () => void
  onOpenBrief: () => void
  onOpenConfirm: () => void
  activeRefId?: string
}

/* ---------- 分析步骤：资料以内联文本链接呈现，点击沿用右侧详情面板 ---------- */

const refById = (id: string): WorkspaceRef => {
  const r = WORKSPACE_REFERENCES.find((x) => x.id === id)
  if (!r) throw new Error(`未找到引用 ${id}`)
  return r
}

type Seg = string | { ref: WorkspaceRef }
interface AnalysisStep {
  title: string
  desc: Seg[]
}

const ANALYSIS_SUMMARY =
  '检索了 3 个相似项目、2 条团队经验和近 90 天入口数据，并获得 2 位同事数字分身的补充。'

const ANALYSIS_STEPS: AnalysisStep[] = [
  {
    title: '理解任务',
    desc: ['结合历史项目和近期数据，判断今年会场首屏的设计方向。'],
  },
  {
    title: '查找相似项目',
    desc: ['找到 ', { ref: refById('ref-2025') }, '、', { ref: refById('ref-2024') }, ' 等 3 个相关项目。'],
  },
  {
    title: '检索团队经验',
    desc: ['检索到 2 条与首屏入口效率相关的团队经验。'],
  },
  {
    title: '查询近期数据',
    desc: ['调用数据查询 Skill，读取近 90 天 ', { ref: refById('ref-data') }, '。'],
  },
  {
    title: '请求数字分身协作',
    desc: ['李明和王晨的数字分身参与协作，补充了 ', { ref: refById('ref-liming') }, ' 与数据口径。'],
  },
]

/** 数字人建议中的三条调整方向 */
const ADJUSTMENTS = [
  '首屏优先展示重点品类和核心活动入口；',
  '使用效率型楼层结构，减少纯氛围内容占用；',
  '如果需要保留沉浸式头图，控制展示高度，并结合入口点击数据进一步验证。',
]

/** 结束状态的轻量追问建议 */
const FOLLOWUPS = ['继续补充重点商品入口方案', '对比两种首屏结构', '创建后续任务']

export function ConversationThread({ onOpenRef, onOpenBrief, activeRefId }: ConversationThreadProps) {
  const { showToast } = useDemo()

  return (
    <div className="space-y-6">
      {/* 任务标题 */}
      <div className="border-b border-white/[0.06] pb-4">
        <div className="flex items-center gap-2 text-[11px] font-medium uppercase tracking-wide text-slate-500">
          <Sparkles className="h-3.5 w-3.5 text-mint-300" />
          当前任务
        </div>
        <h1 className="mt-1.5 text-[19px] font-bold tracking-tight text-white">
          2026 年 618 家电会场首页改版
        </h1>
      </div>

      {/* 用户提问 */}
      <div className="flex justify-end gap-3">
        <div className="max-w-[85%] rounded-[14px] rounded-tr-sm bg-surface-3 px-4 py-3 text-[14px] leading-relaxed text-slate-100">
          我要做今年 618 家电会场首页改版,帮我找一下过去有没有类似项目经验,并给出首屏设计建议。
        </div>
        <Avatar name="林知夏" tone="mint" />
      </div>

      {/* 数字人回答：分析卡 → 直接回答 → Brief 附件（同一条消息） */}
      <div className="flex gap-3">
        <DigitalHumanMark size={38} online={false} className="mt-0.5" />
        <div className="min-w-0 flex-1 space-y-4">
          {/* 一、数字人分析：默认收起，展开后在卡内显示步骤与资料 */}
          <AnalysisModule onOpenRef={onOpenRef} activeRefId={activeRefId} />

          {/* 二、数字人直接回答：不加外层卡片，视觉权重最高 */}
          <div className="space-y-4 text-[14px] leading-[1.75] text-slate-100">
            <p>
              结合历史项目和近期入口数据，我建议今年优先采用
              <strong className="font-semibold text-mint-200">效率型首屏结构</strong>。
            </p>
            <p className="text-slate-200">
              沉浸式头图虽然能够增强会场氛围，但会压缩重点商品和活动入口的首屏可见性。对于本次以品类分流和重点商品承接为主要目标的会场，更适合先保证核心入口效率。
            </p>
            <div className="text-slate-200">
              <div className="mb-2">具体可以从三个方向调整：</div>
              <ol className="space-y-2">
                {ADJUSTMENTS.map((item, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="shrink-0 font-semibold tabular-nums text-mint-300">{i + 1}.</span>
                    <span className="flex-1">{item}</span>
                  </li>
                ))}
              </ol>
            </div>
            <p className="text-slate-200">我已经根据这些结论整理了一份首页设计 Brief：</p>
          </div>

          {/* 三、Brief 附件：紧凑文件卡，紧跟回答之后 */}
          <BriefAttachment onOpenBrief={onOpenBrief} />

          {/* 四、结束状态：低权重说明 + 轻量追问 */}
          <div className="space-y-2.5 pt-0.5">
            <p className="text-[12px] leading-relaxed text-slate-500">
              本次引用的团队经验和资料来源已记录在 Brief 中。
            </p>
            <div className="flex flex-wrap gap-2">
              {FOLLOWUPS.map((f) => (
                <button
                  key={f}
                  onClick={() => showToast(`${f}（演示）`, 'info')}
                  className="rounded-pill border border-white/[0.08] bg-surface-1 px-3 py-1.5 text-[12.5px] text-slate-400 transition-colors hover:border-white/[0.18] hover:bg-surface-2 hover:text-slate-200"
                >
                  {f}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ---------- 一、数字人分析（默认收起的低权重卡片） ---------- */

function AnalysisModule({
  onOpenRef,
  activeRefId,
}: {
  onOpenRef: (ref: WorkspaceRef) => void
  activeRefId?: string
}) {
  const [open, setOpen] = useState(false)
  return (
    <div className="rounded-[12px] border border-white/[0.06] bg-surface-1/70">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start gap-2.5 px-3.5 py-2.5 text-left"
      >
        <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-white/[0.05] text-slate-400">
          <Sparkles className="h-3 w-3" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-[13px] font-medium text-slate-300">数字人已完成分析</div>
          {!open && (
            <div className="mt-0.5 line-clamp-1 text-[12px] leading-snug text-slate-500">
              {ANALYSIS_SUMMARY}
            </div>
          )}
        </div>
        <span className="mt-0.5 flex shrink-0 items-center gap-1 text-[12px] text-slate-500">
          {open ? '收起' : '展开分析'}
          <ChevronDown className={cn('h-3.5 w-3.5 transition-transform', open && 'rotate-180')} />
        </span>
      </button>

      {open && (
        <div className="border-t border-white/[0.06] px-3.5 py-3">
          <ol className="space-y-2.5">
            {ANALYSIS_STEPS.map((step, i) => (
              <li key={step.title} className="flex gap-2.5">
                <span className="mt-[3px] flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-white/[0.06] text-[10px] font-medium tabular-nums text-slate-400">
                  {i + 1}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="text-[12.5px] font-medium text-slate-300">{step.title}</div>
                  <p className="mt-0.5 text-[12.5px] leading-relaxed text-slate-500">
                    {step.desc.map((seg, j) =>
                      typeof seg === 'string' ? (
                        <span key={j}>{seg}</span>
                      ) : (
                        <RefLink
                          key={j}
                          refItem={seg.ref}
                          active={activeRefId === seg.ref.id}
                          onClick={() => onOpenRef(seg.ref)}
                        />
                      ),
                    )}
                  </p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  )
}

/* 内联资料链接：轻量文字链，点击打开右侧详情面板 */
function RefLink({
  refItem,
  active,
  onClick,
}: {
  refItem: WorkspaceRef
  active: boolean
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'mx-0.5 rounded-[3px] underline decoration-dotted underline-offset-2 transition-colors',
        active
          ? 'text-mint-200 decoration-mint-300'
          : 'text-mint-300/90 decoration-mint-400/40 hover:text-mint-200 hover:decoration-mint-300',
      )}
    >
      {refItem.title}
    </button>
  )
}

/* ---------- 三、Brief 附件（紧凑文件卡） ---------- */

function BriefAttachment({ onOpenBrief }: { onOpenBrief: () => void }) {
  return (
    <button
      onClick={onOpenBrief}
      className="group flex w-full items-center gap-3.5 rounded-[12px] border border-white/[0.07] bg-surface-1 px-4 py-4 text-left transition-colors hover:border-white/[0.16] hover:bg-surface-2"
    >
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[10px] bg-knowledge/12 text-knowledge">
        <FileText className="h-5 w-5" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-[14px] font-semibold text-slate-100">{BRIEF.title}</span>
          <span className="shrink-0 text-[12px] text-slate-500">已生成 · 6 个模块</span>
        </div>
        <p className="mt-1 truncate text-[12.5px] text-slate-500">
          项目目标、历史经验、核心问题、设计原则、推荐方向和数据依据
        </p>
      </div>
      <span className="flex shrink-0 items-center gap-1 text-[12.5px] font-medium text-slate-400 transition-colors group-hover:text-slate-200">
        查看
        <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
      </span>
    </button>
  )
}
