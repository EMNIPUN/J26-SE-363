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
  GraduationCap,
  Calendar,
  PlusCircle,
  Download,
  UserCheck,
  Layers,
  Activity,
} from 'lucide-react'
import Card from '../../../../shared/components/Card.jsx'
import Badge from '../../../../shared/components/Badge.jsx'
import Button from '../../../../shared/components/Button.jsx'
import AvatarComp from '../../../../shared/components/Avatar.jsx'
import { Progress } from '@/components/ui/progress'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
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
import AcademicMilestonesTimeline from '../../components/AcademicMilestonesTimeline.jsx'
import AssessmentRubricCard from '../../components/AssessmentRubricCard.jsx'
import SupervisorNoticeBoard from '../../components/SupervisorNoticeBoard.jsx'
import SupervisorConsultationModal from '../../components/SupervisorConsultationModal.jsx'
import ExportPlanningReportModal from '../../components/ExportPlanningReportModal.jsx'
import NewRequirementModal from '../../components/NewRequirementModal.jsx'
import { usePlanningData } from '../../context/usePlanningData.js'
import { QUALITY_DIMENSIONS, ARBITRATION_CASES, GROUPS, getArbitrationForRequirement } from '../../data/mockData.js'
import { COURSE_INFO, STUDENT_ACADEMIC_PROFILES } from '../../data/lmsAcademicData.js'
import { computeStageStats, getNextAction, STAGE_ORDER } from '../../stageStats.js'
import { ARBITRATION_CATEGORY_TONE, GATE_STATUS_TONE, formatRelativeTime } from '../../utils.js'

const PRIORITY_TONE = { High: 'danger', Medium: 'warning', Low: 'neutral' }
const GATE_STATUS_LABEL = { Passing: 'Passed', 'Needs Review': 'Review', Failing: 'Blocked' }
const ROW_STATUS_TONE = { ready: 'success', waiting: 'primary', attention: 'warning', blocked: 'danger' }
const CATEGORY_ORDER = ['COMPOUND', 'AMBIGUOUS', 'STRUCTURAL', 'NOVEL']
const STATUS_FILTERS = [
  { value: 'all', label: 'All statuses' },
  { value: 'ready', label: 'Ready for Sprint' },
  { value: 'waiting', label: 'Waiting on Pipeline' },
  { value: 'attention', label: 'Requires Attention' },
  { value: 'blocked', label: 'Blocked' },
]

const DOT_TONE = {
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  danger: 'bg-destructive',
  primary: 'bg-primary',
  neutral: 'bg-muted-foreground',
}
const DOT_TEXT = {
  success: 'text-emerald-700 dark:text-emerald-400',
  warning: 'text-amber-700 dark:text-amber-400',
  danger: 'text-destructive',
  primary: 'text-primary',
  neutral: 'text-muted-foreground',
}

const ACTIVITY_CATEGORY_META = {
  ai: { label: 'AI Agent Analysis', icon: Sparkles, className: 'bg-primary/10 text-primary' },
  dart: { label: 'DART Arbitration', icon: Gavel, className: 'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400' },
  student: { label: 'Student Change', icon: User, className: 'bg-muted text-foreground' },
  sprint: { label: 'Agile Sprint Action', icon: KanbanSquare, className: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400' },
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

function StatusDot({ tone = 'neutral', children }) {
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${DOT_TEXT[tone]}`}>
      <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${DOT_TONE[tone]}`} />
      {children}
    </span>
  )
}

