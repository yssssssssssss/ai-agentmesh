import { Shield, Bot, Users, Cpu, ScrollText, Share2, MessageSquare, ChevronRight, Moon } from 'lucide-react'
import { Drawer } from '../ui/Drawer'
import { Badge } from '../ui/Badge'

interface SettingsDrawerProps {
  open: boolean
  onClose: () => void
}

/**
 * 设置抽屉：承载不进入一级导航的后台 / 高级能力，
 * 保持普通用户前台的克制。
 */
const ADMIN_ENTRIES = [
  { icon: Bot, label: 'Agent 管理', desc: '管理数字人可用的能力与运行参数' },
  { icon: Users, label: '成员管理', desc: '空间成员与角色权限' },
  { icon: Cpu, label: '模型管理', desc: '底层模型选择与用量' },
  { icon: Share2, label: '协作图', desc: '数字人协作关系全景' },
  { icon: ScrollText, label: '审计日志', desc: '经验共享与引用的完整记录' },
  { icon: MessageSquare, label: '团队 BBS', desc: '空间内的讨论与公告' },
]

export function SettingsDrawer({ open, onClose }: SettingsDrawerProps) {
  return (
    <Drawer
      open={open}
      onClose={onClose}
      icon={<Shield className="h-5 w-5" />}
      title="设置"
      subtitle="偏好设置与高级能力入口"
      width={460}
    >
      <div className="space-y-6">
        {/* 偏好 */}
        <section>
          <h3 className="mb-2.5 text-sm font-semibold text-slate-200">偏好</h3>
          <div className="divide-y divide-white/[0.05] overflow-hidden rounded-[12px] border border-white/[0.06] bg-surface-1">
            <label className="flex items-center gap-3 px-4 py-3">
              <Moon className="h-4 w-4 text-slate-400" />
              <span className="flex-1 text-sm text-slate-200">深色主题</span>
              <span className="relative inline-flex h-5 w-9 items-center rounded-full bg-mint-400">
                <span className="ml-auto mr-0.5 h-4 w-4 rounded-full bg-white shadow" />
              </span>
            </label>
            <label className="flex items-center gap-3 px-4 py-3">
              <Bot className="h-4 w-4 text-slate-400" />
              <span className="flex-1 text-sm text-slate-200">新经验默认需本人确认</span>
              <span className="relative inline-flex h-5 w-9 items-center rounded-full bg-mint-400">
                <span className="ml-auto mr-0.5 h-4 w-4 rounded-full bg-white shadow" />
              </span>
            </label>
          </div>
        </section>

        {/* 高级能力入口 */}
        <section>
          <div className="mb-2.5 flex items-center gap-2">
            <h3 className="text-sm font-semibold text-slate-200">高级能力</h3>
            <Badge tone="neutral">管理员 / 后台</Badge>
          </div>
          <p className="mb-3 text-xs text-slate-500">
            以下能力面向管理与排查场景，日常工作无需进入。
          </p>
          <div className="space-y-2">
            {ADMIN_ENTRIES.map((e) => (
              <button
                key={e.label}
                className="flex w-full items-center gap-3 rounded-[10px] border border-white/[0.06] bg-surface-1 px-4 py-3 text-left transition-colors hover:border-white/[0.12] hover:bg-surface-2"
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-white/[0.05] text-slate-300">
                  <e.icon className="h-4 w-4" />
                </span>
                <span className="flex-1">
                  <span className="block text-sm font-medium text-slate-100">{e.label}</span>
                  <span className="block text-xs text-slate-500">{e.desc}</span>
                </span>
                <ChevronRight className="h-4 w-4 text-slate-600" />
              </button>
            ))}
          </div>
        </section>
      </div>
    </Drawer>
  )
}
