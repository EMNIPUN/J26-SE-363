import { useNavigate } from 'react-router-dom'
import {
  ClipboardCheck,
  GitBranch,
  Gauge,
  KanbanSquare,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Circle,
} from 'lucide-react'
import PageHeader from '../../../../shared/components/PageHeader.jsx'
import Card from '../../../../shared/components/Card.jsx'
import StatCard from '../../../../shared/components/StatCard.jsx'
import Badge from '../../../../shared/components/Badge.jsx'
import AvatarComp from '../../../../shared/components/Avatar.jsx'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import QualityRadarChart from '../../components/QualityRadarChart.jsx'
import WorkflowStepper from '../../components/WorkflowStepper.jsx'
import DartButton from '../../components/DartButton.jsx'
import { usePlanningData } from '../../context/usePlanningData.js'
import { QUALITY_DIMENSIONS } from '../../data/mockData.js'
import { computeStageStats, getNextAction } from '../../stageStats.js'

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

const STAGE_ICON = {
  Passing: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />,
  'Needs Review': <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />,
  Failing: <XCircle className="h-3.5 w-3.5 text-destructive" />,
}

const ROW_STATUS_TONE = { ready: 'success', waiting: 'primary', attention: 'warning', blocked: 'danger' }

export default function Dashboard() {
  const navigate = useNavigate()
  const { requirements, userStories, estimations, kanbanTasks, teamMembers, projectInfo } = usePlanningData()

  const stats = computeStageStats({ requirements, userStories, estimations, kanbanTasks })
  const nextAction = getNextAction(stats)

  const avgScore = stats.quality.percent
  const passingCount = requirements.filter((r) => r.status === 'Passing').length
  const totalPoints = kanbanTasks.reduce((s, t) => s + t.points, 0)
  const donePoints = kanbanTasks.filter((t) => t.status === 'Done').reduce((s, t) => s + t.points, 0)

  const currentStage = stats.quality.percent < 100
    ? 'SRS Quality'
    : stats.decomposition.percent < 100
      ? 'Decomposition'
      : stats.effort.percent < 100
        ? 'Effort Estimation'
        : 'Sprint Management'

  const avgDimensionScores = QUALITY_DIMENSIONS.reduce((acc, dim) => {
    acc[dim.key] = Math.round(requirements.reduce((sum, r) => sum + r.dimensionScores[dim.key], 0) / requirements.length)
    return acc
  }, {})

  return (
    <div className="space-y-6">
      <PageHeader
        title="Project Planning"
        breadcrumb={['Planning', 'Student', 'Dashboard']}
        description="Where you are in your project planning pipeline, and what needs your attention next."
      />

      <Card className="p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Active project</p>
          <h2 className="text-lg font-semibold text-foreground">{projectInfo.name}</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Team {teamMembers.length} members · Status: Planning · Current stage: {currentStage}
          </p>
        </div>
        <Badge tone="primary" className="text-sm px-3 py-1">
          {projectInfo.sprintName} of {projectInfo.totalSprints}
        </Badge>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2">
          <h3 className="text-base font-semibold text-foreground mb-4">Project planning status</h3>
          <WorkflowStepper variant="full" />
        </Card>

        <Card className={`flex flex-col justify-between ${nextAction.tone === 'danger' ? 'border-destructive/30' : nextAction.tone === 'success' ? 'border-emerald-500/30' : 'border-amber-500/30'}`}>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Next action</p>
            <p className="text-sm font-medium text-foreground leading-snug">{nextAction.text}</p>
          </div>
          <button
            type="button"
            onClick={() => navigate(nextAction.to)}
            className="mt-4 inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline cursor-pointer self-start"
          >
            Go there now <ArrowRight className="h-3 w-3" />
          </button>
        </Card>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={ClipboardCheck} label="Requirements" value={requirements.length} trend={`${passingCount} passed`} tone="primary" />
        <StatCard icon={GitBranch} label="SRS Quality" value={`${avgScore}%`} trend={avgScore >= 70 ? 'Gate clear' : 'Gate blocked'} tone={avgScore >= 70 ? 'success' : 'warning'} />
        <StatCard icon={Gauge} label="Estimated Work" value={`${totalPoints} SP`} trend={`${totalPoints - donePoints} SP remaining`} tone="primary" />
        <StatCard icon={KanbanSquare} label="Current Sprint" value={projectInfo.sprintName} trend={`${kanbanTasks.length} tasks`} tone="primary" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1">
          <h3 className="text-base font-semibold text-foreground mb-2">Six-dimension quality profile</h3>
          <p className="text-xs text-muted-foreground mb-2">Averaged across all tracked requirements</p>
          <QualityRadarChart scores={avgDimensionScores} height={200} />
        </Card>

        <Card className="lg:col-span-2 p-0 overflow-hidden">
          <div className="p-5 pb-3">
            <h3 className="text-base font-semibold text-foreground">Requirement health</h3>
            <p className="text-xs text-muted-foreground">Click a row to jump straight to the stage it needs.</p>
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Requirement</TableHead>
                <TableHead className="w-[70px] text-center">Quality</TableHead>
                <TableHead className="w-[90px] text-center">Decomp.</TableHead>
                <TableHead className="w-[70px] text-center">Effort</TableHead>
                <TableHead className="w-[100px]">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {requirements.map((r) => {
                const state = reqStageState(r, userStories, estimations)
                const stories = userStories[r.id] || []
                const decomposed = stories.length > 0 && stories.every((s) => s.status === 'Accepted')
                const estimated = stories.length > 0 && stories.every((s) => estimations[s.id]?.confirmed)
                const target =
                  r.status !== 'Passing'
                    ? '/planning/requirements/srs-quality'
                    : !decomposed
                      ? '/planning/requirements/decomposition'
                      : !estimated
                        ? '/planning/requirements/estimation'
                        : '/planning/sprint-management'
                return (
                  <TableRow key={r.id} className="cursor-pointer" onClick={() => navigate(target)}>
                    <TableCell className="max-w-[220px]">
                      <p className="text-xs font-medium text-muted-foreground">{r.id}</p>
                      <p className="text-sm text-foreground truncate">{r.title}</p>
                    </TableCell>
                    <TableCell className="text-center">{STAGE_ICON[r.status]}</TableCell>
                    <TableCell className="text-center">
                      {r.status !== 'Passing' ? <Circle className="h-3.5 w-3.5 text-muted-foreground/40 mx-auto" /> : decomposed ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 mx-auto" /> : stories.length > 0 ? <AlertTriangle className="h-3.5 w-3.5 text-amber-500 mx-auto" /> : <Circle className="h-3.5 w-3.5 text-muted-foreground/40 mx-auto" />}
                    </TableCell>
                    <TableCell className="text-center">
                      {estimated ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 mx-auto" /> : <Circle className="h-3.5 w-3.5 text-muted-foreground/40 mx-auto" />}
                    </TableCell>
                    <TableCell>
                      <Badge tone={ROW_STATUS_TONE[state.key]}>{state.label}</Badge>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </Card>
      </div>

      <Card>
        <h3 className="text-base font-semibold text-foreground mb-4">Team members</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {teamMembers.map((m) => (
            <div key={m.id} className="flex items-center gap-3 p-3 rounded-lg border border-border bg-muted/20">
              <AvatarComp name={m.name} size={36} />
              <div className="min-w-0">
                <p className="text-sm font-medium text-foreground truncate">{m.name}</p>
                <p className="text-xs text-muted-foreground truncate">{m.role}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <DartButton context="dashboard" />
    </div>
  )
}
