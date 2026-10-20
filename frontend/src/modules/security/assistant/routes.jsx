import { Route, Routes } from 'react-router-dom'
import OverviewPage from './pages/OverviewPage.jsx'

// Mounted at /teams/:teamId/security/assistant/* (see ../routes.jsx). More pages are added here as they are built.
export default function AssistantRoutes() {
  return (
    <Routes>
      <Route index element={<OverviewPage />} />
    </Routes>
  )
}
