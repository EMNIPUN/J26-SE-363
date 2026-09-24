import { Routes, Route, Navigate } from 'react-router-dom'
import RequireRole from '@/shared/auth/RequireRole'

import MyProgress from './pages/student/MyProgress.jsx'
import InstructorDashboard from './pages/instructor/Dashboard.jsx'
import StudentDetail from './pages/instructor/StudentDetail.jsx'
import Assessments from './pages/instructor/Assessments.jsx'
import Reports from './pages/instructor/Reports.jsx'

export default function PerformanceRoutes() {
  return (
    <Routes>
      <Route index element={<Navigate to="my-progress" replace />} />
      <Route path="my-progress" element={<MyProgress />} />

      {/* Instructor & Admin restricted routes */}
      <Route element={<RequireRole allowedRoles={['instructor', 'admin']} />}>
        <Route path="dashboard" element={<InstructorDashboard />} />
        <Route path="students" element={<StudentDetail />} />
        <Route path="assessments" element={<Assessments />} />
        <Route path="reports" element={<Reports />} />
      </Route>

      {/* Backward compatibility redirects for legacy /student/* and /instructor/* links */}
      <Route path="student/my-progress" element={<Navigate to="../my-progress" replace />} />
      <Route path="instructor/dashboard" element={<Navigate to="../dashboard" replace />} />
      <Route path="instructor/student-detail" element={<Navigate to="../students" replace />} />
      <Route path="instructor/assessments" element={<Navigate to="../assessments" replace />} />
      <Route path="instructor/reports" element={<Navigate to="../reports" replace />} />
    </Routes>
  )
}
