import { Check, Pencil, X, Sparkles } from 'lucide-react'
import { SectionCard } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { UNDERSTANDINGS } from '../../data/mockData'
import { useDemo } from '../../store/DemoContext'
import { cn } from '../../lib/cn'

export function UnderstandingList() {
  const { understandings, setUnderstanding } = useDemo()

  return (
    <SectionCard
      title="最近理解了我"
      icon={<Sparkles className="h-[18px] w-[18px]" />}
      desc="数字人从你的工作中形成的新理解，由你确认是否准确"
    >
      <div className="space-y-2.5">
        {UNDERSTANDINGS.map((u) => {
          const status = understandings[u.id]
          const settled = status === 'confirmed' || status === 'ignored' || status === 'modified'
          return (
            <div
              key={u.id}
              className={cn(
                'flex items-center gap-4 rounded-[12px] border px-4 py-3 transition-colors',
                settled ? 'border-white/[0.04] bg-surface-1/60' : 'border-white/[0.06] bg-surface-2',
              )}
            >
              <p className={cn('flex-1 text-sm', settled ? 'text-slate-400' : 'text-slate-200')}>
                {u.text}
              </p>
              {status === 'confirmed' ? (
                <Badge tone="mint" icon={<Check className="h-3 w-3" />}>
                  已确认
                </Badge>
              ) : status === 'modified' ? (
                <Badge tone="knowledge" icon={<Pencil className="h-3 w-3" />}>
                  已修改
                </Badge>
              ) : status === 'ignored' ? (
                <Badge tone="neutral">已忽略</Badge>
              ) : (
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setUnderstanding(u.id, 'confirmed')}
                    className="inline-flex items-center gap-1 rounded-lg bg-mint-400/10 px-2.5 py-1.5 text-[13px] font-medium text-mint-300 transition-colors hover:bg-mint-400/20"
                  >
                    <Check className="h-3.5 w-3.5" />
                    确认
                  </button>
                  <button
                    onClick={() => setUnderstanding(u.id, 'modified')}
                    className="rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-white/[0.06] hover:text-slate-200"
                    aria-label="修改"
                    title="修改"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => setUnderstanding(u.id, 'ignored')}
                    className="rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-white/[0.06] hover:text-slate-200"
                    aria-label="忽略"
                    title="忽略"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </SectionCard>
  )
}
