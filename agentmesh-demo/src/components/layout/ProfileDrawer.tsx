import {
  Bot,
  Brain,
  Sparkles,
  Users,
  Check,
  Pencil,
  Wrench,
} from 'lucide-react'
import { Drawer } from '../ui/Drawer'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { CURRENT_USER, DIGITAL_PROFILE, CONFIGURED_SKILLS, UNDERSTANDINGS } from '../../data/mockData'
import { useDemo } from '../../store/DemoContext'

interface ProfileDrawerProps {
  open: boolean
  onClose: () => void
}

export function ProfileDrawer({ open, onClose }: ProfileDrawerProps) {
  const { understandings, setUnderstanding } = useDemo()

  return (
    <Drawer
      open={open}
      onClose={onClose}
      icon={<Bot className="h-5 w-5" />}
      title={`${CURRENT_USER.name}的数字人`}
      subtitle={`${CURRENT_USER.space} · ${CURRENT_USER.role}`}
      width={480}
    >
      <div className="space-y-6">
        {/* 概览指标 */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { icon: Brain, label: '个人经验', value: DIGITAL_PROFILE.personalKnowledge },
            { icon: Wrench, label: '团队 Skill', value: DIGITAL_PROFILE.teamSkills },
            { icon: Users, label: '本月协作', value: DIGITAL_PROFILE.monthlyCollab },
          ].map((s) => (
            <div key={s.label} className="rounded-[12px] border border-white/[0.06] bg-surface-1 p-3 text-center">
              <s.icon className="mx-auto h-4 w-4 text-mint-300" />
              <div className="mt-1.5 text-xl font-semibold text-white tabular-nums">{s.value}</div>
              <div className="text-[11px] text-slate-500">{s.label}</div>
            </div>
          ))}
        </div>

        {/* 主要领域 */}
        <section>
          <h3 className="mb-2.5 text-sm font-semibold text-slate-200">主要领域</h3>
          <div className="flex flex-wrap gap-2">
            {CURRENT_USER.domains.map((d) => (
              <Badge key={d} tone="knowledge">
                {d}
              </Badge>
            ))}
          </div>
        </section>

        {/* 已配置 Skill */}
        <section>
          <h3 className="mb-2.5 flex items-center gap-2 text-sm font-semibold text-slate-200">
            <Wrench className="h-4 w-4 text-mint-300" />
            已配置团队 Skill
          </h3>
          <div className="space-y-2">
            {CONFIGURED_SKILLS.map((sk) => (
              <div
                key={sk.name}
                className="rounded-[10px] border border-white/[0.06] bg-surface-1 px-3.5 py-2.5"
              >
                <div className="text-sm font-medium text-slate-100">{sk.name}</div>
                <div className="mt-0.5 text-xs text-slate-500">{sk.desc}</div>
              </div>
            ))}
          </div>
        </section>

        {/* 调整数字人理解 */}
        <section>
          <h3 className="mb-2.5 flex items-center gap-2 text-sm font-semibold text-slate-200">
            <Sparkles className="h-4 w-4 text-mint-300" />
            调整数字人理解
          </h3>
          <div className="space-y-2">
            {UNDERSTANDINGS.map((u) => {
              const status = understandings[u.id]
              return (
                <div
                  key={u.id}
                  className="flex items-center gap-3 rounded-[10px] border border-white/[0.06] bg-surface-1 px-3.5 py-2.5"
                >
                  <p className="flex-1 text-sm text-slate-300">{u.text}</p>
                  {status === 'confirmed' ? (
                    <Badge tone="mint" icon={<Check className="h-3 w-3" />}>
                      已确认
                    </Badge>
                  ) : status === 'ignored' ? (
                    <Badge tone="neutral">已忽略</Badge>
                  ) : (
                    <div className="flex gap-1">
                      <Button size="sm" variant="ghost" onClick={() => setUnderstanding(u.id, 'confirmed')}>
                        确认
                      </Button>
                      <button
                        onClick={() => setUnderstanding(u.id, 'modified')}
                        className="rounded-lg p-1.5 text-slate-500 hover:bg-white/[0.06] hover:text-slate-200"
                        aria-label="修改"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </section>
      </div>
    </Drawer>
  )
}
