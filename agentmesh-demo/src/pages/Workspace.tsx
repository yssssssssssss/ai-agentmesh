import { useState } from 'react'
import { ConversationThread } from '../components/workspace/ConversationThread'
import { Composer } from '../components/workspace/Composer'
import { DetailPanel, type DetailContent } from '../components/workspace/DetailPanel'
import { ConfirmKnowledgeModal } from '../components/knowledge/ConfirmKnowledgeModal'
import type { WorkspaceRef } from '../data/mockData'
import { cn } from '../lib/cn'

export function Workspace() {
  const [content, setContent] = useState<DetailContent | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)

  // 当前被查看的引用 id（用于中间对话显示选中态）
  const activeRefId = content?.kind === 'ref' ? content.ref.id : undefined

  const openRef = (ref: WorkspaceRef) => setContent({ kind: 'ref', ref })
  const openProcess = () => setContent({ kind: 'process' })
  const openBrief = () => setContent({ kind: 'brief' })

  return (
    <>
      {/* 对话区 + 右侧详情面板（历史对话已收入左侧主导航） */}
      <div className="relative h-full overflow-hidden">
        {/* 对话滚动区：超宽屏面板打开时向左推挤内容 */}
        <div
          className={cn(
            'h-full overflow-y-auto transition-[padding] duration-300 ease-out',
            content && '2xl:pr-[456px]',
          )}
        >
          <div className="mx-auto max-w-[800px] px-6 pb-44 pt-8">
            <ConversationThread
              onOpenRef={openRef}
              onOpenProcess={openProcess}
              onOpenBrief={openBrief}
              onOpenConfirm={() => setConfirmOpen(true)}
              activeRefId={activeRefId}
            />
          </div>
        </div>

        {/* 底部固定输入框 */}
        <Composer />

        {/* 右侧通用详情面板：滑入 overlay，内部独立滚动，切换引用直接替换 */}
        <DetailPanel content={content} onClose={() => setContent(null)} />
      </div>

      <ConfirmKnowledgeModal open={confirmOpen} onClose={() => setConfirmOpen(false)} />
    </>
  )
}
