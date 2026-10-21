import { Route, Routes } from 'react-router-dom'
import FindingDetailPage from './pages/FindingDetailPage.jsx'
import AgentsPage from './pages/AgentsPage.jsx'
import LearningPage from './pages/LearningPage.jsx'
import FindingsPage from './pages/FindingsPage.jsx'
import OverviewPage from './pages/OverviewPage.jsx'

// Mounted at /teams/:teamId/security/assistant/* (see ../routes.jsx). More pages are added here as they are built.
export default function AssistantRoutes() {
  return (
    <Routes>
      <Route index element={<OverviewPage />} />
      <Route path="findings" element={<FindingsPage />} />
      <Route path="findings/:category" element={<FindingsPage />} />
      <Route path="findings/:category/:groupId" element={<FindingDetailPage />} />
      <Route path="learning" element={<LearningPage />} />
      <Route path="agents" element={<AgentsPage />} />
    </Routes>
  )
}
