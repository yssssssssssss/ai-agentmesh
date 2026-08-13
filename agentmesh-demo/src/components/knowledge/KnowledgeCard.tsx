import { FolderClock, Clock, ChevronRight } from 'lucide-react'
import { Badge } from '../ui/Badge'
import type { KnowledgeCardData } from '../../data/mockData'

interface KnowledgeCardProps {
  data: KnowledgeCardData
  onClick?: () => void
  accent?: 'mint' | 'knowledge' | 'default'
}

const ACCENT: Record<NonNullable<KnowledgeCardProps['accent']>, string> = {
  mint: 'hover:border-mint-400/30',
  knowledge: 'hover:border-knowledge/30',
  default: 'hover:border-white/[0.12]',
}

/** 通用知识卡片，复用于个人 / 项目 / 已共享列表 */
export function KnowledgeCard({ data, onClick, accent = 'default' }: KnowledgeCardProps) {
  return (
    <button
      onClick={onClick}
      className={`group flex w-full flex-col rounded-[12px] border border-white/[0.06] bg-surface-2 p-4 text-left transition-all hover:-translate-y-0.5 hover:bg-surface-3 ${ACCENT[accent]}`}
    >
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-sm font-semibold leading-snug text-slate-100">{data.title}</h3>
        <ChevronRight className="mt-0.5 h-4 w-4 shrink-0 text-slate-600 transition-transform group-hover:translate-x-0.5" />
      </div>
      <p className="mt-1.5 line-clamp-2 text-[13px] leading-relaxed text-slate-400">{data.summary}</p>
      <div className="mt-3 flex flex-wrap items-center gap-1.5">
        {data.tags.map((t) => (
          <Badge key={t} tone="neutral">
            {t}
          </Badge>
        ))}
      </div>
      <div className="mt-3 flex items-center gap-3 border-t border-white/[0.05] pt-2.5 text-[11px] text-slate-500">
        <span className="inline-flex items-center gap-1">
          <FolderClock className="h-3 w-3" />
          {data.project}
        </span>
        <span className="inline-flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {data.updated}
        </span>
      </div>
    </button>
  )
}
