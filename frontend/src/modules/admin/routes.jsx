import { Routes, Route } from 'react-router-dom'
import Users from './pages/Users.jsx'
import Settings from './pages/Settings.jsx'

export default function AdminRoutes() {
  return (
    <Routes>
      <Route path="users" element={<Users />} />
      <Route path="settings" element={<Settings />} />
    </Routes>
  )
}
