import { Routes, Route, Navigate } from 'react-router-dom'
import ModuleLayout from '../../shared/layout/ModuleLayout.jsx'
import { getModule } from '../../shared/constants/modules'

import Dashboard from './pages/student/Dashboard.jsx'
import Blackboard from './pages/student/Blackboard.jsx'
import Traceability from './pages/student/requirements/Traceability.jsx'
import Estimation from './pages/student/requirements/Estimation.jsx'
import SRSQuality from './pages/student/requirements/SRSQuality.jsx'
import Decomposition from './pages/student/requirements/Decomposition.jsx'
import InstructorDashboard from './pages/instructor/Dashboard.jsx'
import InstructorProjects from './pages/instructor/Projects.jsx'
import InstructorGroups from './pages/instructor/Groups.jsx'

const module = getModule('planning')

const navLinks = [
  { to: 'dashboard', label: 'Dashboard' },
  { to: 'blackboard', label: 'Blackboard' },
  { to: 'requirements/traceability', label: 'Requirements · Traceability' },
  { to: 'requirements/estimation', label: 'Requirements · Estimation' },
  { to: 'requirements/srs-quality', label: 'Requirements · SRS Quality' },
  { to: 'requirements/decomposition', label: 'Requirements · Decomposition' },
  { to: 'instructor/dashboard', label: 'Instructor · Dashboard' },
  { to: 'instructor/projects', label: 'Instructor · Projects' },
  { to: 'instructor/groups', label: 'Instructor · Groups' },
]

export default function PlanningRoutes() {
  return (
    <Routes>
      <Route element={<ModuleLayout module={module} navLinks={navLinks} />}>
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
      </Route>
    </Routes>
  )
}
