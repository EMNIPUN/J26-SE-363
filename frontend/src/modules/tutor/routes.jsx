import { Navigate, Route, Routes } from 'react-router-dom'
import { useTeamPath } from '../../shared/hooks/useTeamPath.js'
import Assessments from './pages/Assessments.jsx'
import Chat from './pages/Chat.jsx'
import Practice from './pages/Practice.jsx'
import Progress from './pages/Progress.jsx'
import SprintGuidance from './pages/SprintGuidance.jsx'

function RedirectToGuidance() {
  const team = useTeamPath()
  return <Navigate to={team('/tutor/guidance')} replace />
}

export default function TutorRoutes() {
  return (
    <Routes>
      <Route index element={<RedirectToGuidance />} />
      <Route path="guidance" element={<SprintGuidance />} />
      <Route path="chat" element={<Chat />} />
      <Route path="practice" element={<Practice />} />
      <Route path="practice/:exerciseId" element={<Practice />} />
      <Route path="assessments" element={<Assessments />} />
      <Route path="assessments/:assessmentId" element={<Assessments />} />
      <Route path="progress" element={<Progress />} />
      <Route path="landing" element={<RedirectToGuidance />} />
      <Route path="nudges" element={<RedirectToGuidance />} />
    </Routes>
  )
}
