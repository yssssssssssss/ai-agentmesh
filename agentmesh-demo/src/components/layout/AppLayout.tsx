import { createContext, useContext, useMemo, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { ProfileDrawer } from './ProfileDrawer'
import { SettingsDrawer } from './SettingsDrawer'
import { ToastViewport } from '../ui/ToastViewport'

interface LayoutUIValue {
  openProfile: () => void
  openSettings: () => void
}
const LayoutUIContext = createContext<LayoutUIValue | null>(null)

// eslint-disable-next-line react-refresh/only-export-components
export function useLayoutUI() {
  const ctx = useContext(LayoutUIContext)
  if (!ctx) throw new Error('useLayoutUI 必须在 AppLayout 内使用')
  return ctx
}

export function AppLayout() {
  const [profileOpen, setProfileOpen] = useState(false)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const { pathname } = useLocation()
  const fullBleed = pathname.startsWith('/workspace')

  const ui = useMemo<LayoutUIValue>(
    () => ({
      openProfile: () => setProfileOpen(true),
      openSettings: () => setSettingsOpen(true),
    }),
    [],
  )

  return (
    <LayoutUIContext.Provider value={ui}>
      <div className="flex h-screen overflow-hidden bg-canvas">
        <Sidebar onOpenSettings={ui.openSettings} onOpenProfile={ui.openProfile} />
        {fullBleed ? (
          // 工作台自管理布局与滚动（子导航 / 对话区 / 右侧面板）
          <main className="min-w-0 flex-1 overflow-hidden">
            <Outlet />
          </main>
        ) : (
          <main className="flex-1 overflow-y-auto">
            <div className="mx-auto min-h-full w-full max-w-[1320px] px-8 py-8 2xl:max-w-[1440px]">
              <Outlet />
            </div>
          </main>
        )}
      </div>

      <ProfileDrawer open={profileOpen} onClose={() => setProfileOpen(false)} />
      <SettingsDrawer open={settingsOpen} onClose={() => setSettingsOpen(false)} />
      <ToastViewport />
    </LayoutUIContext.Provider>
  )
}
