import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowRight,
  FileBarChart,
  Gavel,
  ShieldAlert,
  ShieldCheck,
  TrendingUp,
  UserX,
  Users,
} from 'lucide-react'
import { useAuth } from '../../auth/useAuth.js'
import { useScope } from '../../context/useScope.js'
import { getModule } from '../../constants/modules.js'
import { getGreeting, getShortName, formatToday } from '../../utils/greeting.js'
import StatCard from '../../components/StatCard.jsx'
import ComponentLinkGrid from '../../components/ComponentLinkGrid.jsx'
import Card from '../../components/Card.jsx'
import Badge from '../../components/Badge.jsx'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { GROUPS } from '../../../modules/planning/data/mockData.js'

const RISK_TONE = { Low: 'success', Medium: 'warning', High: 'danger' }
const RISK_ORDER = { High: 0, Medium: 1, Low: 2 }

const ATTENTION_ITEMS = [
  {
    id: 'arb',
    icon: Gavel,
    tone: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400',
    title: '4 arbitration cases escalated to you',
    detail: 'DART could not reach agreement on Group 12 and Group 03 requirements.',
    path: '/planning/instructor/arbitration',
    cta: 'Review cases',
  },
  {
    id: 'risk',
    icon: UserX,
    tone: 'bg-destructive/10 text-destructive',
    title: '1 student predicted high-risk',
    detail: 'Low commit activity and 45% stand-up attendance this sprint.',
    path: '/performance/students',
    cta: 'View student',
  },
  {
    id: 'sec',
    icon: ShieldAlert,
    tone: 'bg-destructive/10 text-destructive',
    title: '2 critical vulnerabilities open',
    detail: 'Hardcoded secret and SQL injection findings awaiting remediation.',
    path: '/security/dashboard',
    cta: 'Open report',
  },
]

export default function InstructorHome() {
  const { user } = useAuth()
  const { selectedGroup } = useScope()

  const team = (path) => `/teams/${selectedGroup?.code}${path}`
  const groups = [...GROUPS].sort((a, b) => RISK_ORDER[a.risk] - RISK_ORDER[b.risk])
  const avgGate = Math.round(GROUPS.reduce((sum, g) => sum + g.qualityGate, 0) / GROUPS.length)
  const atRiskGroups = GROUPS.filter((g) => g.risk !== 'Low').length

  const quickLinks = [
    { ...getModule('planning'), to: team('/planning/instructor/dashboard') },
    { ...getModule('performance'), to: team('/performance/dashboard') },
    { ...getModule('security'), to: team('/security/dashboard') },
  ]

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-medium text-muted-foreground">{formatToday()}</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-foreground">
            {getGreeting()}, {getShortName(user.name)}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            You&apos;re supervising {GROUPS.length} groups this semester — {atRiskGroups} need a closer look.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <Button asChild variant="outline" size="lg">
            <Link to={team('/performance/reports')}>
              <FileBarChart className="h-4 w-4" />
              Reports
            </Link>
          </Button>
          <Button asChild size="lg">
            <Link to={team('/planning/instructor/arbitration')}>
              <Gavel className="h-4 w-4" />
              Review arbitration
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Users} label="Supervised groups" value={GROUPS.length} trend="Across 2 batches" tone="primary" />
        <StatCard icon={TrendingUp} label="Avg. quality gate" value={`${avgGate}%`} trend="+6% vs last sprint" tone="success" />
        <StatCard icon={AlertTriangle} label="At-risk students" value="4" trend="1 high, 3 medium" tone="warning" />
        <StatCard icon={ShieldCheck} label="Open vulnerabilities" value="11" trend="2 critical" tone="danger" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="gap-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-foreground">Needs your attention</h2>
            <Badge tone="warning">{ATTENTION_ITEMS.length}</Badge>
          </div>
          <ul className="space-y-2">
            {ATTENTION_ITEMS.map((item) => {
              const Icon = item.icon
              return (
                <li key={item.id}>
                  <Link
                    to={team(item.path)}
                    className="group flex items-start gap-3 rounded-lg border border-border/60 p-3 transition-colors hover:bg-muted/60 outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${item.tone}`}>
                      <Icon className="h-4 w-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-medium text-foreground">{item.title}</span>
                      <span className="mt-0.5 block text-xs text-muted-foreground">{item.detail}</span>
                      <span className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-primary">
                        {item.cta}
                        <ArrowRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" />
                      </span>
                    </span>
                  </Link>
                </li>
              )
            })}
          </ul>
        </Card>

        <Card className="lg:col-span-2 p-0 gap-0 overflow-hidden">
          <div className="flex items-center justify-between px-6 pt-5 pb-3">
            <div>
              <h2 className="text-base font-semibold text-foreground">Groups overview</h2>
              <p className="text-xs text-muted-foreground">Sorted by risk — highest first</p>
            </div>
            <Link to={team('/planning/instructor/groups')} className="text-xs font-medium text-primary hover:underline">
              View all groups
            </Link>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-6">Group</TableHead>
                <TableHead className="w-[170px]">Quality gate</TableHead>
                <TableHead className="w-[90px]">Risk</TableHead>
                <TableHead className="w-[80px] pr-6 text-right">
                  <span className="sr-only">Actions</span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {groups.map((g) => (
                <TableRow key={g.id}>
                  <TableCell className="pl-6">
                    <p className="font-medium text-foreground">{g.name}</p>
                    <p className="text-xs text-muted-foreground truncate max-w-[260px]">{g.project}</p>
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Progress value={g.qualityGate} className="h-1.5 w-20" aria-label={`${g.name} quality gate`} />
                      <span className="text-xs font-medium text-foreground tabular-nums">{g.qualityGate}%</span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge tone={RISK_TONE[g.risk]}>{g.risk}</Badge>
                  </TableCell>
                  <TableCell className="pr-6 text-right">
                    <Button asChild variant="ghost" size="sm">
                      <Link to={team(`/planning/instructor/groups/${g.id}`)} aria-label={`Open ${g.name}`}>
                        Open
                      </Link>
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      </div>

      <section>
        <div className="flex items-baseline justify-between mb-4 gap-4">
          <h2 className="text-xl font-bold tracking-tight text-foreground">Project components</h2>
          <p className="text-xs text-muted-foreground hidden sm:block">Oversight views for each component</p>
        </div>
        <ComponentLinkGrid items={quickLinks} />
      </section>
    </div>
  )
}
