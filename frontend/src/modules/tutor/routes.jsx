import { Routes, Route, Navigate } from 'react-router-dom'

import Landing from './pages/Landing.jsx'
import Chat from './pages/Chat.jsx'
import Nudges from './pages/Nudges.jsx'

export default function TutorRoutes() {
  return (
    <Routes>
      <Route index element={<Navigate to="landing" replace />} />
      <Route path="landing" element={<Landing />} />
      <Route path="chat" element={<Chat />} />
      <Route path="nudges" element={<Nudges />} />
    </Routes>
  )
}
