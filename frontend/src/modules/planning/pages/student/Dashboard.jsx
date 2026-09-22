import { Link } from 'react-router-dom'
import { ClipboardCheck, GitBranch, Gauge, ArrowUpRight, KanbanSquare } from 'lucide-react'
import PageHeader from '../../../../shared/components/PageHeader.jsx'
import Card from '../../../../shared/components/Card.jsx'
import StatCard from '../../../../shared/components/StatCard.jsx'
import Badge from '../../../../shared/components/Badge.jsx'
import AvatarComp from '../../../../shared/components/Avatar.jsx'
import QualityRadarChart from '../../components/QualityRadarChart.jsx'
import { usePlanningData } from '../../context/usePlanningData.js'
import { ACTIVITY_FEED, QUALITY_DIMENSIONS } from '../../data/mockData.js'

const ACTIVITY_DOT_TONE = {
  primary: 'bg-primary',
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  danger: 'bg-destructive',
}

const SHORTCUTS = [
  { label: 'SRS Quality', to: '/planning/requirements/srs-quality' },
  { label: 'Decomposition', to: '/planning/requirements/decomposition' },
  { label: 'Effort Estimation', to: '/planning/requirements/estimation' },
  { label: 'Sprint Management', to: '/planning/sprint-management' },
]

export default function Dashboard() {
  const { requirements, kanbanTasks, teamMembers, projectInfo } = usePlanningData()

  const avgScore = Math.round(requirements.reduce((sum, r) => sum + r.overallScore, 0) / requirements.length)
  const passingCount = requirements.filter((r) => r.status === 'Passing').length
  const totalPoints = kanbanTasks.reduce((s, t) => s + t.points, 0)
  const donePoints = kanbanTasks.filter((t) => t.status === 'Done').reduce((s, t) => s + t.points, 0)
  const sprintProgress = totalPoints ? Math.round((donePoints / totalPoints) * 100) : 0

  const avgDimensionScores = QUALITY_DIMENSIONS.reduce((acc, dim) => {
    acc[dim.key] = Math.round(
      requirements.reduce((sum, r) => sum + r.dimensionScores[dim.key], 0) / requirements.length,
    )
    return acc
  }, {})

  return (
    <div className="space-y-6">
      <PageHeader
        title="Student Dashboard"
        breadcrumb={['Planning', 'Student', 'Dashboard']}
        description="Summary of your project's requirement quality, decomposition and sprint progress."
      />

      <Card className="p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Active project</p>
          <h2 className="text-lg font-semibold text-foreground">{projectInfo.name}</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            Batch {projectInfo.batch} · Supervised by {projectInfo.supervisor} · {projectInfo.sprintName} of {projectInfo.totalSprints}
          </p>
        </div>
        <Badge tone="primary" className="text-sm px-3 py-1">
          Quality gate {avgScore}%
        </Badge>
      </Card>

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

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={ClipboardCheck} label="Quality Gate Score" value={`${avgScore}%`} trend="+5% this sprint" tone="success" />
        <StatCard icon={GitBranch} label="Requirements Passing" value={`${passingCount}/${requirements.length}`} tone="primary" />
        <StatCard icon={Gauge} label="Story Points Completed" value={`${donePoints}/${totalPoints}`} tone="primary" />
        <StatCard icon={KanbanSquare} label="Sprint Progress" value={`${sprintProgress}%`} trend={projectInfo.sprintName} tone={sprintProgress >= 50 ? 'success' : 'warning'} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1">
          <h3 className="text-base font-semibold text-foreground mb-2">Six-dimension quality profile</h3>
          <p className="text-xs text-muted-foreground mb-2">Averaged across all tracked requirements</p>
          <QualityRadarChart scores={avgDimensionScores} height={220} />
        </Card>

        <Card className="lg:col-span-2">
          <h3 className="text-base font-semibold text-foreground mb-4">Pipeline activity</h3>
          <ul className="space-y-4">
            {ACTIVITY_FEED.map((item) => (
              <li key={item.id} className="flex items-start gap-3 text-sm">
                <span className={`h-2 w-2 rounded-full mt-1.5 shrink-0 ${ACTIVITY_DOT_TONE[item.tone]}`} />
                <div>
                  <span className="text-foreground">{item.text}</span>
                  <span className="block text-xs text-muted-foreground mt-0.5">{item.time}</span>
                </div>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card>
        <h3 className="text-base font-semibold text-foreground mb-4">Jump to</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {SHORTCUTS.map((s) => (
            <Link
              key={s.to}
              to={s.to}
              className="flex items-center justify-between text-sm text-foreground rounded-lg px-3 py-2.5 border border-border hover:bg-muted transition-colors duration-150 active:scale-[0.98]"
            >
              {s.label}
              <ArrowUpRight className="h-3.5 w-3.5 text-muted-foreground" />
            </Link>
          ))}
        </div>
      </Card>
    </div>
  )
}
