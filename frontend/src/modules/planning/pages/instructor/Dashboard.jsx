import { useNavigate, Link } from 'react-router-dom'
import { Users, TrendingUp, AlertTriangle, Gavel } from 'lucide-react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  Cell,
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
import DartButton from '../../components/DartButton.jsx'
import { GROUPS, ARBITRATION_CASES, QUALITY_GATE_TREND } from '../../data/mockData.js'
import { getGroupCompletion } from '../../stageStats.js'
import { RISK_TONE } from '../../utils.js'

const RISK_BAR_COLOR = { Low: 'var(--chart-3)', Medium: 'var(--chart-5)', High: 'var(--chart-4)' }
const CATEGORY_ORDER = ['COMPOUND', 'AMBIGUOUS', 'STRUCTURAL', 'NOVEL']

export default function InstructorDashboard() {
  const navigate = useNavigate()

  const avgGate = Math.round(GROUPS.reduce((sum, g) => sum + g.qualityGate, 0) / GROUPS.length)
  const escalated = ARBITRATION_CASES.filter((c) => c.status === 'Open' && (c.category === 'NOVEL' || c.confidenceAgreement < 40))
  const openFlags = ARBITRATION_CASES.filter((c) => c.status === 'Open').length

  const groupsWithCompletion = GROUPS.map((g) => ({ ...g, completion: getGroupCompletion(g) }))
  const atRisk = groupsWithCompletion.filter((g) => g.risk === 'High' || (g.completion != null && g.completion < 40))
  const attentionGroups = groupsWithCompletion
    .filter((g) => g.risk !== 'Low')
    .sort((a, b) => a.qualityGate - b.qualityGate)

  const qualityComparison = [...GROUPS].sort((a, b) => b.qualityGate - a.qualityGate)
  const categoryTally = CATEGORY_ORDER.map((cat) => ({
    category: cat,
    count: ARBITRATION_CASES.filter((c) => c.category === cat).length,
  }))

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
        <StatCard icon={AlertTriangle} label="Groups At Risk" value={atRisk.length} trend="Quality score + pipeline coverage" tone="warning" />
        <StatCard icon={Gavel} label="Escalated to You" value={escalated.length} trend={`${openFlags} open flags total`} tone={escalated.length > 0 ? 'danger' : 'success'} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <h3 className="text-base font-semibold text-foreground mb-1">Requirement quality — across teams</h3>
          <p className="text-xs text-muted-foreground mb-4">Quality gate pass rate per group, ranked</p>
          <div style={{ width: '100%', height: 220 }}>
            <ResponsiveContainer>
              <BarChart data={qualityComparison} layout="vertical" margin={{ left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis type="number" domain={[0, 100]} tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }} unit="%" />
                <YAxis type="category" dataKey="name" width={70} tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }} />
                <RechartsTooltip
                  contentStyle={{ backgroundColor: 'var(--popover)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
                  formatter={(value) => [`${value}%`, 'Quality gate']}
                />
                <Bar dataKey="qualityGate" radius={[0, 6, 6, 0]}>
                  {qualityComparison.map((g) => (
                    <Cell key={g.id} fill={RISK_BAR_COLOR[g.risk]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card>
          <h3 className="text-base font-semibold text-foreground mb-1">DART diagnostic pattern</h3>
          <p className="text-xs text-muted-foreground mb-4">Category distribution across the cohort</p>
          <div style={{ width: '100%', height: 220 }}>
            <ResponsiveContainer>
              <BarChart data={categoryTally}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="category" tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }} />
                <YAxis allowDecimals={false} tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }} />
                <RechartsTooltip contentStyle={{ backgroundColor: 'var(--popover)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }} />
                <Bar dataKey="count" name="Cases" fill="var(--chart-1)" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
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

      {escalated.length > 0 && (
        <Card className="border-destructive/30">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div>
              <h3 className="text-base font-semibold text-foreground">Escalated for your review</h3>
              <p className="text-xs text-muted-foreground">NOVEL-category or low-confidence DART cases the agents couldn't resolve on their own.</p>
            </div>
            <Link to="/planning/instructor/arbitration" className="text-xs font-medium text-primary hover:underline shrink-0">
              Open Arbitration Oversight →
            </Link>
          </div>
        </Card>
      )}

      <Card>
        <h3 className="text-base font-semibold text-foreground mb-1">Groups needing attention</h3>
        <p className="text-xs text-muted-foreground mb-4">Ranked by quality gate score; "at risk" combines quality score and pipeline coverage</p>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Group</TableHead>
              <TableHead>Project</TableHead>
              <TableHead>Quality gate</TableHead>
              <TableHead className="w-[100px]">Pipeline</TableHead>
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
                <TableCell>{g.completion != null ? `${g.completion}%` : '—'}</TableCell>
                <TableCell>
                  <Badge tone={RISK_TONE[g.risk]}>{g.risk}</Badge>
                </TableCell>
                <TableCell>{g.openArbitrations}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <DartButton context="cohort" />
    </div>
  )
}
