import { Routes, Route, Navigate } from 'react-router-dom'

import MyProgress from './pages/student/MyProgress.jsx'
import InstructorDashboard from './pages/instructor/Dashboard.jsx'
import StudentDetail from './pages/instructor/StudentDetail.jsx'
import Assessments from './pages/instructor/Assessments.jsx'
import Reports from './pages/instructor/Reports.jsx'

export default function PerformanceRoutes() {
  return (
    <Routes>
      <Route index element={<Navigate to="student/my-progress" replace />} />
      <Route path="student/my-progress" element={<MyProgress />} />
      <Route path="instructor/dashboard" element={<InstructorDashboard />} />
      <Route path="instructor/student-detail" element={<StudentDetail />} />
      <Route path="instructor/assessments" element={<Assessments />} />
      <Route path="instructor/reports" element={<Reports />} />
    </Routes>
  )
}
