import { useState } from 'react'
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
  FolderPlus,
  GitBranch,
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

// Live API Hooks
import { useTeams } from '@/shared/hooks/useTeamManagement'

// Team Roster Drawer
import TeamRosterDrawer from '@/shared/components/roster/TeamRosterDrawer'

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
  const { selectedGroup, selectedBatch } = useScope()

  // Drawer modal state
  const [activeDrawerTeamId, setActiveDrawerTeamId] = useState(null)

  // Fetch live teams from the database for the active batch
  const currentBatchId = selectedBatch?.id || 'batch-2026-y4s1'
  const { data: liveTeams = [], isLoading: teamsLoading } = useTeams(currentBatchId)

  const team = (path) => `/teams/${selectedGroup?.code || 'J26-SE-363'}${path}`
  const rawGroups = Array.isArray(GROUPS) ? GROUPS : []
  const groups = [...rawGroups].sort((a, b) => (RISK_ORDER[a?.risk] ?? 3) - (RISK_ORDER[b?.risk] ?? 3))
  const avgGate = rawGroups.length
    ? Math.round(rawGroups.reduce((sum, g) => sum + (g?.qualityGate || 0), 0) / rawGroups.length)
    : 79
  const atRiskGroups = rawGroups.filter((g) => g?.risk && g.risk !== 'Low').length

  const quickLinks = [
    { ...getModule('planning'), to: team('/planning/instructor/dashboard') },
    { ...getModule('performance'), to: team('/performance/dashboard') },
    { ...getModule('security'), to: team('/security/dashboard') },
  ]

  const totalTeamsCount = (Array.isArray(liveTeams) && liveTeams.length > 0)
    ? liveTeams.length
    : rawGroups.length

  return (
    <div className="space-y-8">
      {/* HEADER WITH UNIFIED GUIDED SETUP CTA */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-medium text-muted-foreground">{formatToday()}</p>
          <h1 className="mt-1 text-3xl font-bold tracking-tight text-foreground">
            {getGreeting()}, {getShortName(user?.name)}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            You&apos;re supervising {totalTeamsCount} teams this semester — {atRiskGroups} need a closer look.
          </p>
        </div>

        {/* PRIMARY ACTIONS: GUIDED WIZARD + QUICK REPORT */}
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <Button asChild variant="outline" size="lg">
            <Link to={team('/performance/reports')}>
              <FileBarChart className="h-4 w-4 mr-1.5" />
              Reports
            </Link>
          </Button>

          <Button asChild size="lg" className="shadow-xs cursor-pointer">
            <Link to={team('/projects/new')}>
              <FolderPlus className="h-4 w-4 mr-1.5" />
              Create Project
            </Link>
          </Button>
        </div>
      </div>

      {/* KPI METRIC CARDS */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={Users}
          label="Supervised teams"
          value={totalTeamsCount}
          trend={liveTeams.length > 0 ? 'Live from database' : 'Across 2 batches'}
          tone="primary"
        />
        <StatCard
          icon={TrendingUp}
          label="Avg. quality gate"
          value={`${avgGate}%`}
          trend="+6% vs last sprint"
          tone="success"
        />
        <StatCard
          icon={AlertTriangle}
          label="At-risk students"
          value="4"
          trend="1 high, 3 medium"
          tone="warning"
        />
        <StatCard
          icon={ShieldCheck}
          label="Open vulnerabilities"
          value="11"
          trend="2 critical"
          tone="danger"
        />
      </div>

      {/* MAIN TWO-COLUMN CONTENT */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* LEFT COLUMN: ATTENTION ITEMS */}
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

        {/* RIGHT COLUMN: TEAMS OVERVIEW */}
        <Card className="lg:col-span-2 p-0 gap-0 overflow-hidden">
          <div className="flex items-center justify-between px-6 pt-5 pb-3">
            <div>
              <h2 className="text-base font-semibold text-foreground">Groups & Teams overview</h2>
              <p className="text-xs text-muted-foreground">
                Active teams supervised in cohort <span className="font-mono text-foreground font-semibold">{currentBatchId}</span>
              </p>
            </div>
            <Link
              to={team('/planning/instructor/groups')}
              className="text-xs font-medium text-primary hover:underline"
            >
              View all groups
            </Link>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-6">Team Code & Name</TableHead>
                <TableHead className="w-[120px]">Repo</TableHead>
                <TableHead className="w-[100px]">Status</TableHead>
                <TableHead className="w-[90px] pr-6 text-right">Roster</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {teamsLoading ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-8 text-xs text-muted-foreground">
                    Loading teams roster...
                  </TableCell>
                </TableRow>
              ) : (Array.isArray(liveTeams) && liveTeams.length > 0) ? (
                liveTeams.map((t) => (
                  <TableRow key={t.id} className="hover:bg-muted/40 transition">
                    <TableCell className="pl-6">
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-xs text-primary">{t.team_code}</span>
                        <span className="font-medium text-foreground">{t.name}</span>
                      </div>
                      <p className="text-[11px] text-muted-foreground mt-0.5">
                        Leader: <span className="font-mono text-foreground">{t.leader_student_id || 'Not assigned'}</span>
                      </p>
                    </TableCell>
                    <TableCell>
                      {t.repo_url ? (
                        <span className="inline-flex items-center gap-1 font-mono text-[11px] text-muted-foreground truncate max-w-[110px]">
                          <GitBranch className="h-3 w-3 text-emerald-500 shrink-0" />
                          Repo
                        </span>
                      ) : (
                        <span className="text-muted-foreground text-[11px]">None</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-[10px] capitalize">
                        {t.status || 'active'}
                      </Badge>
                    </TableCell>
                    <TableCell className="pr-6 text-right">
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="text-xs text-primary hover:text-primary font-medium"
                        onClick={() => setActiveDrawerTeamId(t.id)}
                      >
                        Manage
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              ) : (
                /* Fallback to mock GROUPS when live DB has no teams */
                groups.map((g) => (
                  <TableRow key={g.id}>
                    <TableCell className="pl-6">
                      <p className="font-medium text-foreground">{g.name}</p>
                      <p className="text-xs text-muted-foreground truncate max-w-[260px]">{g.project}</p>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress value={g.qualityGate} className="h-1.5 w-16" />
                        <span className="text-xs font-medium text-foreground tabular-nums">{g.qualityGate}%</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge tone={RISK_TONE[g.risk]}>{g.risk}</Badge>
                    </TableCell>
                    <TableCell className="pr-6 text-right">
                      <Button asChild variant="ghost" size="sm">
                        <Link to={team(`/planning/instructor/groups/${g.id}`)}>
                          Open
                        </Link>
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </Card>
      </div>

      {/* COMPONENT OVERSIGHT VIEWS */}
      <section>
        <div className="flex items-baseline justify-between mb-4 gap-4">
          <h2 className="text-xl font-bold tracking-tight text-foreground">Project components</h2>
          <p className="text-xs text-muted-foreground hidden sm:block">Oversight views for each research component</p>
        </div>
        <ComponentLinkGrid items={quickLinks} />
      </section>

      {/* TEAM DETAIL & ROSTER MANAGEMENT DRAWER */}
      <TeamRosterDrawer
        open={Boolean(activeDrawerTeamId)}
        onOpenChange={(isOpen) => !isOpen && setActiveDrawerTeamId(null)}
        teamId={activeDrawerTeamId}
      />
    </div>
  )
}
