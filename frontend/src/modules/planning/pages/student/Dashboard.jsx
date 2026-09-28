import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ClipboardList,
  ShieldCheck,
  Gauge,
  Gavel,
  Sparkles,
  User,
  KanbanSquare,
  Clock,
  Users,
  Search,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  XCircle,
} from 'lucide-react'
import PageHeader from '../../../../shared/components/PageHeader.jsx'
import Card from '../../../../shared/components/Card.jsx'
import Badge from '../../../../shared/components/Badge.jsx'
import Button from '../../../../shared/components/Button.jsx'
import AvatarComp from '../../../../shared/components/Avatar.jsx'
import { Progress } from '@/components/ui/progress'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import QualityRadarChart from '../../components/QualityRadarChart.jsx'
import DartButton from '../../components/DartButton.jsx'
import { usePlanningData } from '../../context/usePlanningData.js'
import { QUALITY_DIMENSIONS, ARBITRATION_CASES, GROUPS, getArbitrationForRequirement } from '../../data/mockData.js'
import { computeStageStats, getNextAction, STAGE_ORDER } from '../../stageStats.js'
import { ARBITRATION_CATEGORY_TONE, GATE_STATUS_TONE, formatRelativeTime } from '../../utils.js'

const PRIORITY_TONE = { High: 'danger', Medium: 'warning', Low: 'neutral' }
const GATE_STATUS_LABEL = { Passing: 'Passed', 'Needs Review': 'Review', Failing: 'Blocked' }
const ROW_STATUS_TONE = { ready: 'success', waiting: 'primary', attention: 'warning', blocked: 'danger' }
const CATEGORY_ORDER = ['COMPOUND', 'AMBIGUOUS', 'STRUCTURAL', 'NOVEL']
const CATEGORY_LABEL = { COMPOUND: 'Compound', AMBIGUOUS: 'Ambiguous', STRUCTURAL: 'Structural', NOVEL: 'Novel' }
const STATUS_FILTERS = [
  { value: 'all', label: 'All statuses' },
  { value: 'ready', label: 'Ready' },
  { value: 'waiting', label: 'Waiting' },
  { value: 'attention', label: 'Attention' },
  { value: 'blocked', label: 'Blocked' },
]

const DOT_TONE = { success: 'bg-emerald-500', warning: 'bg-amber-500', danger: 'bg-destructive', primary: 'bg-primary', neutral: 'bg-muted-foreground' }
const DOT_TEXT = {
  success: 'text-emerald-700 dark:text-emerald-400',
  warning: 'text-amber-700 dark:text-amber-400',
  danger: 'text-destructive',
  primary: 'text-primary',
  neutral: 'text-muted-foreground',
}

const ACTIVITY_CATEGORY_META = {
  ai: { label: 'AI analysis', icon: Sparkles, className: 'bg-primary/10 text-primary' },
  dart: { label: 'DART', icon: Gavel, className: 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400' },
  student: { label: 'Student action', icon: User, className: 'bg-muted text-foreground' },
  sprint: { label: 'Sprint', icon: KanbanSquare, className: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400' },
}

function reqStageState(req, userStories, estimations) {
  if (req.status !== 'Passing') return { key: 'blocked', label: 'Blocked' }
  const stories = userStories[req.id] || []
  if (stories.length === 0) return { key: 'waiting', label: 'Waiting' }
  const allAccepted = stories.every((s) => s.status === 'Accepted')
  if (!allAccepted) return { key: 'attention', label: 'Attention' }
  const allEstimated = stories.every((s) => estimations[s.id]?.confirmed)
  if (!allEstimated) return { key: 'waiting', label: 'Waiting' }
  return { key: 'ready', label: 'Ready' }
}

function targetForRequirement(r, userStories, estimations) {
  const stories = userStories[r.id] || []
  const decomposed = stories.length > 0 && stories.every((s) => s.status === 'Accepted')
  const estimated = stories.length > 0 && stories.every((s) => estimations[s.id]?.confirmed)
  if (r.status !== 'Passing') return '/planning/requirements/srs-quality'
  if (!decomposed) return '/planning/requirements/decomposition'
  if (!estimated) return '/planning/requirements/estimation'
  return '/planning/sprint-management'
}

function SectionLabel({ children }) {
  return <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground/70 mb-3">{children}</p>
}

function StatusDot({ tone = 'neutral', children }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${DOT_TEXT[tone]}`}>
      <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${DOT_TONE[tone]}`} />
      {children}
    </span>
  )
}

