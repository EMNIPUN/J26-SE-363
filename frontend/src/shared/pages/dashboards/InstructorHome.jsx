import { Users, TrendingUp, AlertTriangle, ShieldCheck } from 'lucide-react'
import { useAuth } from '../../auth/useAuth.js'
import { getModule } from '../../constants/modules.js'
import StatCard from '../../components/StatCard.jsx'
import ComponentLinkGrid from '../../components/ComponentLinkGrid.jsx'
import Card from '../../components/Card.jsx'
import Badge from '../../components/Badge.jsx'
import '../../styles/table.css'
import './DashboardHome.css'

const quickLinks = [
  { ...getModule('planning'), to: '/planning/instructor/dashboard' },
  { ...getModule('performance'), to: '/performance/instructor/dashboard' },
  { ...getModule('tutor'), to: '/tutor/landing' },
  { ...getModule('security'), to: '/security/dashboard' },
]

const groups = [
  { name: 'Group 07 — AEGIS', gate: '92%', risk: 'Low' },
  { name: 'Group 12 — TrackWise', gate: '74%', risk: 'Medium' },
  { name: 'Group 03 — NexaPlan', gate: '58%', risk: 'High' },
]

const RISK_TONE = { Low: 'success', Medium: 'warning', High: 'danger' }

export default function InstructorHome() {
  const { user } = useAuth()

  return (
    <div>
      <div className="dash-home__welcome">
        <div>
          <h1>Welcome back, {user.name.split(' ').slice(-1)[0]} 👋</h1>
          <p className="dash-home__date">Supervising 8 groups across 3 batches this semester.</p>
        </div>
      </div>

      <div className="dash-home__stats">
        <StatCard icon={Users} label="Supervised Groups" value="8" tone="primary" />
        <StatCard icon={TrendingUp} label="Avg. Quality Gate Pass Rate" value="79%" trend="+6% vs last sprint" tone="success" />
        <StatCard icon={AlertTriangle} label="At-risk Students" value="4" tone="warning" />
        <StatCard icon={ShieldCheck} label="Open Vulnerabilities" value="11" tone="danger" />
      </div>

      <div className="dash-home__section">
        <div className="dash-home__section-head">
          <h2>Your components</h2>
          <p>Oversight views across all four project components</p>
        </div>
        <ComponentLinkGrid items={quickLinks} />
      </div>

      <Card className="dash-home__panel">
        <h3>Groups needing attention</h3>
        <table className="table" style={{ marginTop: 14 }}>
          <thead>
            <tr>
              <th>Group</th>
              <th>Quality gate</th>
              <th>Risk</th>
            </tr>
          </thead>
          <tbody>
            {groups.map((g) => (
              <tr key={g.name}>
                <td>{g.name}</td>
                <td>{g.gate}</td>
                <td>
                  <Badge tone={RISK_TONE[g.risk]}>{g.risk}</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
