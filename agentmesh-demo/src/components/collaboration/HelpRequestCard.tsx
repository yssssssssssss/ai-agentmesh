import { BookMarked, FolderClock, Gift, ShieldAlert, Check, Eye, CheckCircle2 } from 'lucide-react'
import { Avatar } from '../ui/Avatar'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import type { HelpRequest } from '../../data/mockData'

interface HelpRequestCardProps {
  request: HelpRequest
  authorized: boolean
  onAllow: () => void
  onDetail: () => void
  onDecline: () => void
  featured?: boolean
}

function Row({ icon, label, children }: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-2.5">
      <span className="mt-0.5 shrink-0 text-slate-500">{icon}</span>
      <div className="text-sm">
        <span className="text-slate-500">{label}：</span>
        <span className="text-slate-300">{children}</span>
      </div>
    </div>
  )
}

export function HelpRequestCard({
  request,
  authorized,
  onAllow,
  onDetail,
  onDecline,
  featured,
}: HelpRequestCardProps) {
  const name = request.from.replace('的数字分身', '')
  return (
    <div
      className={`card-base p-5 transition-colors ${featured ? 'border-collab/25 bg-collab/[0.04]' : ''}`}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Avatar name={name} tone="collab" size="lg" />
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-semibold text-white">{request.from}向你求助</h3>
              {featured && <Badge tone="collab">重点协作</Badge>}
            </div>
            <p className="mt-0.5 text-sm text-slate-400">
              希望参考你的「{request.knowledge}」经验
            </p>
          </div>
        </div>
        {authorized ? (
          <Badge tone="mint" icon={<CheckCircle2 className="h-3.5 w-3.5" />}>
            已授权
          </Badge>
        ) : (
          <Badge tone="remind" dot>
            等待确认
          </Badge>
        )}
      </div>

      <div className="mt-4 space-y-2.5 rounded-[12px] bg-surface-2 p-4">
        <Row icon={<BookMarked className="h-4 w-4" />} label="请求引用的知识">
          {request.knowledge}
        </Row>
        <Row icon={<FolderClock className="h-4 w-4" />} label="使用项目">
          {request.project}
        </Row>
        <Row icon={<Gift className="h-4 w-4" />} label="预计帮助">
          {request.expect}
        </Row>
        <Row icon={<Check className="h-4 w-4" />} label="当前权限范围">
          {request.scope}
        </Row>
      </div>

      {/* AI 风险提醒 */}
      <div className="mt-3 flex items-start gap-2.5 rounded-[10px] border border-remind/20 bg-remind/[0.05] px-3.5 py-2.5">
        <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-remind" />
        <p className="text-xs leading-relaxed text-remind">数字人提醒：{request.risk}</p>
      </div>

      {authorized ? (
        <div className="mt-4 flex items-center gap-2 rounded-[10px] bg-mint-400/[0.06] px-4 py-3 text-sm text-mint-300">
          <CheckCircle2 className="h-4 w-4" />
          你的数字人已将经验提供给{name}，并保留来源和适用范围。
        </div>
      ) : (
        <div className="mt-4 flex flex-wrap items-center gap-2.5">
          <Button variant="primary" icon={<Check className="h-4 w-4" />} onClick={onAllow}>
            允许引用
          </Button>
          <Button variant="subtle" icon={<Eye className="h-4 w-4" />} onClick={onDetail}>
            查看详情
          </Button>
          <Button variant="ghost" onClick={onDecline}>
            暂不共享
          </Button>
        </div>
      )}
    </div>
  )
}
