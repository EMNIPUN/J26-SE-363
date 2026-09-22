import { Routes, Route, Navigate } from 'react-router-dom'

import Dashboard from './pages/student/Dashboard.jsx'
import Estimation from './pages/student/requirements/Estimation.jsx'
import SRSQuality from './pages/student/requirements/SRSQuality.jsx'
import Decomposition from './pages/student/requirements/Decomposition.jsx'
import SprintManagement from './pages/student/SprintManagement.jsx'
import InstructorDashboard from './pages/instructor/Dashboard.jsx'
import InstructorProjects from './pages/instructor/Projects.jsx'
import InstructorGroups from './pages/instructor/Groups.jsx'
import GroupWorkspace from './pages/instructor/GroupWorkspace.jsx'
import ArbitrationOversight from './pages/instructor/ArbitrationOversight.jsx'

export default function PlanningRoutes() {
  return (
    <Routes>
      <Route index element={<Navigate to="dashboard" replace />} />
      <Route path="dashboard" element={<Dashboard />} />
      <Route path="requirements/srs-quality" element={<SRSQuality />} />
      <Route path="requirements/decomposition" element={<Decomposition />} />
      <Route path="requirements/estimation" element={<Estimation />} />
      <Route path="sprint-management" element={<SprintManagement />} />
      <Route path="instructor/dashboard" element={<InstructorDashboard />} />
      <Route path="instructor/projects" element={<InstructorProjects />} />
      <Route path="instructor/groups" element={<InstructorGroups />} />
      <Route path="instructor/groups/:groupId" element={<GroupWorkspace />} />
      <Route path="instructor/arbitration" element={<ArbitrationOversight />} />
    </Routes>
  )
}