function KpiCard({ icon: Icon, label, value, subtext, to, navigate, badge, children }) {
  return (
    <Card className="p-4 sm:p-5 card-hover-lift flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            <Icon className="h-3.5 w-3.5 text-primary" /> {label}
          </span>
          {badge}
        </div>
        <div className="flex items-baseline justify-between">
          <p className="text-2xl sm:text-3xl font-bold text-foreground tracking-tight">{value}</p>
          {to && (
            <button
              type="button"
              onClick={() => navigate(to)}
              className="text-xs text-primary hover:underline inline-flex items-center gap-0.5 cursor-pointer font-medium"
            >
              Details <ArrowRight className="h-3 w-3" />
            </button>
          )}
        </div>
        {subtext && <p className="text-xs text-muted-foreground mt-0.5">{subtext}</p>}
      </div>
      {children}
    </Card>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { requirements, userStories, estimations, kanbanTasks, teamMembers, projectInfo, activityLog } =
    usePlanningData()

  const [today] = useState(() => Date.now())
  const [activeTab, setActiveTab] = useState('overview')
  const [statusFilter, setStatusFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [selectedReq, setSelectedReq] = useState(null)
  const [activityCategoryFilter, setActivityCategoryFilter] = useState('all')

  // Modals state
  const [consultModalOpen, setConsultModalOpen] = useState(false)
  const [exportModalOpen, setExportModalOpen] = useState(false)
  const [newReqModalOpen, setNewReqModalOpen] = useState(false)

  const stats = computeStageStats({ requirements, userStories, estimations, kanbanTasks })
  const nextAction = getNextAction(stats)
  const pipelineStages = STAGE_ORDER.map((key) => stats[key])

  const avgScore = stats.quality.percent
  const passingCount = requirements.filter((r) => r.status === 'Passing').length
  const reviewCount = requirements.filter((r) => r.status === 'Needs Review').length
  const failingCount = requirements.filter((r) => r.status === 'Failing').length
  const totalPoints = kanbanTasks.reduce((s, t) => s + (t.points || 0), 0)
  const donePoints = kanbanTasks.filter((t) => t.status === 'Done').reduce((s, t) => s + (t.points || 0), 0)
  const blockedTaskCount = kanbanTasks.filter((t) => t.status === 'Blocked').length

  const overallPercent = Math.round(
    (stats.quality.percent + stats.decomposition.percent + stats.effort.percent + stats.sprint.percent) / 4,
  )

  const daysLeft = Math.max(0, Math.ceil((new Date(projectInfo.sprintEndDate).getTime() - today) / 86400000))

  const avgDimensionScores = QUALITY_DIMENSIONS.reduce((acc, dim) => {
    acc[dim.key] = Math.round(
      requirements.reduce((sum, r) => sum + (r.dimensionScores?.[dim.key] ?? 0), 0) / (requirements.length || 1),
    )
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
    const points = assigned.reduce((s, t) => s + (t.points || 0), 0)
    const pct = Math.round((points / (m.capacity || 1)) * 100)
    const academicProfile = STUDENT_ACADEMIC_PROFILES[m.id] || null
    return { ...m, points, pct, over: points > m.capacity, academicProfile }
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

  const filteredActivityLog = activityLog.filter((a) => {
    if (activityCategoryFilter === 'all') return true
    return a.category === activityCategoryFilter
  })

  const selectedArbitration = selectedReq ? getArbitrationForRequirement(selectedReq.id) : []

  return (
    <div className="space-y-6 pb-12">
      {/* Top Academic LMS Breadcrumb Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-border">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <GraduationCap className="h-3.5 w-3.5 text-primary" />
            <span>{COURSE_INFO.courseCode} · {COURSE_INFO.courseName}</span>
            <span className="text-border">/</span>
            <span className="text-foreground">{COURSE_INFO.academicYear}</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            Project Planning &amp; Engineering Gateway
            <Badge tone="success" className="text-xs font-medium">Active Capstone</Badge>
          </h1>
        </div>

        {/* Action Toolbar */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            size="sm"
            variant="outline"
            className="text-xs cursor-pointer gap-1.5"
            onClick={() => setExportModalOpen(true)}
          >
            <Download className="h-3.5 w-3.5 text-primary" /> Export Dossier
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="text-xs cursor-pointer gap-1.5"
            onClick={() => setConsultModalOpen(true)}
          >
            <UserCheck className="h-3.5 w-3.5 text-primary" /> Supervisor Advisory
          </Button>
          <Button
            size="sm"
            className="text-xs cursor-pointer gap-1.5"
            onClick={() => setNewReqModalOpen(true)}
          >
            <PlusCircle className="h-3.5 w-3.5" /> + New Requirement
          </Button>
        </div>
      </div>

      {/* LMS Project Banner Card */}
      <Card className="p-5 relative overflow-hidden bg-card/90">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-5">
          <div className="space-y-2 min-w-0 max-w-2xl">
            <div className="flex items-center gap-2 flex-wrap text-xs text-muted-foreground">
              <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary font-bold">
                {COURSE_INFO.group.number} ({COURSE_INFO.group.code})
              </span>
              <span>·</span>
              <span className="font-semibold text-foreground">{COURSE_INFO.department}</span>
              <span>·</span>
              <span>Specialization: <strong className="text-foreground">{COURSE_INFO.group.specialization}</strong></span>
            </div>

            <h2 className="text-lg sm:text-xl font-semibold text-foreground tracking-tight">
              {projectInfo.name}
            </h2>

            <p className="text-xs text-muted-foreground leading-relaxed">
              Intelligent multi-agent requirements engineering and iterative sprint execution platform. Scored according to IEEE 830 standards and INVEST backlog criteria.
            </p>

            <div className="flex items-center gap-4 flex-wrap pt-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5 font-medium text-foreground">
                <AvatarComp name={COURSE_INFO.supervisor.name} size={22} className="ring-1 ring-border" />
                Supervisor: {COURSE_INFO.supervisor.name}
              </span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span className="flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-primary" />
                {daysLeft === 0 ? 'Sprint closes today' : `${daysLeft} days to Sprint freeze`}
              </span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span className="flex items-center gap-1.5">
                <Users className="h-3.5 w-3.5 text-primary" />
                {teamMembers.length} Research Engineers
              </span>
            </div>
          </div>

          {/* Round Progress Bar with Percentage in Middle */}
          <div className="flex flex-col items-center justify-center shrink-0 self-center sm:self-center px-3 py-1">
            <div className="relative flex items-center justify-center" style={{ width: 92, height: 92 }}>
              <svg className="w-full h-full -rotate-90 transform" viewBox="0 0 92 92">
                {/* Background track */}
                <circle
                  cx="46"
                  cy="46"
                  r="38"
                  className="stroke-muted"
                  strokeWidth="7"
                  fill="transparent"
                />
                {/* Progress ring */}
                <circle
                  cx="46"
                  cy="46"
                  r="38"
                  className="stroke-primary transition-all duration-700 ease-out"
                  strokeWidth="7"
                  strokeDasharray={2 * Math.PI * 38}
                  strokeDashoffset={(2 * Math.PI * 38) * (1 - overallPercent / 100)}
                  strokeLinecap="round"
                  fill="transparent"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-xl font-bold tracking-tight text-foreground">{overallPercent}%</span>
              </div>
            </div>
            <span className="text-xs font-semibold text-muted-foreground mt-1.5">Project Progress</span>
          </div>
        </div>
      </Card>

      {/* 4-Stage Intelligent Planning Stepper */}
      <Card className="p-4 sm:p-5">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              Intelligent Planning Pipeline
            </h3>
            <p className="text-xs text-muted-foreground">Four-phase curriculum workflow for IEEE-compliant agile delivery</p>
          </div>
          <button
            type="button"
            onClick={() => navigate(nextAction.to)}
            className="text-xs font-semibold text-primary hover:underline inline-flex items-center gap-1 cursor-pointer"
          >
            {nextAction.text} <ArrowRight className="h-3 w-3" />
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
          {pipelineStages.map((stage, idx) => {
            return (
              <Link
                key={stage.key}
                to={stage.to}
                className="p-3 rounded-xl border border-border/70 hover:border-primary/50 hover:bg-muted/30 transition-all group flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span
                      className={`h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold ${
                        stage.complete
                          ? 'bg-emerald-500 text-white'
                          : stage.percent > 0
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-muted text-muted-foreground'
                      }`}
                    >
                      {stage.complete ? <CheckCircle2 className="h-4 w-4" /> : idx + 1}
                    </span>
                    <span className="text-sm font-bold text-foreground">{stage.percent}%</span>
                  </div>

                  <p className="text-xs font-bold text-foreground group-hover:text-primary transition-colors">
                    {stage.label}
                  </p>
                  <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-1">{stage.caption}</p>
                </div>

                <div className="mt-3">
                  <Progress
                    value={stage.percent}
                    className={`h-1 ${
                      stage.complete
                        ? '[&>div]:bg-emerald-500'
                        : stage.percent > 0
                          ? '[&>div]:bg-primary'
                          : '[&>div]:bg-muted-foreground/30'
                    }`}
                  />
                </div>
              </Link>
            )
          })}
        </div>
      </Card>

      {/* Main Tabbed LMS Dashboard Interface */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <div className="flex items-center justify-between border-b border-border pb-1 overflow-x-auto">
          <TabsList className="h-10 bg-muted/60 p-1">
            <TabsTrigger value="overview" className="text-xs gap-1.5">
              <Layers className="h-3.5 w-3.5" /> Academic Overview
            </TabsTrigger>
            <TabsTrigger value="requirements" className="text-xs gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5" /> SRS Quality Matrix
              <span className="ml-1 px-1.5 py-0.2 rounded-full bg-primary/10 text-primary text-[10px] font-bold">
                {requirements.length}
              </span>
            </TabsTrigger>
            <TabsTrigger value="milestones" className="text-xs gap-1.5">
              <Calendar className="h-3.5 w-3.5" /> Milestones &amp; Rubric
            </TabsTrigger>
            <TabsTrigger value="workload" className="text-xs gap-1.5">
              <Users className="h-3.5 w-3.5" /> Team Workload
              {overCapacityCount > 0 && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full bg-destructive/15 text-destructive text-[10px] font-bold">
                  !
                </span>
              )}
            </TabsTrigger>
            <TabsTrigger value="diagnostics" className="text-xs gap-1.5">
              <Gavel className="h-3.5 w-3.5" /> DART &amp; Audit Log
              {openFlags.length > 0 && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full bg-amber-500/20 text-amber-700 dark:text-amber-400 text-[10px] font-bold">
                  {openFlags.length}
                </span>
              )}
            </TabsTrigger>
          </TabsList>

          <span className="hidden md:inline-block text-xs text-muted-foreground pr-2">
            Academic Term: <strong>2026/Y4.S1</strong>
          </span>
        </div>

        {/* ----------------- TAB 1: ACADEMIC OVERVIEW ----------------- */}
        <TabsContent value="overview" className="space-y-6">
          {/* Milestone timeline summary */}
          <AcademicMilestonesTimeline onMilestoneSelect={() => setActiveTab('milestones')} />

          {/* Key LMS Metrics Grid */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Key Performance Metrics
              </h3>
              <span className="text-xs text-muted-foreground">Live synchronization with project store</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <KpiCard
                icon={ClipboardList}
                label="Tracked Requirements"
                value={`${requirements.length}`}
                subtext="IEEE 830 functional & non-functional"
                to="/planning/requirements/srs-quality"
                navigate={navigate}
                badge={<Badge tone="primary">{passingCount} Passing</Badge>}
              >
                <div className="mt-3 space-y-1.5">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                      <CheckCircle2 className="h-3 w-3" /> {passingCount} passed
                    </span>
                    <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400 font-medium">
                      <AlertTriangle className="h-3 w-3" /> {reviewCount} review
                    </span>
                    <span className="flex items-center gap-1 text-destructive font-medium">
                      <XCircle className="h-3 w-3" /> {failingCount} blocked
                    </span>
                  </div>
                  <Progress value={Math.round((passingCount / (requirements.length || 1)) * 100)} className="h-1.5" />
                </div>
              </KpiCard>

              <KpiCard
                icon={ShieldCheck}
                label="SRS Quality Gate"
                value={`${avgScore}%`}
                subtext={`Gate Threshold: >= 70%`}
                to="/planning/requirements/srs-quality"
                navigate={navigate}
                badge={
                  <Badge tone={avgScore >= 70 ? 'success' : 'danger'}>
                    {avgScore >= 70 ? 'Quality Passed' : 'Below Gate'}
                  </Badge>
                }
              >
                <div className="mt-3 space-y-1">
                  <Progress
                    value={avgScore}
                    className={`h-1.5 ${avgScore >= 70 ? '[&>div]:bg-emerald-500' : '[&>div]:bg-destructive'}`}
                  />
                  <p className="text-[11px] text-muted-foreground">
                    Lowest dimension: <strong className="text-destructive">{lowestDim.label} ({avgDimensionScores[lowestDim.key]}%)</strong>
                  </p>
                </div>
              </KpiCard>

              <KpiCard
                icon={Gauge}
                label="Sprint 5 Capacity"
                value={`${totalPoints} SP`}
                subtext={`${donePoints} SP completed of ${totalPoints} SP`}
                to="/planning/sprint-management"
                navigate={navigate}
                badge={<Badge tone="primary">{Math.round(totalPoints ? (donePoints / totalPoints) * 100 : 0)}% Burndown</Badge>}
              >
                <div className="mt-3 space-y-1">
                  <Progress
                    value={totalPoints ? Math.round((donePoints / totalPoints) * 100) : 0}
                    className="h-1.5 [&>div]:bg-primary"
                  />
                  <p className="text-[11px] text-muted-foreground flex justify-between">
                    <span>Active tasks: {kanbanTasks.length}</span>
                    <span>Blocked: <strong className={blockedTaskCount > 0 ? 'text-destructive' : ''}>{blockedTaskCount}</strong></span>
                  </p>
                </div>
              </KpiCard>

              <KpiCard
                icon={Gavel}
                label="DART Arbitration"
                value={`${openFlags.length}`}
                subtext={openFlags.length > 0 ? 'Diagnostic flags unresolved' : 'All agents in consensus'}
                to="/planning/requirements/srs-quality"
                navigate={navigate}
                badge={
                  <Badge tone={openFlags.length > 0 ? 'warning' : 'success'}>
                    {openFlags.length > 0 ? 'Review Needed' : 'Consensus Clean'}
                  </Badge>
                }
              >
                <div className="mt-2 space-y-1 text-xs">
                  {openFlags.length === 0 ? (
                    <p className="text-xs text-muted-foreground flex items-center gap-1 pt-1">
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> Zero semantic conflicts
                    </p>
                  ) : (
                    <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                      <span>Compound: {dartTally.COMPOUND || 0}</span>
                      <span>Ambiguous: {dartTally.AMBIGUOUS || 0}</span>
                      <span>Novel: {dartTally.NOVEL || 0}</span>
                    </div>
                  )}
                </div>
              </KpiCard>
            </div>
          </div>

          {/* Attention Required & Supervisor Noticeboard */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* Attention Required Card */}
            <Card className="p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-3 mb-3 border-b border-border">
                  <div className="flex items-center gap-2">
                    <span className="p-1 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400">
                      <AlertTriangle className="h-4 w-4" />
                    </span>
                    <h3 className="text-base font-semibold text-foreground">Action Center &amp; Blockers</h3>
                  </div>
                  <Badge tone="warning">Critical Path</Badge>
                </div>

                <div className="space-y-2.5">
                  {reviewCount > 0 && (
                    <div className="flex items-start gap-2.5 text-xs p-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
                      <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
                      <div>
                        <span className="font-semibold text-foreground">{reviewCount} requirement{reviewCount === 1 ? '' : 's'} require quality review</span>
                        <p className="text-muted-foreground text-[11px] mt-0.5">
                          Score is between 50% and 69%. Apply agent suggested rewrites to unlock decomposition.
                        </p>
                      </div>
                    </div>
                  )}

                  {failingCount > 0 && (
                    <div className="flex items-start gap-2.5 text-xs p-2 rounded-lg bg-destructive/10 border border-destructive/20">
                      <XCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
                      <div>
                        <span className="font-semibold text-foreground">{failingCount} requirement{failingCount === 1 ? '' : 's'} failing quality gate</span>
                        <p className="text-muted-foreground text-[11px] mt-0.5">
                          Infeasible or unmeasurable specification. Must be rewritten or rescored.
                        </p>
                      </div>
                    </div>
                  )}

                  {blockedTaskCount > 0 && (
                    <div className="flex items-start gap-2.5 text-xs p-2 rounded-lg bg-destructive/10 border border-destructive/20">
                      <XCircle className="h-4 w-4 text-destructive mt-0.5 shrink-0" />
                      <div>
                        <span className="font-semibold text-foreground">{blockedTaskCount} sprint task{blockedTaskCount === 1 ? '' : 's'} blocked</span>
                        <p className="text-muted-foreground text-[11px] mt-0.5">
                          Dependencies unresolved on the Kanban board.
                        </p>
                      </div>
                    </div>
                  )}

                  {overCapacityCount > 0 && (
                    <div className="flex items-start gap-2.5 text-xs p-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
                      <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 mt-0.5 shrink-0" />
                      <div>
                        <span className="font-semibold text-foreground">{overCapacityCount} student engineer over capacity limit</span>
                        <p className="text-muted-foreground text-[11px] mt-0.5">
                          Rebalance backlog points to prevent sprint burn-out and rubric penalty.
                        </p>
                      </div>
                    </div>
                  )}

                  {reviewCount === 0 && failingCount === 0 && blockedTaskCount === 0 && overCapacityCount === 0 && (
                    <div className="flex items-center gap-2.5 text-xs p-3 rounded-lg bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">
                      <CheckCircle2 className="h-4 w-4 shrink-0" />
                      <span>All quality gates and sprint workloads are completely clean!</span>
                    </div>
                  )}
                </div>
              </div>

              <div className="pt-4 mt-4 border-t border-border flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Next Recommended Step:</span>
                <Button
                  size="sm"
                  onClick={() => navigate(nextAction.to)}
                  className="text-xs gap-1.5 cursor-pointer"
                >
                  {nextAction.text} <ArrowRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            </Card>

            {/* Supervisor Guidance & Noticeboard */}
            <SupervisorNoticeBoard onConsultClick={() => setConsultModalOpen(true)} />
          </div>
        </TabsContent>

        {/* ----------------- TAB 2: SRS QUALITY MATRIX ----------------- */}
        <TabsContent value="requirements" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
            {/* 6-Dimension Radar Chart Card */}
            <Card className="p-5 lg:col-span-2 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-base font-bold text-foreground">IEEE 830 Quality Profile</h3>
                  <Badge tone={avgScore >= 70 ? 'success' : 'warning'}>
                    Avg: {avgScore}%
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mb-3">
                  Scored across all {requirements.length} functional requirements using multi-agent reasoning.
                </p>

                <QualityRadarChart scores={avgDimensionScores} height={210} />

                <div className="space-y-2 mt-3">
                  {QUALITY_DIMENSIONS.map((dim) => {
                    const score = avgDimensionScores[dim.key] ?? 0
                    return (
                      <div key={dim.key}>
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="text-muted-foreground">{dim.label}</span>
                          <span className="font-semibold text-foreground">{score}%</span>
                        </div>
                        <Progress
                          value={score}
                          className={`h-1 ${
                            score < 60 ? '[&>div]:bg-destructive' : score < 75 ? '[&>div]:bg-amber-500' : '[&>div]:bg-emerald-500'
                          }`}
                        />
                      </div>
                    )
                  })}
                </div>
              </div>

              <div className="pt-3 mt-3 border-t border-border flex items-center justify-between text-xs">
                <div>
                  <span className="text-[11px] text-muted-foreground block">Weakest Dimension</span>
                  <span className="font-bold text-destructive">{lowestDim.label} · {avgDimensionScores[lowestDim.key]}%</span>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => navigate('/planning/requirements/srs-quality')}
                  className="text-xs cursor-pointer gap-1"
                >
                  Quality Gate <ArrowRight className="h-3 w-3" />
                </Button>
              </div>
            </Card>

            {/* Requirements Matrix Table */}
            <Card className="p-0 overflow-hidden lg:col-span-3 flex flex-col justify-between">
              <div>
                <div className="p-4 pb-3 flex items-center justify-between gap-3 flex-wrap border-b border-border">
                  <div>
                    <h3 className="text-base font-bold text-foreground">Requirement Health &amp; Traceability</h3>
                    <p className="text-xs text-muted-foreground">
                      {filteredRequirements.length} of {requirements.length} specifications displayed · Click a row for detail drawer
                    </p>
                  </div>

                  <div className="flex items-center gap-2 flex-wrap">
                    <Select value={statusFilter} onValueChange={setStatusFilter}>
                      <SelectTrigger className="w-[140px] h-8 text-xs">
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
                        placeholder="Search REQ or title..."
                        className="pl-8 h-8 text-xs w-[160px]"
                      />
                    </div>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader className="bg-muted/30">
                      <TableRow>
                        <TableHead>Requirement</TableHead>
                        <TableHead className="w-[85px]">Priority</TableHead>
                        <TableHead className="w-[85px]">Quality</TableHead>
                        <TableHead className="w-[70px] text-center">Decomp.</TableHead>
                        <TableHead className="w-[70px] text-center">Effort</TableHead>
                        <TableHead className="w-[95px] text-right">Sprint Status</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {filteredRequirements.map((r) => {
                        const state = reqStageState(r, userStories, estimations)
                        const stories = userStories[r.id] || []
                        const decomposed = stories.length > 0 && stories.every((s) => s.status === 'Accepted')
                        const estimated = stories.length > 0 && stories.every((s) => estimations[s.id]?.confirmed)

                        return (
                          <TableRow
                            key={r.id}
                            className="cursor-pointer hover:bg-muted/40 transition-colors"
                            onClick={() => setSelectedReq(r)}
                          >
                            <TableCell className="max-w-[220px]">
                              <p className="text-xs font-mono font-semibold text-primary">{r.id}</p>
                              <p className="text-xs text-foreground truncate font-medium">{r.title}</p>
                            </TableCell>
                            <TableCell>
                              <StatusDot tone={PRIORITY_TONE[r.priority]}>{r.priority}</StatusDot>
                            </TableCell>
                            <TableCell>
                              <Badge
                                tone={r.status === 'Passing' ? 'success' : r.status === 'Needs Review' ? 'warning' : 'danger'}
                                className="text-[10px] px-1.5 py-0"
                              >
                                {r.overallScore}% {GATE_STATUS_LABEL[r.status]}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-center">
                              {r.status !== 'Passing' ? (
                                <span className="text-muted-foreground/40 text-xs">—</span>
                              ) : decomposed ? (
                                <CheckCircle2 className="h-4 w-4 text-emerald-500 mx-auto" />
                              ) : stories.length > 0 ? (
                                <AlertTriangle className="h-4 w-4 text-amber-500 mx-auto" />
                              ) : (
                                <span className="text-muted-foreground/40 text-xs">—</span>
                              )}
                            </TableCell>
                            <TableCell className="text-center">
                              {estimated ? (
                                <CheckCircle2 className="h-4 w-4 text-emerald-500 mx-auto" />
                              ) : (
                                <span className="text-muted-foreground/40 text-xs">—</span>
                              )}
                            </TableCell>
                            <TableCell className="text-right">
                              <StatusDot tone={ROW_STATUS_TONE[state.key]}>{state.label}</StatusDot>
                            </TableCell>
                          </TableRow>
                        )
                      })}
                      {filteredRequirements.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={6} className="text-center text-xs text-muted-foreground py-10">
                            No requirements match current search or status filter.
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              </div>

              <div className="p-3 bg-muted/20 border-t border-border flex items-center justify-between text-xs text-muted-foreground">
                <span>Showing {filteredRequirements.length} specifications</span>
                <button
                  type="button"
                  onClick={() => setNewReqModalOpen(true)}
                  className="text-xs font-semibold text-primary hover:underline inline-flex items-center gap-1 cursor-pointer"
                >
                  <PlusCircle className="h-3.5 w-3.5" /> Add Requirement
                </button>
              </div>
            </Card>
          </div>
        </TabsContent>

        {/* ----------------- TAB 3: ACADEMIC MILESTONES & ASSESSMENT RUBRIC ----------------- */}
        <TabsContent value="milestones" className="space-y-6">
          <AcademicMilestonesTimeline onMilestoneSelect={() => {}} />
          <AssessmentRubricCard />
        </TabsContent>

        {/* ----------------- TAB 4: TEAM CAPACITY & WORKLOAD ----------------- */}
        <TabsContent value="workload" className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {workload.map((m) => {
              const profile = m.academicProfile

              return (
                <Card key={m.id} className="p-4 sm:p-5 card-hover-lift flex flex-col justify-between">
                  <div>
                    <div className="flex items-start gap-3 mb-3">
                      <AvatarComp name={m.name} size={42} className="ring-2 ring-primary/20 shrink-0" />
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-bold text-foreground truncate">{m.name}</p>
                        <p className="text-xs font-mono text-primary font-semibold">
                          {profile?.studentId || 'IT23-Pending'}
                        </p>
                        <p className="text-[11px] text-muted-foreground truncate">{m.role}</p>
                      </div>
                    </div>

                    <div className="space-y-2 pt-2 border-t border-border/60">
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Sprint 5 Workload</span>
                        <span className={`font-bold ${m.over ? 'text-destructive' : 'text-foreground'}`}>
                          {m.points} / {m.capacity} SP
                        </span>
                      </div>
                      <Progress
                        value={Math.min(100, m.pct)}
                        className={`h-2 ${m.over ? '[&>div]:bg-destructive' : m.pct >= 80 ? '[&>div]:bg-amber-500' : '[&>div]:bg-emerald-500'}`}
                      />
                      <div className="flex items-center justify-between text-[11px]">
                        <span className={m.over ? 'text-destructive font-semibold' : 'text-muted-foreground'}>
                          {m.pct}% Utilized {m.over && '⚠ Overload'}
                        </span>
                        {profile?.attendance && (
                          <span className="text-muted-foreground">Attendance: {profile.attendance}</span>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="mt-4 pt-3 border-t border-border/60 text-xs">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                      Assigned Kanban Tasks
                    </p>
                    <div className="space-y-1">
                      {kanbanTasks
                        .filter((t) => t.assigneeId === m.id)
                        .slice(0, 2)
                        .map((task) => (
                          <div
                            key={task.id}
                            className="flex items-center justify-between text-[11px] p-1.5 rounded bg-muted/40"
                          >
                            <span className="truncate max-w-[150px] font-medium">{task.title}</span>
                            <span className="font-mono text-primary shrink-0">{task.points} SP</span>
                          </div>
                        ))}
                      {kanbanTasks.filter((t) => t.assigneeId === m.id).length === 0 && (
                        <p className="text-[11px] text-muted-foreground">No tasks assigned yet.</p>
                      )}
                    </div>
                  </div>
                </Card>
              )
            })}
          </div>

          <Card className="p-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 mb-3 border-b border-border">
              <div>
                <h3 className="text-base font-bold text-foreground">Sprint Workload Distribution</h3>
                <p className="text-xs text-muted-foreground">
                  Total sprint capacity: {totalAssigned} SP committed across {totalCapacity} SP team quota
                </p>
              </div>
              <Button
                size="sm"
                onClick={() => navigate('/planning/sprint-management')}
                className="text-xs gap-1.5 cursor-pointer"
              >
                <KanbanSquare className="h-3.5 w-3.5" /> Open Sprint Board
              </Button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
              <div className="p-3 rounded-xl bg-muted/30 border border-border">
                <span className="text-xs text-muted-foreground block">Total Team Velocity</span>
                <span className="text-2xl font-bold text-foreground">{totalPoints} SP</span>
                <span className="text-[11px] text-muted-foreground block mt-1">Average 11 SP / sprint historical</span>
              </div>
              <div className="p-3 rounded-xl bg-muted/30 border border-border">
                <span className="text-xs text-muted-foreground block">Completed this Sprint</span>
                <span className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{donePoints} SP</span>
                <span className="text-[11px] text-muted-foreground block mt-1">
                  {totalPoints ? Math.round((donePoints / totalPoints) * 100) : 0}% of sprint goal
                </span>
              </div>
              <div className="p-3 rounded-xl bg-muted/30 border border-border">
                <span className="text-xs text-muted-foreground block">Remaining Work</span>
                <span className="text-2xl font-bold text-primary">{totalPoints - donePoints} SP</span>
                <span className="text-[11px] text-muted-foreground block mt-1">{daysLeft} days to sprint demo</span>
              </div>
            </div>
          </Card>
        </TabsContent>

        {/* ----------------- TAB 5: DART & AUDIT LOG ----------------- */}
        <TabsContent value="diagnostics" className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
            {/* DART Arbitration Card */}
            <Card className="p-5">
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-border">
                <div>
                  <h3 className="text-base font-bold text-foreground">DART Diagnostic Arbitration</h3>
                  <p className="text-xs text-muted-foreground">Disagreements detected between multi-agent reasoning traces</p>
                </div>
                <Badge tone={openFlags.length > 0 ? 'warning' : 'success'}>
                  {openFlags.length} Open Cases
                </Badge>
              </div>

              {openFlags.length === 0 ? (
                <div className="p-6 text-center text-xs text-muted-foreground">
                  <CheckCircle2 className="h-8 w-8 text-emerald-500 mx-auto mb-2" />
                  <p className="font-semibold text-foreground">All Reasoning Traces in Agreement</p>
                  <p className="mt-1">No outstanding diagnostic conflicts require arbitration.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {openFlags.map((c) => (
                    <div key={c.id} className="p-3 rounded-xl border border-border/80 bg-muted/20 space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5">
                          <Badge tone={ARBITRATION_CATEGORY_TONE[c.category]}>{c.category}</Badge>
                          <span className="font-mono text-xs font-semibold text-primary">{c.requirementId}</span>
                        </div>
                        <span className="text-[11px] font-semibold text-muted-foreground">
                          {c.confidenceAgreement}% Agreement
                        </span>
                      </div>

                      <p className="text-xs font-semibold text-foreground leading-snug">{c.title}</p>
                      <p className="text-[11px] text-muted-foreground leading-relaxed">{c.resolution}</p>

                      <div className="flex items-center justify-between pt-1 border-t border-border/50 text-xs">
                        <span className="text-[10px] text-muted-foreground">{c.createdAt?.slice(0, 10)}</span>
                        <button
                          type="button"
                          onClick={() => navigate('/planning/requirements/srs-quality')}
                          className="text-xs font-semibold text-primary hover:underline inline-flex items-center gap-1 cursor-pointer"
                        >
                          Resolve in Quality Gate <ArrowRight className="h-3 w-3" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* Activity Log Card */}
            <Card className="p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between pb-3 mb-3 border-b border-border">
                  <div className="flex items-center gap-2">
                    <span className="p-1 rounded bg-primary/10 text-primary">
                      <Activity className="h-4 w-4" />
                    </span>
                    <h3 className="text-base font-bold text-foreground">Curriculum Audit Log</h3>
                  </div>

                  <Select value={activityCategoryFilter} onValueChange={setActivityCategoryFilter}>
                    <SelectTrigger className="w-[120px] h-7 text-[11px]">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Events</SelectItem>
                      <SelectItem value="ai">AI Agent</SelectItem>
                      <SelectItem value="dart">DART</SelectItem>
                      <SelectItem value="student">Student</SelectItem>
                      <SelectItem value="sprint">Sprint</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
                  {filteredActivityLog.slice(0, 8).map((a) => {
                    const meta = ACTIVITY_CATEGORY_META[a.category] || ACTIVITY_CATEGORY_META.ai
                    const Icon = meta.icon

                    return (
                      <div key={a.id} className="flex items-start gap-3 text-xs">
                        <span className={`h-7 w-7 rounded-full flex items-center justify-center shrink-0 ${meta.className}`}>
                          <Icon className="h-3.5 w-3.5" />
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-0.5">
                            {meta.label}
                          </p>
                          <p className="text-xs text-foreground leading-snug">{a.text}</p>
                          <p className="text-[10px] text-muted-foreground mt-0.5">{formatRelativeTime(a.timestamp)}</p>
                        </div>
                      </div>
                    )
                  })}

                  {filteredActivityLog.length === 0 && (
                    <p className="text-xs text-muted-foreground text-center py-6">
                      No activity logged for this category.
                    </p>
                  )}
                </div>
              </div>

              <div className="pt-3 mt-3 border-t border-border text-[11px] text-muted-foreground flex items-center justify-between">
                <span>{activityLog.length} total events audited</span>
                <span className="text-primary font-medium">IEEE 830 Traceability Active</span>
              </div>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Requirement Detail Drawer (`Sheet`) */}
      <Sheet open={Boolean(selectedReq)} onOpenChange={(open) => !open && setSelectedReq(null)}>
        <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto column-scroll-contain">
          {selectedReq && (
            <>
              <SheetHeader>
                <div className="flex items-center gap-2 flex-wrap mb-1">
                  <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-primary/10 text-primary">
                    {selectedReq.id}
                  </span>
                  <Badge tone={PRIORITY_TONE[selectedReq.priority]}>{selectedReq.priority}</Badge>
                  <Badge tone={GATE_STATUS_TONE[selectedReq.status]}>{selectedReq.status}</Badge>
                </div>
                <SheetTitle className="text-left text-base leading-snug">{selectedReq.title}</SheetTitle>
                <SheetDescription className="text-left text-xs">
                  Detailed quality dimension breakdown and pipeline traceability
                </SheetDescription>
              </SheetHeader>

              <div className="px-4 pb-4 space-y-4 text-xs mt-3">
                <div className="p-3 rounded-xl bg-muted/40 border border-border">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1">
                    IEEE 830 Specification
                  </p>
                  <p className="text-xs text-foreground leading-relaxed font-sans">{selectedReq.description}</p>
                </div>

                {selectedReq.suggestedRewrite && (
                  <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs space-y-1">
                    <p className="font-bold text-amber-700 dark:text-amber-300 flex items-center gap-1">
                      <Sparkles className="h-3.5 w-3.5" /> Agent Suggested Rewrite
                    </p>
                    <p className="text-foreground/90 leading-relaxed text-[11px]">{selectedReq.suggestedRewrite}</p>
                  </div>
                )}

                <div>
                  <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">
                    Quality Dimension Scores
                  </p>
                  <div className="space-y-2 p-3 rounded-xl border border-border bg-card">
                    {QUALITY_DIMENSIONS.map((dim) => {
                      const score = selectedReq.dimensionScores?.[dim.key] ?? 0
                      const tone = score >= 75 ? 'success' : score >= 50 ? 'warning' : 'danger'
                      return (
                        <div key={dim.key} className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">{dim.label}</span>
                          <div className="flex items-center gap-2">
                            <Progress value={score} className="w-16 h-1" />
                            <StatusDot tone={tone}>{score}%</StatusDot>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>

                {selectedArbitration.length > 0 && (
                  <div>
                    <p className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2">
                      DART Arbitration Cases
                    </p>
                    <div className="space-y-2">
                      {selectedArbitration.map((c) => (
                        <div key={c.id} className="p-2.5 rounded-lg border border-border bg-muted/20 text-xs">
                          <div className="flex items-center gap-2 mb-1">
                            <Badge tone={ARBITRATION_CATEGORY_TONE[c.category]}>{c.category}</Badge>
                            <span className="text-muted-foreground text-[10px]">{c.confidenceAgreement}% Agreement</span>
                          </div>
                          <p className="text-foreground leading-snug">{c.title}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="pt-2 space-y-2">
                  <Button
                    className="w-full text-xs cursor-pointer"
                    onClick={() => {
                      const target = targetForRequirement(selectedReq, userStories, estimations)
                      setSelectedReq(null)
                      navigate(target)
                    }}
                  >
                    Open in Planning Pipeline ({targetForRequirement(selectedReq, userStories, estimations).split('/').pop()})
                  </Button>
                  <Button
                    variant="outline"
                    className="w-full text-xs cursor-pointer"
                    onClick={() => {
                      setSelectedReq(null)
                      setConsultModalOpen(true)
                    }}
                  >
                    Request Supervisor Review for this Requirement
                  </Button>
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* LMS Modals */}
      <SupervisorConsultationModal
        open={consultModalOpen}
        onOpenChange={setConsultModalOpen}
        requirements={requirements}
      />

      <ExportPlanningReportModal
        open={exportModalOpen}
        onOpenChange={setExportModalOpen}
        requirements={requirements}
        kanbanTasks={kanbanTasks}
        teamMembers={teamMembers}
        projectInfo={projectInfo}
        stats={stats}
      />

      <NewRequirementModal
        open={newReqModalOpen}
        onOpenChange={setNewReqModalOpen}
        existingCount={requirements.length}
      />

      <DartButton context="dashboard" />
    </div>
  )
}
