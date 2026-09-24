import { Users, TrendingUp, AlertTriangle, ShieldCheck } from 'lucide-react'
import { useAuth } from '../../auth/useAuth.js'
import { getModule } from '../../constants/modules.js'
import StatCard from '../../components/StatCard.jsx'
import ComponentLinkGrid from '../../components/ComponentLinkGrid.jsx'
import Card from '../../components/Card.jsx'
import Badge from '../../components/Badge.jsx'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

const quickLinks = [
  { ...getModule('planning'), to: '/planning/dashboard' },
  { ...getModule('performance'), to: '/performance/dashboard' },
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
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
          Welcome back, {user.name.split(' ').slice(-1)[0]} 👋
        </h1>
        <p className="text-sm text-muted-foreground mt-1">Supervising 8 groups across 3 batches this semester.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Users} label="Supervised Groups" value="8" tone="primary" />
        <StatCard icon={TrendingUp} label="Avg. Quality Gate Pass Rate" value="79%" trend="+6% vs last sprint" tone="success" />
        <StatCard icon={AlertTriangle} label="At-risk Students" value="4" tone="warning" />
        <StatCard icon={ShieldCheck} label="Open Vulnerabilities" value="11" tone="danger" />
      </div>

      <div>
        <div className="flex items-baseline justify-between mb-4">
          <h2 className="text-xl font-bold tracking-tight text-foreground">Your components</h2>
          <p className="text-xs text-muted-foreground">Oversight views across all four project components</p>
        </div>
        <ComponentLinkGrid items={quickLinks} />
      </div>

      <Card>
        <h3 className="text-base font-semibold text-foreground mb-4">Groups needing attention</h3>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Group</TableHead>
              <TableHead>Quality gate</TableHead>
              <TableHead className="w-[120px]">Risk</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {groups.map((g) => (
              <TableRow key={g.name}>
                <TableCell className="font-medium">{g.name}</TableCell>
                <TableCell>{g.gate}</TableCell>
                <TableCell>
                  <Badge tone={RISK_TONE[g.risk]}>{g.risk}</Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}

