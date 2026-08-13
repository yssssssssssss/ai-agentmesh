import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, MoreHorizontal } from 'lucide-react'
import { CONVERSATIONS, type Conversation } from '../../data/mockData'
import { useDemo } from '../../store/DemoContext'
import { cn } from '../../lib/cn'

// 保留时间维度用于排序，但不再展示分组小标题
const GROUP_ORDER: Conversation['group'][] = ['进行中', '今天', '昨天', '本周']

/**
 * 历史对话子导航：内嵌在左侧主导航「AI 工作台」展开区内。
 * 「开始新对话」与历史对话统一为左对齐文字行，仅展示标题、不分组、不带背景块。
 */
export function ConversationNav() {
  const navigate = useNavigate()
  const { showToast } = useDemo()
  const [activeId, setActiveId] = useState(
    CONVERSATIONS.find((c) => c.active)?.id ?? CONVERSATIONS[0]?.id,
  )

  const conversations = GROUP_ORDER.flatMap((group) =>
    CONVERSATIONS.filter((c) => c.group === group),
  )

  return (
    <div className="space-y-0.5">
      {/* 开始新对话：文字链样式，与历史对话对齐 */}
      <button
        onClick={() => {
          navigate('/workspace')
          showToast('已开始新对话', 'info')
        }}
        className="flex w-full items-center gap-2 rounded-[8px] px-2.5 py-1.5 text-left text-[13px] font-medium text-mint-300 transition-colors hover:bg-white/[0.04] hover:text-mint-200"
      >
        <Plus className="h-4 w-4 shrink-0" />
        开始新对话
      </button>

      {/* 历史对话（仅标题、不分组） */}
      {conversations.map((c) => (
        <ConversationItem
          key={c.id}
          conv={c}
          active={c.id === activeId}
          onSelect={() => {
            setActiveId(c.id)
            navigate('/workspace')
            if (c.id !== CONVERSATIONS[0]?.id) showToast(`已切换到「${c.title}」`, 'info')
          }}
          onMore={() => showToast('对话操作：重命名 / 归档 / 删除', 'info')}
        />
      ))}
    </div>
  )
}

function ConversationItem({
  conv,
  active,
  onSelect,
  onMore,
}: {
  conv: Conversation
  active: boolean
  onSelect: () => void
  onMore: () => void
}) {
  return (
    <div
      onClick={onSelect}
      className={cn(
        'group relative flex cursor-pointer items-center gap-2 rounded-[8px] px-2.5 py-1.5 transition-colors',
        active ? 'bg-surface-3' : 'hover:bg-white/[0.04]',
      )}
    >
      <span
        className={cn(
          'min-w-0 flex-1 truncate text-[13px] leading-snug',
          active ? 'font-medium text-slate-100' : 'text-slate-300',
        )}
      >
        {conv.title}
      </span>
      {/* 更多操作 */}
      <button
        onClick={(e) => {
          e.stopPropagation()
          onMore()
        }}
        className="shrink-0 rounded-md p-1 text-slate-600 opacity-0 transition-all hover:bg-white/[0.08] hover:text-slate-300 group-hover:opacity-100"
        aria-label="更多操作"
      >
        <MoreHorizontal className="h-4 w-4" />
      </button>
    </div>
  )
}
