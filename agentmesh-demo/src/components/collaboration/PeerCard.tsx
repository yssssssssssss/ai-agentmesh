import { Sparkles, Share2, FolderClock } from 'lucide-react'
import { Avatar } from '../ui/Avatar'
import { Button } from '../ui/Button'
import type { RecommendedPeer } from '../../data/mockData'

interface PeerCardProps {
  peer: RecommendedPeer
  onCollab: () => void
}

export function PeerCard({ peer, onCollab }: PeerCardProps) {
  return (
    <div className="card-base flex flex-col p-5">
      <div className="flex items-center gap-3">
        <Avatar name={peer.name} tone={peer.tone} size="lg" />
        <div>
          <h3 className="text-base font-semibold text-white">{peer.name}</h3>
          <p className="text-xs text-slate-500">擅长 · {peer.domain}</p>
        </div>
      </div>

      <div className="mt-4 space-y-2.5 text-sm">
        <div className="flex items-center gap-2 text-slate-300">
          <Share2 className="h-4 w-4 text-mint-300" />
          可共享经验 <span className="font-semibold text-white tabular-nums">{peer.shareable}</span> 条
        </div>
        <div className="flex items-center gap-2 text-slate-300">
          <FolderClock className="h-4 w-4 text-knowledge" />
          最近帮助：{peer.recentProject}
        </div>
      </div>

      <Button
        variant="secondary"
        block
        className="mt-4"
        icon={<Sparkles className="h-4 w-4" />}
        onClick={onCollab}
      >
        发起协作
      </Button>
    </div>
  )
}
