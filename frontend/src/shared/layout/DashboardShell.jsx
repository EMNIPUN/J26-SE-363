import { Outlet } from 'react-router-dom'
import TopNavbar from './TopNavbar.jsx'
import Sidebar from './Sidebar.jsx'
import { useAuth } from '../auth/useAuth.js'
import { getNavForRole } from './navConfig.js'
import './DashboardShell.css'

const PORTAL_LABEL = {
  student: 'Student Portal',
  instructor: 'Instructor Portal',
  admin: 'Admin Portal',
}

export default function DashboardShell() {
  const { user } = useAuth()
  const sections = getNavForRole(user.role)

  return (
    <div className="dashboard-shell">
      <TopNavbar />
      <div className="dashboard-shell__body">
        <Sidebar sections={sections} portalLabel={PORTAL_LABEL[user.role]} />
        <main className="dashboard-shell__content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
