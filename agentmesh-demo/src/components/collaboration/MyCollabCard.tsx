import { Network, CheckCircle2, ArrowRight } from 'lucide-react'
import { Avatar } from '../ui/Avatar'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { MY_COLLAB } from '../../data/mockData'

interface MyCollabCardProps {
  onDetail: () => void
  status?: 'ongoing' | 'done'
}

export function MyCollabCard({ onDetail, status = 'done' }: MyCollabCardProps) {
  return (
    <div className="card-base p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-[12px] bg-mint-400/12 text-mint-300">
            <Network className="h-5 w-5" />
          </span>
          <div>
            <h3 className="text-base font-semibold text-white">{MY_COLLAB.title}</h3>
            <p className="text-xs text-slate-500">你发起 · 3 个数字分身 + 1 个 Skill 参与</p>
          </div>
        </div>
        <Badge tone={status === 'done' ? 'mint' : 'knowledge'} dot>
          {status === 'done' ? '已完成' : '协作中'}
        </Badge>
      </div>

      {/* 参与者 */}
      <div className="mt-4 flex flex-wrap gap-2">
        {MY_COLLAB.participants.map((p) => (
          <div
            key={p.name}
            className="flex items-center gap-2 rounded-pill border border-white/[0.06] bg-surface-2 py-1 pl-1 pr-3"
          >
            <Avatar name={p.name} tone={p.tone} size="sm" />
            <span className="text-xs text-slate-300">{p.name}</span>
          </div>
        ))}
      </div>

      {/* 结果 */}
      <div className="mt-4 grid grid-cols-2 gap-2.5">
        {MY_COLLAB.results.map((r) => (
          <div key={r} className="flex items-center gap-2 rounded-[10px] bg-surface-2 px-3.5 py-2.5">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-mint-300" />
            <span className="text-sm text-slate-300">{r}</span>
          </div>
        ))}
      </div>

      <Button variant="subtle" className="mt-4" iconRight={<ArrowRight className="h-4 w-4" />} onClick={onDetail}>
        查看协作详情与完整时间线
      </Button>
    </div>
  )
}
