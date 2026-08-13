import { useEffect, useState } from 'react'
import { Check, ChevronLeft, Lightbulb, ShieldCheck, Target, PartyPopper } from 'lucide-react'
import { Modal } from '../ui/Modal'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'
import { cn } from '../../lib/cn'
import { NEW_KNOWLEDGE } from '../../data/mockData'
import { SCOPE_LABELS, useDemo, type ShareScope } from '../../store/DemoContext'

interface ConfirmKnowledgeModalProps {
  open: boolean
  onClose: () => void
}

const SCOPE_OPTIONS: { key: ShareScope; label: string; desc: string }[] = [
  { key: 'self', label: '仅自己', desc: '只用于你自己的数字人' },
  { key: 'project', label: '当前项目', desc: '618 家电会场项目内可见' },
  { key: 'group', label: '家电设计组', desc: '组内数字人可引用（推荐）' },
  { key: 'more', label: '更多团队', desc: '扩展到相关营销设计团队' },
]

const STEPS = [
  { icon: Lightbulb, label: '确认知识内容' },
  { icon: Target, label: '设置适用范围' },
  { icon: ShieldCheck, label: '设置共享权限' },
]

export function ConfirmKnowledgeModal({ open, onClose }: ConfirmKnowledgeModalProps) {
  const { confirmAndShare, knowledgeShared } = useDemo()
  const [step, setStep] = useState(0)
  const [scope, setScope] = useState<ShareScope>(NEW_KNOWLEDGE.recommendScope)
  const [applyRange, setApplyRange] = useState(NEW_KNOWLEDGE.scope)
  const [submitting, setSubmitting] = useState(false)
  const [done, setDone] = useState(false)

  // 打开时重置
  useEffect(() => {
    if (open) {
      setStep(0)
      setScope(NEW_KNOWLEDGE.recommendScope)
      setApplyRange(NEW_KNOWLEDGE.scope)
      setSubmitting(false)
      setDone(false)
    }
  }, [open])

  const handleSubmit = () => {
    setSubmitting(true)
    window.setTimeout(() => {
      confirmAndShare(scope)
      setSubmitting(false)
      setDone(true)
    }, 900)
  }

  const isFinalShare = scope !== 'self'

  const footer = done ? (
    <Button variant="primary" onClick={onClose} icon={<Check className="h-4 w-4" />}>
      完成
    </Button>
  ) : (
    <>
      {step > 0 ? (
        <Button variant="ghost" onClick={() => setStep((s) => s - 1)} icon={<ChevronLeft className="h-4 w-4" />}>
          上一步
        </Button>
      ) : (
        <Button variant="ghost" onClick={onClose}>
          取消
        </Button>
      )}
      {step < 2 ? (
        <Button variant="primary" onClick={() => setStep((s) => s + 1)}>
          下一步
        </Button>
      ) : (
        <Button variant="primary" loading={submitting} onClick={handleSubmit}>
          {isFinalShare ? '确认并共享' : '确认并仅自己使用'}
        </Button>
      )}
    </>
  )

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="lg"
      title={done ? '已完成沉淀' : '确认并沉淀新经验'}
      subtitle={done ? undefined : '由你确认知识内容、适用范围与共享权限'}
      footer={footer}
    >
      {done ? (
        <SuccessView scope={scope} shared={knowledgeShared} />
      ) : (
        <>
          {/* 步骤条 */}
          <div className="mb-6 flex items-center">
            {STEPS.map((s, i) => {
              const active = i === step
              const complete = i < step
              return (
                <div key={s.label} className="flex flex-1 items-center last:flex-none">
                  <div className="flex items-center gap-2.5">
                    <span
                      className={cn(
                        'flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold transition-colors',
                        active
                          ? 'bg-mint-400 text-[#04241c]'
                          : complete
                            ? 'bg-mint-400/20 text-mint-300'
                            : 'bg-white/[0.06] text-slate-500',
                      )}
                    >
                      {complete ? <Check className="h-4 w-4" /> : i + 1}
                    </span>
                    <span className={cn('text-sm font-medium', active ? 'text-white' : 'text-slate-500')}>
                      {s.label}
                    </span>
                  </div>
                  {i < STEPS.length - 1 && (
                    <div className={cn('mx-3 h-px flex-1', complete ? 'bg-mint-400/40' : 'bg-white/[0.08]')} />
                  )}
                </div>
              )
            })}
          </div>

          {/* 步骤内容 */}
          {step === 0 && (
            <div className="space-y-4 animate-fade-in">
              <div className="rounded-[12px] border border-mint-400/20 bg-mint-400/[0.06] p-4">
                <div className="mb-1 text-xs font-medium text-mint-300">知识结论</div>
                <h3 className="text-[15px] font-semibold text-white">{NEW_KNOWLEDGE.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-300">{NEW_KNOWLEDGE.conclusion}</p>
              </div>
              <div>
                <div className="mb-1.5 text-xs font-medium text-slate-400">解决的问题</div>
                <p className="text-sm leading-relaxed text-slate-300">{NEW_KNOWLEDGE.problem}</p>
              </div>
              <div>
                <div className="mb-2 text-xs font-medium text-slate-400">数据与案例依据</div>
                <ul className="space-y-1.5">
                  {NEW_KNOWLEDGE.evidence.map((e) => (
                    <li key={e} className="flex gap-2 text-sm text-slate-300">
                      <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-slate-500" />
                      {e}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          {step === 1 && (
            <div className="space-y-4 animate-fade-in">
              <p className="text-sm text-slate-400">明确这条经验适合被应用到什么场景，避免被误用。</p>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-400">适用范围</label>
                <input
                  value={applyRange}
                  onChange={(e) => setApplyRange(e.target.value)}
                  className="w-full rounded-[10px] border border-white/[0.08] bg-surface-1 px-3.5 py-2.5 text-sm text-slate-100 outline-none transition-colors focus:border-mint-400/50"
                />
              </div>
              <div className="rounded-[10px] border border-white/[0.06] bg-surface-1 p-4">
                <div className="mb-2 text-xs font-medium text-slate-400">来源依据</div>
                <div className="flex flex-wrap gap-2">
                  {NEW_KNOWLEDGE.sources.map((s) => (
                    <Badge key={s} tone="knowledge">
                      {s}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step === 2 && (
            <div className="space-y-3 animate-fade-in">
              <p className="text-sm text-slate-400">
                你可以选择共享范围。数字人会保留经验来源与适用范围，其他人引用时可追溯。
              </p>
              <div className="grid grid-cols-2 gap-3">
                {SCOPE_OPTIONS.map((opt) => {
                  const active = scope === opt.key
                  return (
                    <button
                      key={opt.key}
                      onClick={() => setScope(opt.key)}
                      className={cn(
                        'rounded-[12px] border p-3.5 text-left transition-all',
                        active
                          ? 'border-mint-400/50 bg-mint-400/[0.08]'
                          : 'border-white/[0.06] bg-surface-1 hover:border-white/[0.12]',
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-semibold text-slate-100">{opt.label}</span>
                        <span
                          className={cn(
                            'flex h-4 w-4 items-center justify-center rounded-full border',
                            active ? 'border-mint-400 bg-mint-400' : 'border-white/20',
                          )}
                        >
                          {active && <Check className="h-3 w-3 text-[#04241c]" />}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-slate-500">{opt.desc}</p>
                    </button>
                  )
                })}
              </div>
              <div className="flex items-start gap-2 rounded-[10px] bg-knowledge/[0.08] px-3.5 py-2.5 text-xs text-knowledge">
                <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                数字人建议：{NEW_KNOWLEDGE.recommendScope === scope ? '与 AI 推荐一致，' : ''}共享给「
                {SCOPE_LABELS[scope]}」。
              </div>
            </div>
          )}
        </>
      )}
    </Modal>
  )
}

function SuccessView({ scope, shared }: { scope: ShareScope; shared: boolean }) {
  return (
    <div className="flex flex-col items-center py-4 text-center animate-scale-in">
      <span className="flex h-16 w-16 items-center justify-center rounded-full bg-mint-400/15 text-mint-300">
        <PartyPopper className="h-8 w-8" />
      </span>
      <h3 className="mt-4 text-lg font-semibold text-white">经验已确认并沉淀</h3>
      <p className="mt-2 max-w-sm text-sm leading-relaxed text-slate-400">
        「入口型会场应优先保证首屏核心入口效率」已{scope === 'self' ? '保存为个人经验' : `共享给「${SCOPE_LABELS[scope]}」`}。
        {shared && scope !== 'self' && '组内其他数字人现在可以引用它。'}
      </p>
      <div className="mt-5 grid w-full grid-cols-2 gap-3 text-left">
        <div className="rounded-[10px] border border-white/[0.06] bg-surface-1 p-3">
          <div className="text-xs text-slate-500">待我确认</div>
          <div className="mt-1 text-sm font-medium text-slate-200">
            1 → <span className="text-mint-300">0</span>
          </div>
        </div>
        {scope !== 'self' && (
          <div className="rounded-[10px] border border-white/[0.06] bg-surface-1 p-3">
            <div className="text-xs text-slate-500">已共享经验</div>
            <div className="mt-1 text-sm font-medium text-slate-200">
              12 → <span className="text-mint-300">13</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
