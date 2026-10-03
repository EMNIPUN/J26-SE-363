import { Routes, Route, Navigate, Outlet } from 'react-router-dom'

import NotFound from '@/shared/pages/NotFound.jsx'
import TutorPage from './pages/Tutor/TutorPage.jsx'
import SprintGuidancePage from './pages/Learning/SprintGuidancePage.jsx'
import ActivityPage from './pages/Activity/ActivityPage.jsx'
import ExercisesPage from './pages/Exercise/ExercisesPage.jsx'
import AssessmentsPage from './pages/Quiz/AssessmentsPage.jsx'
import ProgressPage from './pages/Results/ProgressPage.jsx'
import ResultsPage from './pages/Results/ResultsPage.jsx'

const LEGACY_PATHS = ['landing', 'nudges']

// Leaves room below the last control for the floating AI Copilot button,
// which the shell shows on every page except Tutor Chat.
function ScrollablePage() {
  return (
    <div className="pb-16">
      <Outlet />
    </div>
  )
}

export default function TutorRoutes() {
  return (
    <Routes>
      <Route index element={<Navigate to="chat" replace />} />
      <Route path="chat" element={<TutorPage />} />
      <Route element={<ScrollablePage />}>
        <Route path="learning" element={<SprintGuidancePage />} />
        <Route path="activity/:activityId" element={<ActivityPage />} />
        <Route path="exercise" element={<ExercisesPage />} />
        <Route path="quiz" element={<AssessmentsPage />} />
        <Route path="results" element={<ProgressPage />} />
        <Route path="results/:id" element={<ResultsPage />} />
      </Route>
      {LEGACY_PATHS.map((path) => (
        <Route key={path} path={path} element={<Navigate to="../chat" relative="path" replace />} />
      ))}
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
