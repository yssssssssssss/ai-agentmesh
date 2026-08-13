import { Bot, Brain, Wrench, Users, FileText, SlidersHorizontal } from 'lucide-react'
import { DigitalHumanMark } from '../ui/DigitalHumanMark'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { CURRENT_USER, DIGITAL_PROFILE } from '../../data/mockData'
import { useLayoutUI } from '../layout/AppLayout'

export function IdentityCard() {
  const { openProfile } = useLayoutUI()

  const metrics = [
    { icon: Brain, label: '已掌握个人经验', value: `${DIGITAL_PROFILE.personalKnowledge} 条` },
    { icon: Wrench, label: '已配置团队 Skill', value: `${DIGITAL_PROFILE.teamSkills} 个` },
    { icon: Users, label: '本月数字分身协作', value: `${DIGITAL_PROFILE.monthlyCollab} 次` },
  ]

  return (
    <section className="card-base p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-4">
          <DigitalHumanMark size={60} />
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-semibold text-white">{CURRENT_USER.name}的数字人</h2>
              <Badge tone="mint" icon={<Bot className="h-3 w-3" />}>
                {CURRENT_USER.space} · {CURRENT_USER.role}
              </Badge>
            </div>
            <p className="mt-1.5 text-sm text-slate-400">
              主要领域：{CURRENT_USER.domains.join(' · ')}
            </p>
            <div className="mt-2 inline-flex items-center gap-2 rounded-lg bg-surface-2 px-3 py-1.5 text-xs text-slate-300">
              <span className="text-slate-500">当前项目</span>
              <span className="font-medium text-slate-100">{CURRENT_USER.project}</span>
            </div>
          </div>
        </div>
        <div className="flex shrink-0 gap-2">
          <Button variant="subtle" size="sm" icon={<FileText className="h-4 w-4" />} onClick={openProfile}>
            查看完整档案
          </Button>
          <Button
            variant="ghost"
            size="sm"
            icon={<SlidersHorizontal className="h-4 w-4" />}
            onClick={openProfile}
          >
            调整数字人理解
          </Button>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-3 gap-3">
        {metrics.map((m) => (
          <div key={m.label} className="flex items-center gap-3 rounded-[12px] bg-surface-2 px-4 py-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-mint-400/10 text-mint-300">
              <m.icon className="h-[18px] w-[18px]" />
            </span>
            <div>
              <div className="text-[15px] font-semibold text-white">{m.value}</div>
              <div className="text-xs text-slate-500">{m.label}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
