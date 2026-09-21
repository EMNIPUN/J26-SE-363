import { Routes, Route, Navigate } from 'react-router-dom'
import ModuleLayout from '../../shared/layout/ModuleLayout.jsx'
import { getModule } from '../../shared/constants/modules'

import MyProgress from './pages/student/MyProgress.jsx'
import InstructorDashboard from './pages/instructor/Dashboard.jsx'
import StudentDetail from './pages/instructor/StudentDetail.jsx'
import Assessments from './pages/instructor/Assessments.jsx'
import Reports from './pages/instructor/Reports.jsx'

const module = getModule('performance')

const navLinks = [
  { to: 'student/my-progress', label: 'Student · My Progress' },
  { to: 'instructor/dashboard', label: 'Instructor · Dashboard' },
  { to: 'instructor/student-detail', label: 'Instructor · Student Detail' },
  { to: 'instructor/assessments', label: 'Instructor · Assessments' },
  { to: 'instructor/reports', label: 'Instructor · Reports' },
]

export default function PerformanceRoutes() {
  return (
    <Routes>
      <Route element={<ModuleLayout module={module} navLinks={navLinks} />}>
        <Route index element={<Navigate to="student/my-progress" replace />} />
        <Route path="student/my-progress" element={<MyProgress />} />
        <Route path="instructor/dashboard" element={<InstructorDashboard />} />
        <Route path="instructor/student-detail" element={<StudentDetail />} />
        <Route path="instructor/assessments" element={<Assessments />} />
        <Route path="instructor/reports" element={<Reports />} />
      </Route>
    </Routes>
  )
}
