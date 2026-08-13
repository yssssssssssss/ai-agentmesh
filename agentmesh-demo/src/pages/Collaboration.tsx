import { useState } from 'react'
import {
  Network,
  Activity,
  InboxIcon,
  Users,
  HeartHandshake,
  CheckCircle2,
  Clock,
  ArrowRight,
} from 'lucide-react'
import { PageHeader } from '../components/ui/PageHeader'
import { Tabs, type TabItem } from '../components/ui/Tabs'
import { StatTile } from '../components/ui/StatTile'
import { Badge } from '../components/ui/Badge'
import { Avatar } from '../components/ui/Avatar'
import { HelpRequestCard } from '../components/collaboration/HelpRequestCard'
import { MyCollabCard } from '../components/collaboration/MyCollabCard'
import { PeerCard } from '../components/collaboration/PeerCard'
import { CollabTimelineDrawer } from '../components/collaboration/CollabTimelineDrawer'
import {
  COLLAB_OVERVIEW,
  HELP_REQUESTS,
  COMPLETED_COLLAB,
  RECOMMENDED_PEERS,
} from '../data/mockData'
import { useDemo } from '../store/DemoContext'

export function Collaboration() {
  const { peopleHelped, wangchenAuthorized, authorizeWangchen, showToast } = useDemo()
  const [tab, setTab] = useState('requests')
  const [timelineOpen, setTimelineOpen] = useState(false)
  const [localAuthorized, setLocalAuthorized] = useState<Set<string>>(new Set())
  const [declined, setDeclined] = useState<Set<string>>(new Set())

  const tabs: TabItem[] = [
    { key: 'requests', label: '向我求助', count: 3 },
    { key: 'mine', label: '我发起的', count: 2 },
    { key: 'ongoing', label: '协作中', count: 2 },
    { key: 'done', label: '已完成', count: 8 },
    { key: 'peers', label: '推荐数字分身' },
  ]

  const isAuthorized = (id: string) => (id === 'req-wangchen' ? wangchenAuthorized : localAuthorized.has(id))

  const handleAllow = (id: string) => {
    if (id === 'req-wangchen') {
      authorizeWangchen()
    } else {
      setLocalAuthorized((prev) => new Set(prev).add(id))
      showToast('已允许引用，数字人会保留来源与适用范围')
    }
  }

  const handleDecline = (id: string) => {
    setDeclined((prev) => new Set(prev).add(id))
    showToast('已选择暂不共享', 'info')
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="协作网络"
        subtitle="你的数字人如何调用他人经验，也展示你的经验如何帮助其他人。"
      />

      {/* 概览 */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatTile label="协作进行中" value={COLLAB_OVERVIEW.ongoing} icon={<Activity className="h-4 w-4" />} tone="mint" />
        <StatTile label="请求等待确认" value={COLLAB_OVERVIEW.pendingRequests} icon={<InboxIcon className="h-4 w-4" />} tone="remind" />
        <StatTile label="本月帮助同事" value={peopleHelped} icon={<HeartHandshake className="h-4 w-4" />} tone="collab" />
        <StatTile label="收到经验支持" value={COLLAB_OVERVIEW.receivedSupport} icon={<Users className="h-4 w-4" />} tone="knowledge" />
      </div>

      <Tabs items={tabs} value={tab} onChange={setTab} />

      {/* 向我求助 */}
      {tab === 'requests' && (
        <div className="space-y-4 animate-fade-in">
          {HELP_REQUESTS.filter((r) => !declined.has(r.id)).map((r) => (
            <HelpRequestCard
              key={r.id}
              request={r}
              featured={r.id === 'req-wangchen'}
              authorized={isAuthorized(r.id)}
              onAllow={() => handleAllow(r.id)}
              onDetail={() => setTimelineOpen(true)}
              onDecline={() => handleDecline(r.id)}
            />
          ))}
          {HELP_REQUESTS.every((r) => declined.has(r.id)) && (
            <div className="card-base py-12 text-center text-sm text-slate-400">暂无待处理的求助</div>
          )}
        </div>
      )}

      {/* 我发起的 */}
      {tab === 'mine' && (
        <div className="space-y-4 animate-fade-in">
          <MyCollabCard status="done" onDetail={() => setTimelineOpen(true)} />
          <CompactCollab
            title="确认 2026 首屏重点商品入口方案"
            peer="王晨的数字人"
            status="ongoing"
            note="等待暑期主推品类清单"
          />
        </div>
      )}

      {/* 协作中 */}
      {tab === 'ongoing' && (
        <div className="space-y-4 animate-fade-in">
          <CompactCollab title="查找 618 家电会场历史经验" peer="李明的数字人" status="ongoing" note="正在补充复盘细节" onDetail={() => setTimelineOpen(true)} />
          <CompactCollab title="首屏入口点击口径二次确认" peer="王晨的数字人" status="ongoing" note="数据查询 Skill 处理中" />
        </div>
      )}

      {/* 已完成 */}
      {tab === 'done' && (
        <div className="grid grid-cols-1 gap-3 animate-fade-in md:grid-cols-2">
          {COMPLETED_COLLAB.map((c) => (
            <div key={c.id} className="card-base flex items-center gap-4 p-4">
              <Avatar name={c.peer} tone="knowledge" />
              <div className="min-w-0 flex-1">
                <div className="truncate text-sm font-medium text-slate-100">{c.title}</div>
                <div className="text-xs text-slate-500">
                  {c.peer} · {c.result}
                </div>
              </div>
              <div className="flex flex-col items-end gap-1">
                <Badge tone="mint" icon={<CheckCircle2 className="h-3 w-3" />}>
                  已完成
                </Badge>
                <span className="text-[11px] text-slate-600">{c.time}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 推荐数字分身 */}
      {tab === 'peers' && (
        <div className="grid grid-cols-1 gap-4 animate-fade-in md:grid-cols-2 xl:grid-cols-3">
          {RECOMMENDED_PEERS.map((p) => (
            <PeerCard key={p.id} peer={p} onCollab={() => showToast(`已向${p.name}发起协作请求`)} />
          ))}
        </div>
      )}

      <div className="flex items-center gap-2 text-xs text-slate-600">
        <Network className="h-3.5 w-3.5" />
        经验引用全程可追溯，任何跨成员共享都需要经验拥有者本人授权。
      </div>

      <CollabTimelineDrawer open={timelineOpen} onClose={() => setTimelineOpen(false)} />
    </div>
  )
}

/** 紧凑协作条目 */
function CompactCollab({
  title,
  peer,
  status,
  note,
  onDetail,
}: {
  title: string
  peer: string
  status: 'ongoing' | 'done'
  note: string
  onDetail?: () => void
}) {
  return (
    <div className="card-base flex items-center gap-4 p-4">
      <span className="flex h-10 w-10 items-center justify-center rounded-[12px] bg-knowledge/12 text-knowledge">
        <Clock className="h-5 w-5" />
      </span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-semibold text-slate-100">{title}</div>
        <div className="text-xs text-slate-500">
          {peer} · {note}
        </div>
      </div>
      <Badge tone={status === 'done' ? 'mint' : 'knowledge'} dot>
        {status === 'done' ? '已完成' : '协作中'}
      </Badge>
      {onDetail && (
        <button
          onClick={onDetail}
          className="rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-white/[0.06] hover:text-slate-200"
          aria-label="查看详情"
        >
          <ArrowRight className="h-4 w-4" />
        </button>
      )}
    </div>
  )
}
