import { Routes, Route, Navigate } from 'react-router-dom'
import RequireRole from '@/shared/auth/RequireRole'
import { useAuth } from '@/shared/auth/useAuth'

import Dashboard from './pages/student/Dashboard.jsx'
import Blackboard from './pages/student/Blackboard.jsx'
import Traceability from './pages/student/requirements/Traceability.jsx'
import Estimation from './pages/student/requirements/Estimation.jsx'
import SRSQuality from './pages/student/requirements/SRSQuality.jsx'
import Decomposition from './pages/student/requirements/Decomposition.jsx'
import InstructorDashboard from './pages/instructor/Dashboard.jsx'
import InstructorProjects from './pages/instructor/Projects.jsx'
import InstructorGroups from './pages/instructor/Groups.jsx'

function PlanningDashboard() {
  const { user } = useAuth()
  if (user?.role === 'instructor' || user?.role === 'admin') {
    return <InstructorDashboard />
  }
  return <Dashboard />
}

export default function PlanningRoutes() {
  return (
    <Routes>
      <Route index element={<Navigate to="dashboard" replace />} />
      <Route path="dashboard" element={<PlanningDashboard />} />
      <Route path="blackboard" element={<Blackboard />} />
      <Route path="requirements/traceability" element={<Traceability />} />
      <Route path="requirements/estimation" element={<Estimation />} />
      <Route path="requirements/srs-quality" element={<SRSQuality />} />
      <Route path="requirements/decomposition" element={<Decomposition />} />

      {/* Instructor & Admin restricted routes */}
      <Route element={<RequireRole allowedRoles={['instructor', 'admin']} />}>
        <Route path="projects" element={<InstructorProjects />} />
        <Route path="groups" element={<InstructorGroups />} />
      </Route>

      {/* Backward compatibility redirects for legacy /instructor/* links */}
      <Route path="instructor/dashboard" element={<Navigate to="../dashboard" replace />} />
      <Route path="instructor/projects" element={<Navigate to="../projects" replace />} />
      <Route path="instructor/groups" element={<Navigate to="../groups" replace />} />
    </Routes>
  )
}
