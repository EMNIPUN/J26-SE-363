import { ClipboardCheck, Gauge, MessageCircle, ShieldAlert } from 'lucide-react'
import { useAuth } from '../../auth/useAuth.js'
import { getModule } from '../../constants/modules.js'
import StatCard from '../../components/StatCard.jsx'
import ComponentLinkGrid from '../../components/ComponentLinkGrid.jsx'
import Card from '../../components/Card.jsx'

const quickLinks = [
  { ...getModule('planning'), to: '/planning/dashboard' },
  { ...getModule('performance'), to: '/performance/my-progress' },
  { ...getModule('security'), to: '/security/dashboard' },
]

export default function StudentHome() {
  const { user } = useAuth()

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
          Welcome back, {user.name.split(' ')[0]} 👋
        </h1>
        <p className="text-sm text-muted-foreground mt-1">Here's what's happening with your project today.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={ClipboardCheck} label="Quality Gate Score" value="86%" trend="+4% this sprint" tone="success" />
        <StatCard icon={Gauge} label="My Contribution Score" value="7.8 / 10" tone="primary" />
        <StatCard icon={MessageCircle} label="Tutor Sessions" value="12" trend="3 this week" tone="primary" />
        <StatCard icon={ShieldAlert} label="Open Security Findings" value="3" tone="warning" />
      </div>

      <div>
        <div className="flex items-baseline justify-between mb-4">
          <h2 className="text-xl font-bold tracking-tight text-foreground">Your components</h2>
          <p className="text-xs text-muted-foreground">Jump back into your project components</p>
        </div>
        <ComponentLinkGrid items={quickLinks} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <h3 className="text-base font-semibold text-foreground mb-4">Recent activity</h3>
          <ul className="space-y-4">
            <li className="flex items-start gap-3 text-sm">
              <span className="h-2 w-2 rounded-full bg-primary mt-1.5 shrink-0" />
              <div>
                <span className="text-foreground">
                  SRS Quality Gate re-scored requirement <strong>REQ-014</strong> — now passing.
                </span>
                <span className="block text-xs text-muted-foreground mt-0.5">2 hours ago</span>
              </div>
            </li>
            <li className="flex items-start gap-3 text-sm">
              <span className="h-2 w-2 rounded-full bg-emerald-500 mt-1.5 shrink-0" />
              <div>
                <span className="text-foreground">Tutor suggested a sprint guidance session on estimation.</span>
                <span className="block text-xs text-muted-foreground mt-0.5">Yesterday</span>
              </div>
            </li>
            <li className="flex items-start gap-3 text-sm">
              <span className="h-2 w-2 rounded-full bg-destructive mt-1.5 shrink-0" />
              <div>
                <span className="text-foreground">
                  AEGIS flagged a hardcoded secret in <code className="bg-muted px-1.5 py-0.5 rounded text-xs">config.py</code>.
                </span>
                <span className="block text-xs text-muted-foreground mt-0.5">2 days ago</span>
              </div>
            </li>
          </ul>
        </Card>

        <Card>
          <h3 className="text-base font-semibold text-foreground mb-4">Sprint checklist</h3>
          <ul className="space-y-3">
            <li className="flex items-center gap-3 text-sm">
              <span className="h-2 w-2 rounded-full bg-emerald-500 shrink-0" />
              <span className="text-foreground">Submit requirement decomposition</span>
            </li>
            <li className="flex items-center gap-3 text-sm">
              <span className="h-2 w-2 rounded-full bg-primary shrink-0" />
              <span className="text-foreground">Review traceability gaps</span>
            </li>
            <li className="flex items-center gap-3 text-sm">
              <span className="h-2 w-2 rounded-full bg-primary shrink-0" />
              <span className="text-foreground">Fix flagged security findings</span>
            </li>
          </ul>
        </Card>
      </div>
    </div>
  )
}

