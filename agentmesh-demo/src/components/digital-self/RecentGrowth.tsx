import { useNavigate } from 'react-router-dom'
import { TrendingUp, Award, Wrench, Users, ArrowRight, CheckCircle2, Clock } from 'lucide-react'
import { SectionCard } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { useDemo } from '../../store/DemoContext'
import { cn } from '../../lib/cn'

export function RecentGrowth() {
  const navigate = useNavigate()
  const { pendingCount } = useDemo()
  const confirmed = pendingCount === 0

  const items = [
    { icon: Award, label: '新增 1 条项目经验', tone: 'mint' as const },
    { icon: Wrench, label: '新掌握 1 个 Skill', tone: 'knowledge' as const },
    { icon: Users, label: '完成 2 次跨成员协作', tone: 'collab' as const },
  ]

  return (
    <SectionCard title="最近成长" icon={<TrendingUp className="h-[18px] w-[18px]" />}>
      <div className="grid grid-cols-3 gap-2.5">
        {items.map((it) => (
          <div
            key={it.label}
            className="flex flex-col gap-2 rounded-[12px] border border-white/[0.06] bg-surface-2 p-3.5"
          >
            <span
              className={cn(
                'flex h-8 w-8 items-center justify-center rounded-lg',
                it.tone === 'mint' && 'bg-mint-400/10 text-mint-300',
                it.tone === 'knowledge' && 'bg-knowledge/10 text-knowledge',
                it.tone === 'collab' && 'bg-collab/10 text-collab',
              )}
            >
              <it.icon className="h-4 w-4" />
            </span>
            <span className="text-[13px] leading-snug text-slate-300">{it.label}</span>
          </div>
        ))}
      </div>

      {/* 突出卡片：首屏核心入口效率判断 */}
      <button
        onClick={() => navigate('/knowledge')}
        className={cn(
          'mt-3 flex w-full items-center gap-4 rounded-[12px] border p-4 text-left transition-all',
          confirmed
            ? 'border-mint-400/30 bg-mint-400/[0.06]'
            : 'border-remind/25 bg-remind/[0.06] hover:border-remind/40',
        )}
      >
        <span
          className={cn(
            'flex h-10 w-10 shrink-0 items-center justify-center rounded-[10px]',
            confirmed ? 'bg-mint-400/15 text-mint-300' : 'bg-remind/15 text-remind',
          )}
        >
          {confirmed ? <CheckCircle2 className="h-5 w-5" /> : <Clock className="h-5 w-5" />}
        </span>
        <div className="flex-1">
          <div className="text-sm font-semibold text-white">首屏核心入口效率判断</div>
          <div className="mt-0.5 text-xs text-slate-400">
            {confirmed ? '已完成沉淀，可供家电设计组引用' : '数字人已形成新判断，等待本人确认'}
          </div>
        </div>
        {confirmed ? (
          <Badge tone="mint">已完成沉淀</Badge>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs font-medium text-remind">
            去确认 <ArrowRight className="h-3.5 w-3.5" />
          </span>
        )}
      </button>
    </SectionCard>
  )
}
