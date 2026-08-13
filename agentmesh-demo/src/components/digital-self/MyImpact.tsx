import { Share2, Users, Layers, Quote, Sparkle } from 'lucide-react'
import { SectionCard } from '../ui/Card'
import { StatTile } from '../ui/StatTile'
import { useDemo } from '../../store/DemoContext'
import { cn } from '../../lib/cn'

export function MyImpact() {
  const { sharedCount, peopleHelped, reusedCount, monthlyCitations, impactFeed } = useDemo()

  return (
    <SectionCard
      title="我的影响"
      icon={<Share2 className="h-[18px] w-[18px]" />}
      desc="你沉淀的经验，正在通过数字人帮助更多同事"
    >
      <div className="grid grid-cols-4 gap-3">
        <StatTile label="已共享经验" value={sharedCount} icon={<Share2 className="h-4 w-4" />} tone="mint" />
        <StatTile label="帮助同事" value={peopleHelped} icon={<Users className="h-4 w-4" />} tone="collab" />
        <StatTile label="应用项目" value={6} icon={<Layers className="h-4 w-4" />} tone="knowledge" />
        <StatTile
          label="本月被引用"
          value={monthlyCitations}
          icon={<Quote className="h-4 w-4" />}
          tone="remind"
        />
      </div>

      <div className="mt-4 space-y-2">
        {impactFeed.map((f) => (
          <div
            key={f.id}
            className={cn(
              'flex items-start gap-3 rounded-[12px] border px-4 py-3',
              f.highlight ? 'border-mint-400/20 bg-mint-400/[0.05]' : 'border-white/[0.06] bg-surface-2',
            )}
          >
            <Sparkle
              className={cn('mt-0.5 h-4 w-4 shrink-0', f.highlight ? 'text-mint-300' : 'text-slate-500')}
            />
            <p className="flex-1 text-sm leading-relaxed text-slate-300">{f.text}</p>
            <span className="shrink-0 text-xs text-slate-500">{f.time}</span>
          </div>
        ))}
      </div>

      <p className="mt-3 text-xs text-slate-500">
        被复用经验共 <span className="font-medium text-slate-300 tabular-nums">{reusedCount}</span> 条
      </p>
    </SectionCard>
  )
}
