import { Users, FolderKanban, ShieldAlert, Activity } from 'lucide-react'
import { useAuth } from '../../auth/useAuth.js'
import { getModule } from '../../constants/modules.js'
import StatCard from '../../components/StatCard.jsx'
import ComponentLinkGrid from '../../components/ComponentLinkGrid.jsx'
import Card from '../../components/Card.jsx'
import '../../styles/table.css'
import './DashboardHome.css'

const quickLinks = [
  { ...getModule('planning'), to: '/planning/instructor/dashboard' },
  { ...getModule('performance'), to: '/performance/instructor/dashboard' },
  { ...getModule('tutor'), to: '/tutor/landing' },
  { ...getModule('security'), to: '/security/dashboard' },
]

export default function AdminHome() {
  const { user } = useAuth()

  return (
    <div>
      <div className="dash-home__welcome">
        <div>
          <h1>Welcome back, {user.name} 👋</h1>
          <p className="dash-home__date">System-wide overview across every component.</p>
        </div>
      </div>

      <div className="dash-home__stats">
        <StatCard icon={Users} label="Total Users" value="342" tone="primary" />
        <StatCard icon={FolderKanban} label="Active Projects" value="28" tone="primary" />
        <StatCard icon={ShieldAlert} label="Open Security Issues" value="19" tone="danger" />
        <StatCard icon={Activity} label="System Uptime" value="99.9%" tone="success" />
      </div>

      <div className="dash-home__section">
        <div className="dash-home__section-head">
          <h2>Components</h2>
          <p>Read-only oversight into each teammate's component</p>
        </div>
        <ComponentLinkGrid items={quickLinks} />
      </div>

      <Card className="dash-home__panel">
        <h3>Recently added users</h3>
        <table className="table" style={{ marginTop: 14 }}>
          <thead>
            <tr>
              <th>Name</th>
              <th>Role</th>
              <th>Joined</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Kasun Fernando</td>
              <td>Student</td>
              <td>2 days ago</td>
            </tr>
            <tr>
              <td>Dr. Ishara Weerasinghe</td>
              <td>Instructor</td>
              <td>5 days ago</td>
            </tr>
            <tr>
              <td>Tharindu Jayasuriya</td>
              <td>Student</td>
              <td>1 week ago</td>
            </tr>
          </tbody>
        </table>
      </Card>
    </div>
  )
}
