import { Routes, Route, Navigate, useSearchParams } from 'react-router-dom'
import RequireRole from '@/shared/auth/RequireRole'
import { useAuth } from '@/shared/auth/useAuth'

import MyAssessment from './pages/student/MyAssessment.jsx'
import TeamAssessment from './pages/instructor/TeamAssessment.jsx'
import StudentAssessment from './pages/instructor/StudentAssessment.jsx'
import StudentQuestions from './pages/instructor/StudentQuestions.jsx'
import RunPage from './pages/instructor/RunPage.jsx'
import Method from './pages/instructor/Method.jsx'

function PerformanceIndex() {
  const { user } = useAuth()
  return <Navigate to={user?.role === 'instructor' || user?.role === 'admin' ? 'team/results' : 'my-assessment'} replace />
}

/** The earlier address of the team page (?tab=runs) goes to the address of that tab. */
function LegacyAssessment() {
  const [params] = useSearchParams()
  const rest = new URLSearchParams(params)
  const tab = rest.get('tab') || 'results'
  rest.delete('tab')
  return <Navigate to={`../team/${tab}${rest.toString() ? `?${rest}` : ''}`} replace />
}

/**
 * Performance assessment, inside a team. Lecturers (and administrators) see the whole team and the pipeline of every run;
 * a student sees only their own assessment. The API enforces the same rule: these guards are only the first line.
 */
export default function PerformanceRoutes() {
  return (
    <Routes>
      <Route index element={<PerformanceIndex />} />
      <Route path="my-assessment" element={<MyAssessment />} />

      <Route element={<RequireRole allowedRoles={['instructor', 'admin']} />}>
        <Route path="team" element={<Navigate to="results" replace />} />
        <Route path="team/:tab" element={<TeamAssessment />} />
        <Route path="assessment" element={<LegacyAssessment />} />
        <Route path="students/:studentId" element={<StudentAssessment />} />
        <Route path="students/:studentId/questions" element={<StudentQuestions />} />
        <Route path="runs/:runId" element={<RunPage />} />
        <Route path="method" element={<Method />} />
      </Route>

      {/* links from the earlier prototype pages */}
      <Route path="my-progress" element={<Navigate to="../my-assessment" replace />} />
      <Route path="dashboard" element={<Navigate to="../team/results" replace />} />
      <Route path="students" element={<Navigate to="../team/results" replace />} />
      <Route path="assessments" element={<Navigate to="../team/results" replace />} />
      <Route path="reports" element={<Navigate to="../team/runs" replace />} />
    </Routes>
  )
}
