import { useState } from 'react'
import { BookMarked, CheckCircle2, ArrowRight, Sparkles } from 'lucide-react'
import { PageHeader } from '../components/ui/PageHeader'
import { Tabs, type TabItem } from '../components/ui/Tabs'
import { Button } from '../components/ui/Button'
import { KnowledgeCard } from '../components/knowledge/KnowledgeCard'
import { PendingKnowledgeCard } from '../components/knowledge/PendingKnowledgeCard'
import { ReuseSection } from '../components/knowledge/ReuseSection'
import { ConfirmKnowledgeModal } from '../components/knowledge/ConfirmKnowledgeModal'
import {
  PERSONAL_KNOWLEDGE,
  PROJECT_KNOWLEDGE,
  SHARED_KNOWLEDGE,
  NEW_KNOWLEDGE,
  type KnowledgeCardData,
} from '../data/mockData'
import { useDemo } from '../store/DemoContext'

const NEW_AS_CARD: KnowledgeCardData = {
  id: 'sh-new',
  title: NEW_KNOWLEDGE.title,
  summary: NEW_KNOWLEDGE.conclusion,
  tags: ['首屏效率', '刚共享'],
  project: '2026 618 家电会场',
  updated: '刚刚',
}

export function Knowledge() {
  const { pendingCount, sharedCount, reusedCount, knowledgeShared, showToast } = useDemo()
  const [tab, setTab] = useState('pending')
  const [confirmOpen, setConfirmOpen] = useState(false)

  const tabs: TabItem[] = [
    { key: 'pending', label: '待我确认', count: pendingCount },
    { key: 'personal', label: '个人知识', count: 24 },
    { key: 'project', label: '项目经验', count: 8 },
    { key: 'shared', label: '已共享', count: sharedCount },
    { key: 'reused', label: '被复用', count: reusedCount },
  ]

  const openCard = (title: string) => showToast(`已打开知识卡：${title}`, 'info')
  const sharedList = knowledgeShared ? [NEW_AS_CARD, ...SHARED_KNOWLEDGE] : SHARED_KNOWLEDGE

  return (
    <div className="space-y-6">
      <PageHeader
        title="我的知识"
        subtitle="数字人从你的工作中学到的经验，由你控制它如何进入项目和团队。"
      />

      <Tabs items={tabs} value={tab} onChange={setTab} />

      {/* 待我确认 */}
      {tab === 'pending' && (
        <div className="animate-fade-in">
          {pendingCount > 0 ? (
            <PendingKnowledgeCard onConfirm={() => setConfirmOpen(true)} />
          ) : (
            <div className="card-base flex flex-col items-center py-14 text-center">
              <span className="flex h-14 w-14 items-center justify-center rounded-full bg-mint-400/12 text-mint-300">
                <CheckCircle2 className="h-7 w-7" />
              </span>
              <h3 className="mt-4 text-base font-semibold text-white">待确认经验已全部处理</h3>
              <p className="mt-1.5 max-w-sm text-sm text-slate-400">
                「首屏核心入口效率判断」已确认并沉淀，已移动到「已共享」，家电设计组的数字人现在可以引用它。
              </p>
              <Button
                variant="subtle"
                className="mt-5"
                icon={<ArrowRight className="h-4 w-4" />}
                onClick={() => setTab('shared')}
              >
                查看已共享经验
              </Button>
            </div>
          )}
        </div>
      )}

      {/* 个人知识 */}
      {tab === 'personal' && (
        <div className="grid grid-cols-1 gap-4 animate-fade-in md:grid-cols-2 xl:grid-cols-3">
          {PERSONAL_KNOWLEDGE.map((k) => (
            <KnowledgeCard key={k.id} data={k} onClick={() => openCard(k.title)} />
          ))}
        </div>
      )}

      {/* 项目经验 */}
      {tab === 'project' && (
        <div className="grid grid-cols-1 gap-4 animate-fade-in md:grid-cols-2 xl:grid-cols-3">
          {PROJECT_KNOWLEDGE.map((k) => (
            <KnowledgeCard key={k.id} data={k} accent="knowledge" onClick={() => openCard(k.title)} />
          ))}
        </div>
      )}

      {/* 已共享 */}
      {tab === 'shared' && (
        <div className="animate-fade-in">
          {knowledgeShared && (
            <div className="mb-4 flex items-center gap-2.5 rounded-[12px] border border-mint-400/20 bg-mint-400/[0.05] px-4 py-3 text-sm text-mint-300">
              <Sparkles className="h-4 w-4" />
              新经验「{NEW_KNOWLEDGE.title}」已加入已共享，当前共 {sharedCount} 条。
            </div>
          )}
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {sharedList.map((k) => (
              <KnowledgeCard
                key={k.id}
                data={k}
                accent={k.id === 'sh-new' ? 'mint' : 'default'}
                onClick={() => openCard(k.title)}
              />
            ))}
          </div>
        </div>
      )}

      {/* 被复用 */}
      {tab === 'reused' && (
        <div className="animate-fade-in">
          <ReuseSection />
        </div>
      )}

      <div className="flex items-center gap-2 text-xs text-slate-600">
        <BookMarked className="h-3.5 w-3.5" />
        所有经验的共享与引用都需你本人确认，数字人不会在未授权时对外提供。
      </div>

      <ConfirmKnowledgeModal open={confirmOpen} onClose={() => setConfirmOpen(false)} />
    </div>
  )
}
