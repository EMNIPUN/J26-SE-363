import { Routes, Route, Navigate } from 'react-router-dom'
import ModuleLayout from '../../shared/layout/ModuleLayout.jsx'
import { getModule } from '../../shared/constants/modules'

import Landing from './pages/Landing.jsx'
import Chat from './pages/Chat.jsx'
import Nudges from './pages/Nudges.jsx'

const module = getModule('tutor')

const navLinks = [
  { to: 'landing', label: 'Landing' },
  { to: 'chat', label: 'Chat' },
  { to: 'nudges', label: 'Nudges' },
]

export default function TutorRoutes() {
  return (
    <Routes>
      <Route element={<ModuleLayout module={module} navLinks={navLinks} />}>
        <Route index element={<Navigate to="landing" replace />} />
        <Route path="landing" element={<Landing />} />
        <Route path="chat" element={<Chat />} />
        <Route path="nudges" element={<Nudges />} />
      </Route>
    </Routes>
  )
}
