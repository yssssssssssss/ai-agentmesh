import { useState } from 'react'
import { Recycle, Quote, Layers, Clock, Plus, ChevronRight, GitBranch } from 'lucide-react'
import { Drawer } from '../ui/Drawer'
import { Badge } from '../ui/Badge'
import { Avatar } from '../ui/Avatar'
import { REUSE_DETAIL } from '../../data/mockData'
import { useDemo } from '../../store/DemoContext'

export function ReuseSection() {
  const [open, setOpen] = useState(false)
  const { reusedCount, wangchenAuthorized } = useDemo()

  return (
    <>
      <div className="space-y-4">
        <p className="text-sm text-slate-400">
          你的经验被其他数字人引用后的真实结果，共{' '}
          <span className="font-medium text-slate-200 tabular-nums">{reusedCount}</span> 条被复用。
        </p>

        {/* 王晨引用后新增的动态 */}
        {wangchenAuthorized && (
          <div className="flex items-center gap-3 rounded-[12px] border border-mint-400/20 bg-mint-400/[0.05] px-4 py-3 animate-fade-in">
            <Avatar name="王晨" tone="collab" size="sm" />
            <p className="flex-1 text-sm text-slate-300">
              王晨的数字人引用了你的「首屏核心入口效率判断」，用于家电暑期会场改版。
            </p>
            <Badge tone="mint">刚刚</Badge>
          </div>
        )}

        {/* 复用主卡 */}
        <div className="card-base p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-[12px] bg-collab/12 text-collab">
                <Recycle className="h-5 w-5" />
              </span>
              <div>
                <h3 className="text-base font-semibold text-white">{REUSE_DETAIL.title}</h3>
                <p className="text-xs text-slate-500">最近使用：{REUSE_DETAIL.recent}</p>
              </div>
            </div>
            <Badge tone="collab">已共享</Badge>
          </div>

          <div className="mt-4 grid grid-cols-3 gap-3">
            <div className="rounded-[10px] bg-surface-2 p-3">
              <Quote className="h-4 w-4 text-collab" />
              <div className="mt-2 text-xl font-semibold text-white tabular-nums">{REUSE_DETAIL.citedBy}</div>
              <div className="text-xs text-slate-500">位同事引用</div>
            </div>
            <div className="rounded-[10px] bg-surface-2 p-3">
              <Layers className="h-4 w-4 text-knowledge" />
              <div className="mt-2 text-xl font-semibold text-white tabular-nums">{REUSE_DETAIL.projects}</div>
              <div className="text-xs text-slate-500">个项目应用</div>
            </div>
            <div className="rounded-[10px] bg-surface-2 p-3">
              <Plus className="h-4 w-4 text-mint-300" />
              <div className="mt-2 text-xl font-semibold text-white tabular-nums">1</div>
              <div className="text-xs text-slate-500">条新增适用条件</div>
            </div>
          </div>

          <div className="mt-3 flex items-start gap-2 rounded-[10px] bg-mint-400/[0.06] px-3.5 py-2.5 text-xs text-mint-300">
            <Plus className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            复用后新增条件：{REUSE_DETAIL.addedCondition}
          </div>

          <button
            onClick={() => setOpen(true)}
            className="mt-4 flex w-full items-center justify-center gap-1.5 rounded-[10px] border border-white/[0.08] py-2.5 text-sm font-medium text-slate-300 transition-colors hover:border-white/[0.16] hover:text-white"
          >
            查看复用详情
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      <Drawer
        open={open}
        onClose={() => setOpen(false)}
        icon={<GitBranch className="h-5 w-5" />}
        title={REUSE_DETAIL.title}
        subtitle={`被 ${REUSE_DETAIL.citedBy} 位同事引用 · 应用于 ${REUSE_DETAIL.projects} 个项目`}
      >
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-slate-200">复用记录</h3>
          <ol className="relative space-y-4">
            {REUSE_DETAIL.timeline.map((t, i) => {
              const last = i === REUSE_DETAIL.timeline.length - 1
              return (
                <li key={i} className="relative flex gap-3">
                  {!last && <span className="absolute left-4 top-9 h-[calc(100%+4px)] w-px bg-white/[0.08]" />}
                  <Avatar name={t.who} tone="collab" />
                  <div className="flex-1 rounded-[12px] border border-white/[0.06] bg-surface-1 p-3.5">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-slate-100">{t.who}</span>
                      <Badge tone="knowledge">{t.project}</Badge>
                    </div>
                    <p className="mt-1.5 text-sm text-slate-400">{t.note}</p>
                  </div>
                </li>
              )
            })}
          </ol>
          <div className="flex items-center gap-2 rounded-[10px] bg-surface-1 px-3.5 py-2.5 text-xs text-slate-500">
            <Clock className="h-3.5 w-3.5" />
            每次复用都保留来源与适用范围，可追溯到你的原始经验。
          </div>
        </div>
      </Drawer>
    </>
  )
}
