import { ClipboardCheck, Gauge, MessageCircle, ShieldAlert } from 'lucide-react'
import { useAuth } from '../../auth/useAuth.js'
import { getModule } from '../../constants/modules.js'
import StatCard from '../../components/StatCard.jsx'
import ComponentLinkGrid from '../../components/ComponentLinkGrid.jsx'
import Card from '../../components/Card.jsx'
import './DashboardHome.css'

const quickLinks = [
  { ...getModule('planning'), to: '/planning/dashboard' },
  { ...getModule('performance'), to: '/performance/student/my-progress' },
  { ...getModule('tutor'), to: '/tutor/landing' },
  { ...getModule('security'), to: '/security/dashboard' },
]

export default function StudentHome() {
  const { user } = useAuth()

  return (
    <div>
      <div className="dash-home__welcome">
        <div>
          <h1>Welcome back, {user.name.split(' ')[0]} 👋</h1>
          <p className="dash-home__date">Here's what's happening with your project today.</p>
        </div>
      </div>

      <div className="dash-home__stats">
        <StatCard icon={ClipboardCheck} label="Quality Gate Score" value="86%" trend="+4% this sprint" tone="success" />
        <StatCard icon={Gauge} label="My Contribution Score" value="7.8 / 10" tone="primary" />
        <StatCard icon={MessageCircle} label="Tutor Sessions" value="12" trend="3 this week" tone="primary" />
        <StatCard icon={ShieldAlert} label="Open Security Findings" value="3" tone="warning" />
      </div>

      <div className="dash-home__section">
        <div className="dash-home__section-head">
          <h2>Your components</h2>
          <p>Jump back into any of the four project components</p>
        </div>
        <ComponentLinkGrid items={quickLinks} />
      </div>

      <div className="dash-home__two-col">
        <Card className="dash-home__panel">
          <h3>Recent activity</h3>
          <ul className="dash-home__activity" style={{ marginTop: 14 }}>
            <li>
              <span className="dash-home__activity-dot" />
              <div>
                <span className="dash-home__activity-text">
                  SRS Quality Gate re-scored requirement <strong>REQ-014</strong> — now passing.
                </span>
                <span className="dash-home__activity-time">2 hours ago</span>
              </div>
            </li>
            <li>
              <span className="dash-home__activity-dot" style={{ background: 'var(--color-success)' }} />
              <div>
                <span className="dash-home__activity-text">Tutor suggested a sprint guidance session on estimation.</span>
                <span className="dash-home__activity-time">Yesterday</span>
              </div>
            </li>
            <li>
              <span className="dash-home__activity-dot" style={{ background: 'var(--color-danger)' }} />
              <div>
                <span className="dash-home__activity-text">
                  AEGIS flagged a hardcoded secret in <code>config.py</code>.
                </span>
                <span className="dash-home__activity-time">2 days ago</span>
              </div>
            </li>
          </ul>
        </Card>

        <Card className="dash-home__panel">
          <h3>Sprint checklist</h3>
          <ul className="dash-home__activity" style={{ marginTop: 14 }}>
            <li>
              <span className="dash-home__activity-dot" style={{ background: 'var(--color-success)' }} />
              <span className="dash-home__activity-text">Submit requirement decomposition</span>
            </li>
            <li>
              <span className="dash-home__activity-dot" />
              <span className="dash-home__activity-text">Review traceability gaps</span>
            </li>
            <li>
              <span className="dash-home__activity-dot" />
              <span className="dash-home__activity-text">Fix flagged security findings</span>
            </li>
          </ul>
        </Card>
      </div>
    </div>
  )
}
