import { Lightbulb, AlertCircle, FolderClock, BarChart3, Target, Sparkles, Check, Pencil, User, X } from 'lucide-react'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { NEW_KNOWLEDGE } from '../../data/mockData'
import { SCOPE_LABELS, useDemo } from '../../store/DemoContext'

interface PendingKnowledgeCardProps {
  onConfirm: () => void
}

function Field({
  icon,
  label,
  children,
}: {
  icon: React.ReactNode
  label: string
  children: React.ReactNode
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-center gap-1.5 text-xs font-medium text-slate-500">
        <span className="text-slate-400">{icon}</span>
        {label}
      </div>
      <div className="text-sm leading-relaxed text-slate-300">{children}</div>
    </div>
  )
}

export function PendingKnowledgeCard({ onConfirm }: PendingKnowledgeCardProps) {
  const { confirmAndShare, showToast } = useDemo()

  return (
    <div className="relative overflow-hidden rounded-card border border-mint-400/25 bg-gradient-to-br from-mint-400/[0.07] to-transparent p-6">
      <div className="pointer-events-none absolute -right-12 -top-12 h-40 w-40 rounded-full bg-mint-400/[0.06] blur-3xl" />
      <div className="relative">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div className="flex items-start gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[12px] bg-mint-400/15 text-mint-300">
              <Lightbulb className="h-5 w-5" />
            </span>
            <div>
              <h2 className="text-lg font-semibold text-white">{NEW_KNOWLEDGE.title}</h2>
              <p className="mt-1 text-sm leading-relaxed text-slate-300">{NEW_KNOWLEDGE.conclusion}</p>
            </div>
          </div>
          <Badge tone="remind" dot>
            待确认
          </Badge>
        </div>

        <div className="grid grid-cols-1 gap-5 rounded-[12px] bg-black/20 p-5 md:grid-cols-2">
          <Field icon={<AlertCircle className="h-3.5 w-3.5" />} label="解决的问题">
            {NEW_KNOWLEDGE.problem}
          </Field>
          <Field icon={<Target className="h-3.5 w-3.5" />} label="适用范围">
            <Badge tone="knowledge">{NEW_KNOWLEDGE.scope}</Badge>
          </Field>
          <Field icon={<FolderClock className="h-3.5 w-3.5" />} label="来源项目">
            <div className="flex flex-wrap gap-1.5">
              {NEW_KNOWLEDGE.sources.map((s) => (
                <Badge key={s} tone="neutral">
                  {s}
                </Badge>
              ))}
            </div>
          </Field>
          <Field icon={<Sparkles className="h-3.5 w-3.5" />} label="AI 推荐的共享范围">
            <span className="inline-flex items-center gap-1.5 text-mint-300">
              <Check className="h-4 w-4" />
              建议共享给「{SCOPE_LABELS[NEW_KNOWLEDGE.recommendScope]}」
            </span>
          </Field>
          <div className="md:col-span-2">
            <Field icon={<BarChart3 className="h-3.5 w-3.5" />} label="数据与案例依据">
              <ul className="space-y-1.5">
                {NEW_KNOWLEDGE.evidence.map((e) => (
                  <li key={e} className="flex gap-2">
                    <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-mint-400" />
                    {e}
                  </li>
                ))}
              </ul>
            </Field>
          </div>
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-2.5">
          <Button variant="primary" icon={<Check className="h-4 w-4" />} onClick={onConfirm}>
            确认并沉淀
          </Button>
          <Button variant="subtle" icon={<Pencil className="h-4 w-4" />} onClick={onConfirm}>
            修改
          </Button>
          <Button
            variant="subtle"
            icon={<User className="h-4 w-4" />}
            onClick={() => confirmAndShare('self')}
          >
            仅自己使用
          </Button>
          <Button
            variant="ghost"
            icon={<X className="h-4 w-4" />}
            onClick={() => showToast('已忽略这条经验，数字人不会共享它', 'info')}
          >
            忽略
          </Button>
        </div>
      </div>
    </div>
  )
}
