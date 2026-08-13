import { useNavigate } from 'react-router-dom'
import { ArrowRight, Sparkles } from 'lucide-react'
import { DigitalHumanMark } from '../ui/DigitalHumanMark'
import { Button } from '../ui/Button'
import { useDemo } from '../../store/DemoContext'

export function WelcomeHero() {
  const navigate = useNavigate()
  const { pendingCount } = useDemo()

  return (
    <section className="relative overflow-hidden rounded-card border border-white/[0.06] bg-gradient-to-br from-surface-2 to-surface-1 p-7">
      {/* 柔和光斑，克制处理 */}
      <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-mint-400/[0.07] blur-3xl" />
      <div className="relative flex flex-wrap items-center justify-between gap-6">
        <div className="max-w-2xl">
          <h1 className="text-[28px] font-bold tracking-tight text-white">下午好，林知夏</h1>
          <p className="mt-2.5 text-[15px] leading-relaxed text-slate-300">
            你的数字人正在跟进 <span className="font-semibold text-mint-300">3 项工作</span>，
            并从最近的协作中形成了{' '}
            <span className="font-semibold text-mint-300">
              {pendingCount > 0 ? '1 条新经验' : '1 条已确认经验'}
            </span>
            。
          </p>
          <div className="mt-5 flex items-center gap-3">
            <Button
              size="lg"
              icon={<Sparkles className="h-[18px] w-[18px]" />}
              iconRight={<ArrowRight className="h-4 w-4" />}
              onClick={() => navigate('/workspace')}
            >
              开始一项工作
            </Button>
            {pendingCount > 0 && (
              <Button size="lg" variant="subtle" onClick={() => navigate('/knowledge')}>
                去确认新经验
              </Button>
            )}
          </div>
        </div>

        <div className="flex flex-col items-center gap-3">
          <DigitalHumanMark size={92} />
          <span className="inline-flex items-center gap-2 rounded-pill bg-mint-400/10 px-3 py-1 text-xs font-medium text-mint-300 ring-1 ring-inset ring-mint-400/20">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-mint-400" />
            数字人在线
          </span>
        </div>
      </div>
    </section>
  )
}
