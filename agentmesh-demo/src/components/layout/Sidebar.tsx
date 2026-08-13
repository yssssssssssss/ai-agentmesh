import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  Bot,
  Sparkles,
  LineChart,
  BookMarked,
  Network,
  Settings,
  ChevronRight,
  ChevronDown,
} from 'lucide-react'
import { cn } from '../../lib/cn'
import { useDemo } from '../../store/DemoContext'
import { CURRENT_USER } from '../../data/mockData'
import { Avatar } from '../ui/Avatar'
import { DigitalHumanMark } from '../ui/DigitalHumanMark'
import { ConversationNav } from '../workspace/ConversationNav'

const NAV = [
  { to: '/digital-self', label: '我的数字人', icon: Bot },
  { to: '/workspace', label: 'AI 工作台', icon: Sparkles },
  { to: '/insights', label: '工作洞察', icon: LineChart },
  { to: '/knowledge', label: '我的知识', icon: BookMarked, badgeKey: 'pending' as const },
  { to: '/collaboration', label: '协作网络', icon: Network, badgeKey: 'requests' as const },
]

interface SidebarProps {
  onOpenSettings: () => void
  onOpenProfile: () => void
}

export function Sidebar({ onOpenSettings, onOpenProfile }: SidebarProps) {
  const { pendingCount } = useDemo()
  const { pathname } = useLocation()
  const isWorkspace = pathname.startsWith('/workspace')

  // 「AI 工作台」下的历史对话子导航：进入工作台自动展开，可手动折叠
  const [historyOpen, setHistoryOpen] = useState(isWorkspace)
  useEffect(() => {
    if (isWorkspace) setHistoryOpen(true)
  }, [isWorkspace])

  return (
    <aside className="flex h-full w-[260px] shrink-0 flex-col border-r border-white/[0.06] bg-base">
      {/* 品牌 */}
      <div className="flex items-center gap-3 px-5 py-5">
        <DigitalHumanMark size={40} />
        <div className="leading-tight">
          <div className="text-[15px] font-semibold text-white">我的数字人</div>
          <div className="text-[11px] tracking-wide text-slate-500">AgentMesh</div>
        </div>
      </div>

      {/* 一级导航（AI 工作台 展开历史对话子导航） */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2">
        {NAV.map((item) => {
          const Icon = item.icon
          const badge =
            item.badgeKey === 'pending' ? pendingCount : item.badgeKey === 'requests' ? 3 : 0
          const isWorkspaceItem = item.to === '/workspace'
          return (
            <div key={item.to}>
              <NavLink
                to={item.to}
                className={({ isActive }) =>
                  cn(
                    'group relative flex items-center gap-3 rounded-[10px] px-3 py-2.5 text-sm font-medium transition-all duration-150',
                    isActive
                      ? 'bg-surface-3 text-white'
                      : 'text-slate-400 hover:bg-white/[0.04] hover:text-slate-200',
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {isActive && (
                      <span className="absolute left-0 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full bg-mint-400" />
                    )}
                    <Icon
                      className={cn('h-[18px] w-[18px] shrink-0', isActive ? 'text-mint-300' : '')}
                    />
                    <span className="flex-1">{item.label}</span>
                    {badge > 0 && (
                      <span className="inline-flex h-5 min-w-[20px] items-center justify-center rounded-full bg-mint-400/20 px-1.5 text-[11px] font-semibold text-mint-300 tabular-nums">
                        {badge}
                      </span>
                    )}
                    {isWorkspaceItem && (
                      <button
                        type="button"
                        onClick={(e) => {
                          e.preventDefault()
                          e.stopPropagation()
                          setHistoryOpen((v) => !v)
                        }}
                        className="-mr-1 rounded p-0.5 text-slate-500 transition-colors hover:text-slate-200"
                        aria-label={historyOpen ? '收起历史对话' : '展开历史对话'}
                      >
                        <ChevronDown
                          className={cn(
                            'h-4 w-4 transition-transform',
                            historyOpen ? '' : '-rotate-90',
                          )}
                        />
                      </button>
                    )}
                  </>
                )}
              </NavLink>

              {/* 历史对话子导航 + 与其余导航的分割线 */}
              {isWorkspaceItem && historyOpen && (
                <>
                  <div className="mt-1.5 border-l border-white/[0.06] pl-2">
                    <ConversationNav />
                  </div>
                  {/* 分割线：区隔「AI 工作台」模块与后续导航 */}
                  <div className="mt-2 border-t border-white/[0.08]" />
                </>
              )}
            </div>
          )
        })}
      </nav>

      {/* 底部：空间 + 用户 + 设置 */}
      <div className="border-t border-white/[0.06] p-3">
        <div className="mb-2 flex items-center gap-2 rounded-[10px] bg-surface-1 px-3 py-2">
          <span className="h-2 w-2 rounded-full bg-mint-400" />
          <span className="text-xs text-slate-400">当前空间</span>
          <span className="ml-auto text-xs font-medium text-slate-200">{CURRENT_USER.space}</span>
        </div>

        <button
          onClick={onOpenProfile}
          className="flex w-full items-center gap-3 rounded-[10px] px-2 py-2 text-left transition-colors hover:bg-white/[0.04]"
        >
          <Avatar name={CURRENT_USER.name} size="md" tone="mint" />
          <div className="min-w-0 flex-1 leading-tight">
            <div className="truncate text-sm font-medium text-slate-100">{CURRENT_USER.name}</div>
            <div className="truncate text-xs text-slate-500">{CURRENT_USER.role}</div>
          </div>
          <ChevronRight className="h-4 w-4 text-slate-600" />
        </button>

        <button
          onClick={onOpenSettings}
          className="mt-1 flex w-full items-center gap-3 rounded-[10px] px-3 py-2 text-sm text-slate-400 transition-colors hover:bg-white/[0.04] hover:text-slate-200"
        >
          <Settings className="h-[18px] w-[18px]" />
          设置
        </button>
      </div>
    </aside>
  )
}
