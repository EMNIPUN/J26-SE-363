import { Routes, Route, Navigate } from 'react-router-dom'

import Dashboard from './pages/student/Dashboard.jsx'
import Blackboard from './pages/student/Blackboard.jsx'
import Traceability from './pages/student/requirements/Traceability.jsx'
import Estimation from './pages/student/requirements/Estimation.jsx'
import SRSQuality from './pages/student/requirements/SRSQuality.jsx'
import Decomposition from './pages/student/requirements/Decomposition.jsx'
import InstructorDashboard from './pages/instructor/Dashboard.jsx'
import InstructorProjects from './pages/instructor/Projects.jsx'
import InstructorGroups from './pages/instructor/Groups.jsx'

export default function PlanningRoutes() {
  return (
    <Routes>
      <Route index element={<Navigate to="dashboard" replace />} />
      <Route path="dashboard" element={<Dashboard />} />
      <Route path="blackboard" element={<Blackboard />} />
      <Route path="requirements/traceability" element={<Traceability />} />
      <Route path="requirements/estimation" element={<Estimation />} />
      <Route path="requirements/srs-quality" element={<SRSQuality />} />
      <Route path="requirements/decomposition" element={<Decomposition />} />
      <Route path="instructor/dashboard" element={<InstructorDashboard />} />
      <Route path="instructor/projects" element={<InstructorProjects />} />
      <Route path="instructor/groups" element={<InstructorGroups />} />
    </Routes>
  )
}
