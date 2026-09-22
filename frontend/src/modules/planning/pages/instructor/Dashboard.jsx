import { useNavigate } from 'react-router-dom'
import { Users, TrendingUp, AlertTriangle, Gavel } from 'lucide-react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
} from 'recharts'
import PageHeader from '../../../../shared/components/PageHeader.jsx'
import Card from '../../../../shared/components/Card.jsx'
import StatCard from '../../../../shared/components/StatCard.jsx'
import Badge from '../../../../shared/components/Badge.jsx'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { GROUPS, ARBITRATION_CASES, QUALITY_GATE_TREND } from '../../data/mockData.js'
import { RISK_TONE } from '../../utils.js'

export default function InstructorDashboard() {
  const navigate = useNavigate()

  const avgGate = Math.round(GROUPS.reduce((sum, g) => sum + g.qualityGate, 0) / GROUPS.length)
  const atRisk = GROUPS.filter((g) => g.risk === 'High').length
  const openFlags = ARBITRATION_CASES.filter((c) => c.status === 'Open').length
  const attentionGroups = GROUPS.filter((g) => g.risk !== 'Low').sort((a, b) => a.qualityGate - b.qualityGate)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Instructor Dashboard"
        breadcrumb={['Planning', 'Instructor', 'Dashboard']}
        description="Cross-project view of requirement quality-gate pass rates and open DART arbitration flags across every supervised group."
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Users} label="Supervised Groups" value={GROUPS.length} tone="primary" />
        <StatCard icon={TrendingUp} label="Avg. Quality Gate Pass Rate" value={`${avgGate}%`} trend="+5% vs last sprint" tone="success" />
        <StatCard icon={AlertTriangle} label="Groups At Risk" value={atRisk} tone="warning" />
        <StatCard icon={Gavel} label="Open DART Flags" value={openFlags} tone={openFlags > 0 ? 'warning' : 'success'} />
      </div>

      <Card>
        <h3 className="text-base font-semibold text-foreground mb-4">Quality gate pass rate — last 3 sprints</h3>
        <div style={{ width: '100%', height: 220 }}>
          <ResponsiveContainer>
            <LineChart data={QUALITY_GATE_TREND}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="sprint" tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }} />
              <YAxis tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }} unit="%" />
              <RechartsTooltip
                contentStyle={{
                  backgroundColor: 'var(--popover)',
                  border: '1px solid var(--border)',
                  borderRadius: 8,
                  fontSize: 12,
                }}
              />
              <Line type="monotone" dataKey="passRate" name="Pass rate" stroke="var(--chart-1)" strokeWidth={2} dot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card>
        <h3 className="text-base font-semibold text-foreground mb-4">Groups needing attention</h3>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Group</TableHead>
              <TableHead>Project</TableHead>
              <TableHead>Quality gate</TableHead>
              <TableHead className="w-[110px]">Risk</TableHead>
              <TableHead className="w-[110px]">Open flags</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {attentionGroups.map((g) => (
              <TableRow key={g.id} className="cursor-pointer" onClick={() => navigate(`/planning/instructor/groups/${g.id}`)}>
                <TableCell className="font-medium">{g.name}</TableCell>
                <TableCell className="text-muted-foreground max-w-xs truncate">{g.project}</TableCell>
                <TableCell>{g.qualityGate}%</TableCell>
                <TableCell>
                  <Badge tone={RISK_TONE[g.risk]}>{g.risk}</Badge>
                </TableCell>
                <TableCell>{g.openArbitrations}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