function KpiCard({ icon: Icon, label, to, navigate, children }) {
  return (
    <Card className="p-5">
      <button
        type="button"
        onClick={() => to && navigate(to)}
        className="w-full flex items-center justify-between mb-3 text-left cursor-pointer group"
      >
        <span className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          <Icon className="h-3.5 w-3.5" /> {label}
        </span>
        {to && (
          <ArrowRight className="h-3.5 w-3.5 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all shrink-0" />
        )}
      </button>
      {children}
    </Card>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { requirements, userStories, estimations, kanbanTasks, teamMembers, projectInfo, activityLog } = usePlanningData()

  const [today] = useState(() => Date.now())
  const [statusFilter, setStatusFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [selectedReq, setSelectedReq] = useState(null)

  const stats = computeStageStats({ requirements, userStories, estimations, kanbanTasks })
  const nextAction = getNextAction(stats)
  const pipelineStages = STAGE_ORDER.map((key) => stats[key])

  const avgScore = stats.quality.percent
  const passingCount = requirements.filter((r) => r.status === 'Passing').length
  const reviewCount = requirements.filter((r) => r.status === 'Needs Review').length
  const failingCount = requirements.filter((r) => r.status === 'Failing').length
  const totalPoints = kanbanTasks.reduce((s, t) => s + t.points, 0)
  const donePoints = kanbanTasks.filter((t) => t.status === 'Done').reduce((s, t) => s + t.points, 0)
  const blockedTaskCount = kanbanTasks.filter((t) => t.status === 'Blocked').length

  const overallPercent = Math.round(
    (stats.quality.percent + stats.decomposition.percent + stats.effort.percent + stats.sprint.percent) / 4,
  )

  const currentStage = stats.quality.percent < 100
    ? 'SRS Quality'
    : stats.decomposition.percent < 100
      ? 'Decomposition'
      : stats.effort.percent < 100
        ? 'Effort Estimation'
        : 'Sprint Management'

  const daysLeft = Math.max(0, Math.ceil((new Date(projectInfo.sprintEndDate).getTime() - today) / 86400000))

  const avgDimensionScores = QUALITY_DIMENSIONS.reduce((acc, dim) => {
    acc[dim.key] = Math.round(requirements.reduce((sum, r) => sum + r.dimensionScores[dim.key], 0) / requirements.length)
    return acc
  }, {})
  const lowestDim = QUALITY_DIMENSIONS.reduce(
    (min, dim) => (avgDimensionScores[dim.key] < avgDimensionScores[min.key] ? dim : min),
    QUALITY_DIMENSIONS[0],
  )

  const ownGroup = GROUPS.find((g) => g.id === projectInfo.groupId)
  const openFlags = ownGroup
    ? ARBITRATION_CASES.filter((c) => c.status === 'Open' && ownGroup.requirementIds.includes(c.requirementId))
    : []
  const dartTally = CATEGORY_ORDER.reduce((acc, cat) => {
    acc[cat] = openFlags.filter((c) => c.category === cat).length
    return acc
  }, {})

  const workload = teamMembers.map((m) => {
    const assigned = kanbanTasks.filter((t) => t.assigneeId === m.id && t.status !== 'Done')
    const points = assigned.reduce((s, t) => s + t.points, 0)
    const pct = Math.round((points / m.capacity) * 100)
    return { ...m, points, pct, over: points > m.capacity }
  })
  const totalCapacity = teamMembers.reduce((s, m) => s + m.capacity, 0)
  const totalAssigned = workload.reduce((s, m) => s + m.points, 0)
  const overCapacityCount = workload.filter((w) => w.over).length

  const filteredRequirements = requirements.filter((r) => {
    const q = search.trim().toLowerCase()
    if (q && !(r.id.toLowerCase().includes(q) || r.title.toLowerCase().includes(q))) return false
    if (statusFilter === 'all') return true
    return reqStageState(r, userStories, estimations).key === statusFilter
  })

  const selectedArbitration = selectedReq ? getArbitrationForRequirement(selectedReq.id) : []

  return (
    <div className="space-y-6">
      <PageHeader title="Project Planning" breadcrumb={['Planning', 'Student', 'Dashboard']} />

      {/* Project header */}
      <Card className="p-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="min-w-0">
            <div className="flex items-center gap-1.5 mb-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-500 shrink-0" />
              <span className="text-xs font-semibold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">Active project</span>
            </div>
            <h1 className="text-2xl font-bold text-foreground tracking-tight truncate">{projectInfo.name}</h1>
            <p className="text-xs text-muted-foreground mt-1">
              {projectInfo.batch} · Group {projectInfo.groupId.toUpperCase()} · Supervised by {projectInfo.supervisor}
            </p>
          </div>
          <Badge tone="primary" className="text-sm px-3 py-1 shrink-0">
            {projectInfo.sprintName} of {projectInfo.totalSprints}
          </Badge>
        </div>

        <div className="flex items-center flex-wrap gap-x-4 gap-y-2 mt-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <Users className="h-3.5 w-3.5" /> {teamMembers.length} members
          </span>
          <span className="h-1 w-1 rounded-full bg-border" />
          <span>
            Current stage: <span className="font-medium text-foreground">{currentStage}</span>
          </span>
          <span className="h-1 w-1 rounded-full bg-border" />
          <span className="flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" />
            {daysLeft === 0 ? 'Sprint ends today' : `${daysLeft} day${daysLeft === 1 ? '' : 's'} left`}
          </span>
          <div className="flex -space-x-2 ml-1">
            {teamMembers.map((m) => (
              <AvatarComp key={m.id} name={m.name} size={24} className="ring-2 ring-card" />
            ))}
          </div>
        </div>

        <div className="flex items-center gap-4 mt-5">
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between text-xs mb-1.5">
              <span className="font-medium text-muted-foreground">Project progress</span>
              <span className="font-semibold text-foreground">{overallPercent}%</span>
            </div>
            <Progress value={overallPercent} className="h-2" />
          </div>
          <Button size="sm" icon={KanbanSquare} onClick={() => navigate('/planning/sprint-management')} className="shrink-0">
            Open Sprint Board
          </Button>
        </div>
      </Card>

      {/* Key metrics */}
      <div>
        <SectionLabel>Key metrics</SectionLabel>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard icon={ClipboardList} label="Requirements" to="/planning/requirements/srs-quality" navigate={navigate}>
            <p className="text-3xl font-bold text-foreground tracking-tight">{requirements.length}</p>
            <p className="text-xs text-muted-foreground mt-0.5">Total requirements</p>
            <div className="flex items-center gap-3 mt-3 text-xs flex-wrap">
              <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                <CheckCircle2 className="h-3 w-3" /> {passingCount} passed
              </span>
              <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400 font-medium">
                <AlertTriangle className="h-3 w-3" /> {reviewCount} attention
              </span>
              <span className="flex items-center gap-1 text-destructive font-medium">
                <XCircle className="h-3 w-3" /> {failingCount} blocked
              </span>
            </div>
            <Progress value={avgScore} className="h-1.5 mt-3" />
            <p className="text-[11px] text-muted-foreground mt-1.5">{avgScore}% completed</p>
          </KpiCard>

          <KpiCard icon={ShieldCheck} label="SRS Quality" to="/planning/requirements/srs-quality" navigate={navigate}>
            <p className="text-3xl font-bold text-foreground tracking-tight">{avgScore}%</p>
            <p className="text-xs text-muted-foreground mt-0.5">Requirements passing</p>
            <Progress value={avgScore} className="h-1.5 mt-3" />
            <p className="text-xs text-muted-foreground mt-2">
              {passingCount} / {requirements.length} passed{failingCount > 0 ? ` · ${failingCount} blocked` : ''}
            </p>
          </KpiCard>

          <KpiCard icon={Gauge} label="Estimated Work" to="/planning/sprint-management" navigate={navigate}>
            <p className="text-3xl font-bold text-foreground tracking-tight">{totalPoints} SP</p>
            <p className="text-xs text-muted-foreground mt-0.5">Current sprint</p>
            <div className="flex items-center justify-between text-xs text-muted-foreground mt-3">
              <span>{donePoints} SP done</span>
              <span>{totalPoints - donePoints} SP remaining</span>
            </div>
            <Progress value={totalPoints ? Math.round((donePoints / totalPoints) * 100) : 0} className="h-1.5 mt-1.5" />
          </KpiCard>

          <KpiCard icon={Gavel} label="DART Flags" to="/planning/requirements/srs-quality" navigate={navigate}>
            <p className="text-3xl font-bold text-foreground tracking-tight">{openFlags.length}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{openFlags.length > 0 ? 'Require attention' : 'All clear'}</p>
            {openFlags.length === 0 ? (
              <p className="text-xs text-muted-foreground flex items-center gap-1.5 mt-3">
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> No unresolved conflicts
              </p>
            ) : (
              <div className="space-y-1.5 mt-3">
                {CATEGORY_ORDER.filter((cat) => dartTally[cat] > 0).map((cat) => (
                  <div key={cat} className="flex items-center justify-between text-xs">
                    <span className="text-muted-foreground">{CATEGORY_LABEL[cat]}</span>
                    <span className="font-semibold text-foreground">{dartTally[cat]}</span>
                  </div>
                ))}
              </div>
            )}
          </KpiCard>
        </div>
      </div>

      {/* Pipeline */}
      <Card className="p-6">
        <h3 className="text-base font-semibold text-foreground">Project planning pipeline</h3>
        <p className="text-xs text-muted-foreground mb-6">Where your project stands across all four stages</p>
        <div className="relative grid grid-cols-2 sm:grid-cols-4 gap-y-8 gap-x-4">
          <div className="hidden sm:block absolute top-[22px] left-[12.5%] right-[12.5%] h-px bg-border" />
          {pipelineStages.map((stage) => {
            const isSprint = stage.key === 'sprint'
            const tone = isSprint ? 'primary' : stage.complete ? 'success' : (stage.blocked || stage.percent === 0) ? 'neutral' : 'warning'
            return (
              <Link key={stage.key} to={stage.to} className="relative flex flex-col items-center text-center group">
                <span
                  className={`relative z-10 h-11 w-11 rounded-full flex items-center justify-center border-2 bg-card transition-colors ${
                    tone === 'success'
                      ? 'border-emerald-500'
                      : tone === 'warning'
                        ? 'border-amber-500'
                        : tone === 'primary'
                          ? 'border-primary'
                          : 'border-border'
                  }`}
                >
                  {tone === 'success' ? (
                    <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                  ) : tone === 'warning' ? (
                    <AlertTriangle className="h-5 w-5 text-amber-500" />
                  ) : isSprint ? (
                    <span className="h-2.5 w-2.5 rounded-full bg-primary" />
                  ) : (
                    <span className="text-muted-foreground text-xs font-semibold">—</span>
                  )}
                </span>
                <p className="text-sm font-semibold text-foreground mt-3 group-hover:text-primary transition-colors">{stage.label}</p>
                <p className="text-lg font-bold text-foreground leading-tight">{stage.percent}%</p>
                <p className="text-xs text-muted-foreground mt-0.5 max-w-[150px]">{stage.caption}</p>
              </Link>
            )
          })}
        </div>
      </Card>

      {/* Attention & insights */}
      <div>
        <SectionLabel>Attention &amp; insights</SectionLabel>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="p-6 flex flex-col">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-4">Attention required</h3>
            <div className="space-y-3 flex-1">
              {reviewCount > 0 && (
                <div className="flex items-start gap-2.5 text-sm">
                  <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                  <span className="text-foreground">{reviewCount} requirement{reviewCount === 1 ? '' : 's'} need review</span>
                </div>
              )}
              {failingCount > 0 && (
                <div className="flex items-start gap-2.5 text-sm">
                  <XCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
                  <span className="text-foreground">{failingCount} requirement{failingCount === 1 ? '' : 's'} blocked</span>
                </div>
              )}
              {blockedTaskCount > 0 && (
                <div className="flex items-start gap-2.5 text-sm">
                  <XCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
                  <span className="text-foreground">{blockedTaskCount} sprint task{blockedTaskCount === 1 ? '' : 's'} blocked</span>
                </div>
              )}
              {overCapacityCount > 0 && (
                <div className="flex items-start gap-2.5 text-sm">
                  <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
                  <span className="text-foreground">{overCapacityCount} member{overCapacityCount === 1 ? '' : 's'} over sprint capacity</span>
                </div>
              )}
              {reviewCount === 0 && failingCount === 0 && blockedTaskCount === 0 && overCapacityCount === 0 && (
                <div className="flex items-start gap-2.5 text-sm">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500 mt-0.5 shrink-0" />
                  <span className="text-foreground">Nothing needs attention right now.</span>
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={() => navigate(nextAction.to)}
              className="mt-4 inline-flex items-center gap-1.5 self-start px-3 py-2 rounded-lg bg-primary/10 text-primary text-xs font-semibold hover:bg-primary/15 transition-colors cursor-pointer"
            >
              {nextAction.text} <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </Card>

          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">DART arbitration</h3>
              <Badge tone={openFlags.length > 0 ? 'danger' : 'success'}>{openFlags.length} open</Badge>
            </div>
            {openFlags.length === 0 ? (
              <p className="text-sm text-foreground flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-500" /> No unresolved conflicts right now.
              </p>
            ) : (
              <div className="space-y-3">
                {openFlags.slice(0, 2).map((c) => (
                  <div key={c.id} className="pb-3 border-b border-border last:border-0 last:pb-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge tone={ARBITRATION_CATEGORY_TONE[c.category]}>{c.category}</Badge>
                      <span className="text-xs text-muted-foreground">{c.requirementId}</span>
                    </div>
                    <p className="text-xs text-foreground leading-snug mb-1.5">{c.title}</p>
                    <button
                      type="button"
                      onClick={() => navigate('/planning/requirements/srs-quality')}
                      className="text-xs font-medium text-primary hover:underline inline-flex items-center gap-1 cursor-pointer"
                    >
                      Review <ArrowRight className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
            <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 mt-4 pt-4 border-t border-border">
              {CATEGORY_ORDER.map((cat) => (
                <div key={cat} className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">{CATEGORY_LABEL[cat]}</span>
                  <span className="font-semibold text-foreground">{dartTally[cat] || 0}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* Requirement analytics */}
      <div>
        <SectionLabel>Requirement analytics</SectionLabel>
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          <Card className="p-6 lg:col-span-2">
            <h3 className="text-base font-semibold text-foreground mb-0.5">Quality profile</h3>
            <p className="text-xs text-muted-foreground mb-4">Averaged across {requirements.length} tracked requirements</p>
            <QualityRadarChart scores={avgDimensionScores} height={200} />
            <div className="space-y-2.5 mt-4">
              {QUALITY_DIMENSIONS.map((dim) => {
                const score = avgDimensionScores[dim.key]
                return (
                  <div key={dim.key}>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-muted-foreground">{dim.label}</span>
                      <span className="font-semibold text-foreground">{score}%</span>
                    </div>
                    <Progress
                      value={score}
                      className={`h-1 ${score < 60 ? '[&>div]:bg-destructive' : score < 75 ? '[&>div]:bg-amber-500' : '[&>div]:bg-emerald-500'}`}
                    />
                  </div>
                )
              })}
            </div>
            <div className="flex items-center justify-between mt-4 pt-4 border-t border-border">
              <div>
                <p className="text-[11px] text-muted-foreground">Lowest dimension</p>
                <p className="text-sm font-semibold text-destructive">{lowestDim.label} · {avgDimensionScores[lowestDim.key]}%</p>
              </div>
              <button
                type="button"
                onClick={() => navigate('/planning/requirements/srs-quality')}
                className="text-xs font-medium text-primary hover:underline inline-flex items-center gap-1 cursor-pointer shrink-0"
              >
                Review weak areas <ArrowRight className="h-3 w-3" />
              </button>
            </div>
          </Card>

          <Card className="p-0 overflow-hidden lg:col-span-3">
            <div className="p-5 pb-3 flex items-center justify-between gap-3 flex-wrap">
              <div>
                <h3 className="text-base font-semibold text-foreground">Requirement health</h3>
                <p className="text-xs text-muted-foreground">{filteredRequirements.length} of {requirements.length} requirements · click a row for details</p>
              </div>
              <div className="flex items-center gap-2">
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger className="w-[130px] h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {STATUS_FILTERS.map((f) => (
                      <SelectItem key={f.value} value={f.value}>{f.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <div className="relative">
                  <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                  <Input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search..."
                    className="pl-8 h-8 text-xs w-[140px]"
                  />
                </div>
              </div>
            </div>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Requirement</TableHead>
                  <TableHead className="w-[80px]">Priority</TableHead>
                  <TableHead className="w-[90px]">Quality</TableHead>
                  <TableHead className="w-[70px] text-center">Decomp.</TableHead>
                  <TableHead className="w-[70px] text-center">Effort</TableHead>
                  <TableHead className="w-[90px]">Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRequirements.map((r) => {
                  const state = reqStageState(r, userStories, estimations)
                  const stories = userStories[r.id] || []
                  const decomposed = stories.length > 0 && stories.every((s) => s.status === 'Accepted')
                  const estimated = stories.length > 0 && stories.every((s) => estimations[s.id]?.confirmed)
                  return (
                    <TableRow key={r.id} className="cursor-pointer" onClick={() => setSelectedReq(r)}>
                      <TableCell className="max-w-[200px]">
                        <p className="text-xs font-medium text-muted-foreground">{r.id}</p>
                        <p className="text-sm text-foreground truncate">{r.title}</p>
                      </TableCell>
                      <TableCell>
                        <StatusDot tone={PRIORITY_TONE[r.priority]}>{r.priority}</StatusDot>
                      </TableCell>
                      <TableCell>
                        <StatusDot tone={GATE_STATUS_TONE[r.status]}>{GATE_STATUS_LABEL[r.status]}</StatusDot>
                      </TableCell>
                      <TableCell className="text-center">
                        {r.status !== 'Passing' ? (
                          <span className="text-muted-foreground/40 text-sm">—</span>
                        ) : decomposed ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-500 mx-auto" />
                        ) : stories.length > 0 ? (
                          <AlertTriangle className="h-4 w-4 text-amber-500 mx-auto" />
                        ) : (
                          <span className="text-muted-foreground/40 text-sm">—</span>
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        {estimated ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-500 mx-auto" />
                        ) : (
                          <span className="text-muted-foreground/40 text-sm">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <StatusDot tone={ROW_STATUS_TONE[state.key]}>{state.label}</StatusDot>
                      </TableCell>
                    </TableRow>
                  )
                })}
                {filteredRequirements.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center text-xs text-muted-foreground py-8">
                      No requirements match this filter.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </div>
      </div>

      {/* Team & activity */}
      <div>
        <SectionLabel>Team &amp; activity</SectionLabel>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="p-6">
            <h3 className="text-base font-semibold text-foreground">Team &amp; sprint workload</h3>
            <p className="text-xs text-muted-foreground mb-4">{totalAssigned} / {totalCapacity} SP assigned this sprint</p>
            <div className="divide-y divide-border">
              {workload.map((m) => (
                <div key={m.id} className="py-3 first:pt-0 last:pb-0">
                  <div className="flex items-center gap-3">
                    <AvatarComp name={m.name} size={36} />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between gap-2">
                        <p className="text-sm font-medium text-foreground truncate">{m.name}</p>
                        <span className={`text-xs font-semibold shrink-0 ${m.over ? 'text-destructive' : 'text-muted-foreground'}`}>
                          {m.points} / {m.capacity} SP
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground truncate">{m.role}</p>
                    </div>
                  </div>
                  <div className="mt-2 flex items-center gap-2">
                    <Progress
                      value={Math.min(100, m.pct)}
                      className={`h-1.5 flex-1 ${m.over ? '[&>div]:bg-destructive' : m.pct >= 80 ? '[&>div]:bg-amber-500' : ''}`}
                    />
                    <span className={`text-[11px] font-medium shrink-0 ${m.over ? 'text-destructive' : 'text-muted-foreground'}`}>
                      {m.pct}% capacity{m.over ? ' ⚠' : ''}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <Card className="p-6">
            <h3 className="text-base font-semibold text-foreground mb-4">Recent activity</h3>
            <div className="space-y-4">
              {activityLog.slice(0, 6).map((a) => {
                const meta = ACTIVITY_CATEGORY_META[a.category] || ACTIVITY_CATEGORY_META.ai
                const Icon = meta.icon
                return (
                  <div key={a.id} className="flex items-start gap-3">
                    <span className={`h-7 w-7 rounded-full flex items-center justify-center shrink-0 ${meta.className}`}>
                      <Icon className="h-3.5 w-3.5" />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-0.5">{meta.label}</p>
                      <p className="text-xs text-foreground leading-snug">{a.text}</p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">{formatRelativeTime(a.timestamp)}</p>
                    </div>
                  </div>
                )
              })}
              {activityLog.length === 0 && (
                <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5" /> No activity yet — start with SRS Quality.
                </p>
              )}
            </div>
          </Card>
        </div>
      </div>

      {/* Requirement detail drawer */}
      <Sheet open={Boolean(selectedReq)} onOpenChange={(open) => !open && setSelectedReq(null)}>
        <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto column-scroll-contain">
          {selectedReq && (
            <>
              <SheetHeader>
                <div className="flex items-center gap-2 flex-wrap">
                  <SheetTitle>{selectedReq.id}</SheetTitle>
                  <Badge tone={PRIORITY_TONE[selectedReq.priority]}>{selectedReq.priority}</Badge>
                  <Badge tone={GATE_STATUS_TONE[selectedReq.status]}>{selectedReq.status}</Badge>
                </div>
                <SheetDescription>{selectedReq.title}</SheetDescription>
              </SheetHeader>

              <div className="px-4 pb-4 space-y-5">
                <p className="text-sm text-foreground leading-relaxed">{selectedReq.description}</p>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Quality dimensions</p>
                  <div className="space-y-2">
                    {QUALITY_DIMENSIONS.map((dim) => {
                      const score = selectedReq.dimensionScores[dim.key]
                      const tone = score >= 75 ? 'success' : score >= 50 ? 'warning' : 'danger'
                      return (
                        <div key={dim.key} className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground">{dim.label}</span>
                          <StatusDot tone={tone}>{score}%</StatusDot>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {selectedArbitration.length > 0 && (
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">DART</p>
                    <div className="space-y-2">
                      {selectedArbitration.map((c) => (
                        <div key={c.id} className="flex items-start gap-2 text-sm">
                          <Badge tone={ARBITRATION_CATEGORY_TONE[c.category]} className="shrink-0">{c.category}</Badge>
                          <span className="text-foreground leading-snug">{c.title}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <Button
                  className="w-full"
                  onClick={() => {
                    const target = targetForRequirement(selectedReq, userStories, estimations)
                    setSelectedReq(null)
                    navigate(target)
                  }}
                >
                  Review requirement
                </Button>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      <DartButton context="dashboard" />
    </div>
  )
}
