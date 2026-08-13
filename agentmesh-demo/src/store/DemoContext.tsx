import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

export type ShareScope = 'self' | 'project' | 'group' | 'more'

export const SCOPE_LABELS: Record<ShareScope, string> = {
  self: '仅自己',
  project: '当前项目',
  group: '家电设计组',
  more: '更多团队',
}

export type UnderstandingStatus = 'pending' | 'confirmed' | 'modified' | 'ignored'

export interface ImpactItem {
  id: string
  text: string
  time: string
  highlight?: boolean
}

interface Toast {
  id: number
  message: string
  tone: 'success' | 'info'
}

interface DemoState {
  /** 首屏核心入口效率经验：是否已确认并共享 */
  knowledgeShared: boolean
  /** 共享给的范围 */
  shareScope: ShareScope
  /** 已共享经验数量 12 → 13 */
  sharedCount: number
  /** 待我确认数量 1 → 0 */
  pendingCount: number
  /** 被复用条目数 9 → 10 */
  reusedCount: number
  /** 帮助同事人数 9 → 10 */
  peopleHelped: number
  /** 本月被引用次数 18 → 19 */
  monthlyCitations: number
  /** 王晨是否已获得引用授权 */
  wangchenAuthorized: boolean
  /** 我的影响动态流 */
  impactFeed: ImpactItem[]
  /** 首页"最近理解了我"三条确认状态 */
  understandings: Record<string, UnderstandingStatus>
  toasts: Toast[]
}

interface DemoActions {
  confirmAndShare: (scope: ShareScope) => void
  authorizeWangchen: () => void
  setUnderstanding: (id: string, status: UnderstandingStatus) => void
  showToast: (message: string, tone?: Toast['tone']) => void
  dismissToast: (id: number) => void
}

type DemoContextValue = DemoState & DemoActions

const DemoContext = createContext<DemoContextValue | null>(null)

const INITIAL_IMPACT: ImpactItem[] = [
  {
    id: 'imp-tag',
    text: '你沉淀的「活动标签信息层级规范」本周帮助了 4 位同事。',
    time: '本周',
    highlight: true,
  },
  {
    id: 'imp-floor',
    text: '你的「会场楼层优先级模型」被应用到 2024 家电超级品类日复盘。',
    time: '上周',
  },
]

let toastSeq = 1

export function DemoProvider({ children }: { children: ReactNode }) {
  const [knowledgeShared, setKnowledgeShared] = useState(false)
  const [shareScope, setShareScope] = useState<ShareScope>('group')
  const [sharedCount, setSharedCount] = useState(12)
  const [reusedCount, setReusedCount] = useState(9)
  const [peopleHelped, setPeopleHelped] = useState(9)
  const [monthlyCitations, setMonthlyCitations] = useState(18)
  const [wangchenAuthorized, setWangchenAuthorized] = useState(false)
  const [impactFeed, setImpactFeed] = useState<ImpactItem[]>(INITIAL_IMPACT)
  const [understandings, setUnderstandings] = useState<Record<string, UnderstandingStatus>>({
    'u-1': 'pending',
    'u-2': 'pending',
    'u-3': 'pending',
  })
  const [toasts, setToasts] = useState<Toast[]>([])

  const dismissToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const showToast = useCallback(
    (message: string, tone: Toast['tone'] = 'success') => {
      const id = toastSeq++
      setToasts((prev) => [...prev, { id, message, tone }])
      window.setTimeout(() => dismissToast(id), 3200)
    },
    [dismissToast],
  )

  const confirmAndShare = useCallback(
    (scope: ShareScope) => {
      setKnowledgeShared(true)
      setShareScope(scope)
      if (scope !== 'self') {
        setSharedCount((c) => (c < 13 ? 13 : c))
      }
      setImpactFeed((prev) => {
        if (prev.some((i) => i.id === 'imp-new-share')) return prev
        return [
          {
            id: 'imp-new-share',
            text: '你确认的「首屏核心入口效率判断」已沉淀，可供家电设计组数字人引用。',
            time: '刚刚',
            highlight: true,
          },
          ...prev,
        ]
      })
      showToast(`经验已确认并共享给「${SCOPE_LABELS[scope]}」`)
    },
    [showToast],
  )

  const authorizeWangchen = useCallback(() => {
    setWangchenAuthorized(true)
    setReusedCount((c) => c + 1)
    setPeopleHelped((c) => c + 1)
    setMonthlyCitations((c) => c + 1)
    setImpactFeed((prev) => {
      if (prev.some((i) => i.id === 'imp-wangchen')) return prev
      return [
        {
          id: 'imp-wangchen',
          text: '王晨的数字人已引用你的「首屏核心入口效率判断」，用于家电暑期会场改版。',
          time: '刚刚',
          highlight: true,
        },
        ...prev,
      ]
    })
    showToast('你的数字人已将经验提供给王晨，并保留来源与适用范围')
  }, [showToast])

  const setUnderstanding = useCallback(
    (id: string, status: UnderstandingStatus) => {
      setUnderstandings((prev) => ({ ...prev, [id]: status }))
      if (status === 'confirmed') showToast('已确认，你的数字人会强化这项理解')
      if (status === 'ignored') showToast('已忽略这条理解', 'info')
    },
    [showToast],
  )

  const value = useMemo<DemoContextValue>(
    () => ({
      knowledgeShared,
      shareScope,
      sharedCount,
      pendingCount: knowledgeShared ? 0 : 1,
      reusedCount,
      peopleHelped,
      monthlyCitations,
      wangchenAuthorized,
      impactFeed,
      understandings,
      toasts,
      confirmAndShare,
      authorizeWangchen,
      setUnderstanding,
      showToast,
      dismissToast,
    }),
    [
      knowledgeShared,
      shareScope,
      sharedCount,
      reusedCount,
      peopleHelped,
      monthlyCitations,
      wangchenAuthorized,
      impactFeed,
      understandings,
      toasts,
      confirmAndShare,
      authorizeWangchen,
      setUnderstanding,
      showToast,
      dismissToast,
    ],
  )

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useDemo() {
  const ctx = useContext(DemoContext)
  if (!ctx) throw new Error('useDemo 必须在 DemoProvider 内使用')
  return ctx
}
