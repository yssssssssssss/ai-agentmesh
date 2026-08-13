import { Network, CheckCircle2, Info } from 'lucide-react'
import { Drawer } from '../ui/Drawer'
import { Badge } from '../ui/Badge'
import { Avatar } from '../ui/Avatar'
import { MY_COLLAB, COLLAB_TIMELINE, type TimelineNode } from '../../data/mockData'
import { cn } from '../../lib/cn'

interface CollabTimelineDrawerProps {
  open: boolean
  onClose: () => void
}

const DOT: Record<TimelineNode['tone'], string> = {
  mint: 'bg-mint-400',
  knowledge: 'bg-knowledge',
  collab: 'bg-collab',
  remind: 'bg-remind',
  rose: 'bg-rose',
}

export function CollabTimelineDrawer({ open, onClose }: CollabTimelineDrawerProps) {
  return (
    <Drawer
      open={open}
      onClose={onClose}
      icon={<Network className="h-5 w-5" />}
      title={MY_COLLAB.title}
      subtitle="数字分身协作 · 先看结果，再看过程"
      width={520}
    >
      <div className="space-y-6">
        {/* 结果优先 */}
        <section>
          <h3 className="mb-2.5 text-sm font-semibold text-slate-200">协作结果</h3>
          <div className="grid grid-cols-2 gap-2.5">
            {MY_COLLAB.results.map((r) => (
              <div
                key={r}
                className="flex items-center gap-2 rounded-[10px] border border-white/[0.06] bg-surface-1 px-3.5 py-2.5"
              >
                <CheckCircle2 className="h-4 w-4 shrink-0 text-mint-300" />
                <span className="text-sm text-slate-300">{r}</span>
              </div>
            ))}
          </div>
        </section>

        {/* 参与者 */}
        <section>
          <h3 className="mb-2.5 text-sm font-semibold text-slate-200">参与的数字分身</h3>
          <div className="flex flex-wrap gap-2">
            {MY_COLLAB.participants.map((p) => (
              <div
                key={p.name}
                className="flex items-center gap-2 rounded-pill border border-white/[0.06] bg-surface-1 py-1 pl-1 pr-3"
              >
                <Avatar name={p.name} tone={p.tone} size="sm" />
                <span className="text-xs text-slate-300">{p.name}</span>
                <span className="text-[11px] text-slate-500">· {p.role}</span>
              </div>
            ))}
          </div>
        </section>

        {/* 协作过程时间线 */}
        <section>
          <h3 className="mb-3 text-sm font-semibold text-slate-200">协作过程</h3>
          <ol className="relative space-y-4">
            {COLLAB_TIMELINE.map((node, i) => {
              const last = i === COLLAB_TIMELINE.length - 1
              return (
                <li key={node.id} className="relative flex gap-3.5">
                  {!last && (
                    <span className="absolute left-[7px] top-5 h-[calc(100%+4px)] w-px bg-white/[0.08]" />
                  )}
                  <span
                    className={cn('relative z-10 mt-1 h-3.5 w-3.5 shrink-0 rounded-full ring-4 ring-surface-2', DOT[node.tone])}
                  />
                  <div className="flex-1 pb-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium text-slate-100">{node.who}</span>
                      <Badge tone={node.tone === 'rose' ? 'rose' : node.tone === 'knowledge' ? 'knowledge' : node.tone === 'collab' ? 'collab' : 'mint'}>
                        {node.action}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm leading-relaxed text-slate-400">{node.detail}</p>
                  </div>
                </li>
              )
            })}
          </ol>
        </section>

        <div className="flex items-start gap-2 rounded-[10px] bg-surface-1 px-3.5 py-2.5 text-xs text-slate-500">
          <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          协作过程已翻译为工作语言。发起求助、补充经验、提醒限制、确认方案、形成新经验，均可追溯来源。
        </div>
      </div>
    </Drawer>
  )
}
