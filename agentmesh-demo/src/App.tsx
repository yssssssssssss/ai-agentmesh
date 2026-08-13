import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { DigitalSelf } from './pages/DigitalSelf'
import { Workspace } from './pages/Workspace'
import { Insights } from './pages/Insights'
import { Knowledge } from './pages/Knowledge'
import { Collaboration } from './pages/Collaboration'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/digital-self" replace />} />
        <Route path="/digital-self" element={<DigitalSelf />} />
        <Route path="/workspace" element={<Workspace />} />
        <Route path="/insights" element={<Insights />} />
        <Route path="/knowledge" element={<Knowledge />} />
        <Route path="/collaboration" element={<Collaboration />} />
        <Route path="*" element={<Navigate to="/digital-self" replace />} />
      </Route>
    </Routes>
  )
}
