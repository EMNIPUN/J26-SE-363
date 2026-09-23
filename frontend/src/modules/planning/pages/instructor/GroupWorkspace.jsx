import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Radio } from 'lucide-react'
import PageHeader from '../../../../shared/components/PageHeader.jsx'
import Card from '../../../../shared/components/Card.jsx'
import Badge from '../../../../shared/components/Badge.jsx'
import EmptyState from '../../../../shared/components/EmptyState.jsx'
import AvatarComp from '../../../../shared/components/Avatar.jsx'
import { Progress } from '@/components/ui/progress'
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
import GanttTimeline from '../../components/GanttTimeline.jsx'
import { usePlanningData } from '../../context/usePlanningData.js'
import {
  GROUPS,
  ARBITRATION_CASES,
  QUALITY_DIMENSIONS,
  TEAM_MEMBERS,
  PROJECT_INFO,
  getGroupPipelineData,
} from '../../data/mockData.js'
import { computeStageStats, STAGE_ORDER } from '../../stageStats.js'
import { GATE_STATUS_TONE, RISK_TONE, ARBITRATION_CATEGORY_TONE } from '../../utils.js'

export default function GroupWorkspace() {
  const { groupId } = useParams()
  const group = GROUPS.find((g) => g.id === groupId)
  const live = usePlanningData()

  if (!group) {
    return (
      <div className="space-y-6">
        <PageHeader title="Group not found" breadcrumb={['Planning', 'Instructor', 'Groups']} />
        <EmptyState
          title="No such group"
          description="This group may have been removed or the link is out of date."
          actionLabel="Back to Groups"
          onAction={() => window.history.back()}
        />
      </div>
    )
  }

  const isLive = group.id === PROJECT_INFO.groupId
  const data = isLive
    ? { requirements: live.requirements, userStories: live.userStories, estimations: live.estimations, kanbanTasks: live.kanbanTasks }
    : getGroupPipelineData(group)

  const { requirements, userStories, estimations, kanbanTasks } = data
  const cases = ARBITRATION_CASES.filter((c) => group.requirementIds.includes(c.requirementId))
  const stats = computeStageStats({ requirements, userStories, estimations, kanbanTasks })

  const avgDimensionScores = QUALITY_DIMENSIONS.reduce((acc, dim) => {
    acc[dim.key] = requirements.length
      ? Math.round(requirements.reduce((sum, r) => sum + r.dimensionScores[dim.key], 0) / requirements.length)
      : 0
    return acc
  }, {})

  const members = isLive ? TEAM_MEMBERS : []
  const membersWithLoad = members.map((m) => {
    const assigned = kanbanTasks.filter((t) => t.assigneeId === m.id)
    const done = assigned.filter((t) => t.status === 'Done')
    const current = assigned.filter((t) => t.status !== 'Done').reduce((s, t) => s + t.points, 0)
    return { member: m, assignedCount: assigned.length, doneCount: done.length, current }
  })

  return (
    <div className="space-y-6">
      <div>
        <Link
          to="/planning/instructor/groups"
          className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground mb-3 transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Groups
        </Link>
        <PageHeader
          title={group.name}
          breadcrumb={['Planning', 'Instructor', 'Groups', group.name]}
          description={group.project}
          actions={
            <>
              {isLive && (
                <Badge tone="success" className="text-sm px-2.5 py-1 flex items-center gap-1">
                  <Radio className="h-3 w-3" />
                  Live
                </Badge>
              )}
              <Badge tone={RISK_TONE[group.risk]} className="text-sm px-2.5 py-1">
                {group.risk} risk
              </Badge>
              <Badge tone="primary" className="text-sm px-2.5 py-1">
                Quality gate {group.qualityGate}%
              </Badge>
            </>
          }
        />
      </div>

      <Card>
        <h3 className="text-base font-semibold text-foreground mb-4">Pipeline progress</h3>
        {isLive ? (
          <WorkflowStepper variant="full" />
        ) : (
          <div className="space-y-3">
            {STAGE_ORDER.map((key) => {
              const stage = stats[key]
              return (
                <div key={key} className="flex items-center gap-4">
                  <span className="text-sm font-medium text-foreground w-40 shrink-0">{stage.label}</span>
                  <Progress value={stage.percent} className="h-2 flex-1" />
                  <span className="text-xs font-semibold text-muted-foreground w-10 text-right shrink-0">{stage.percent}%</span>
                </div>
              )
            })}
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card>
          <h3 className="text-base font-semibold text-foreground mb-2">Quality profile</h3>
          <p className="text-xs text-muted-foreground mb-2">Averaged across this group's requirements</p>
          <QualityRadarChart scores={avgDimensionScores} height={220} />
        </Card>

        <Card className="lg:col-span-2">
          <h3 className="text-base font-semibold text-foreground mb-4">Requirements</h3>
          {requirements.length === 0 ? (
            <EmptyState card={false} title="No requirements yet" description="This group has not submitted any requirements." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID</TableHead>
                  <TableHead>Requirement</TableHead>
                  <TableHead className="w-[120px]">Gate</TableHead>
                  <TableHead className="w-[110px]">Decomposed</TableHead>
                  <TableHead className="w-[100px]">Estimated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {requirements.map((r) => {
                  const stories = userStories[r.id] || []
                  const estimatedPoints = stories.reduce((sum, s) => {
                    const est = estimations[s.id]
                    return sum + (est ? est.finalPoints ?? est.studentPoints ?? est.aiPoints ?? 0 : 0)
                  }, 0)
                  return (
                    <TableRow key={r.id}>
                      <TableCell className="font-medium text-muted-foreground">{r.id}</TableCell>
                      <TableCell className="max-w-xs truncate">{r.title}</TableCell>
                      <TableCell>
                        <Badge tone={GATE_STATUS_TONE[r.status]}>{r.status}</Badge>
                      </TableCell>
                      <TableCell>{stories.length > 0 ? `${stories.length} stories` : '—'}</TableCell>
                      <TableCell>{estimatedPoints > 0 ? `${estimatedPoints} SP` : '—'}</TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <h3 className="text-base font-semibold text-foreground mb-1">Team progress</h3>
          <p className="text-xs text-muted-foreground mb-4">Individual contribution across the requirements-to-backlog pipeline</p>
          {membersWithLoad.length === 0 ? (
            <p className="text-xs text-muted-foreground">Detailed team activity becomes available once this group's board is live.</p>
          ) : (
            <div className="space-y-3">
              {membersWithLoad.map(({ member, assignedCount, doneCount, current }) => (
                <div key={member.id} className="flex items-center gap-3">
                  <AvatarComp name={member.name} size={30} />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-foreground truncate">{member.name}</p>
                    <p className="text-[11px] text-muted-foreground">{doneCount}/{assignedCount} tasks done</p>
                  </div>
                  <div className="w-28 shrink-0">
                    <Progress value={Math.min(100, (current / member.capacity) * 100)} className={`h-1.5 ${current > member.capacity ? '[&>div]:bg-destructive' : ''}`} />
                  </div>
                  <span className={`text-xs w-16 text-right shrink-0 ${current > member.capacity ? 'text-destructive font-medium' : 'text-muted-foreground'}`}>
                    {current}/{member.capacity} SP
                  </span>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Card>
          <h3 className="text-base font-semibold text-foreground mb-1">Sprint timeline</h3>
          <p className="text-xs text-muted-foreground mb-4">{PROJECT_INFO.sprintName} · read-only</p>
          <GanttTimeline tasks={kanbanTasks} sprintStart={PROJECT_INFO.sprintStartDate} sprintEnd={PROJECT_INFO.sprintEndDate} />
        </Card>
      </div>

      <Card>
        <h3 className="text-base font-semibold text-foreground mb-4">DART flags for this group</h3>
        {cases.length === 0 ? (
          <EmptyState card={false} title="No arbitration cases" description="No agent disagreements have been raised for this group." />
        ) : (
          <ul className="space-y-3">
            {cases.map((c) => (
              <li key={c.id} className="p-3 rounded-lg border border-border flex items-center justify-between gap-3 flex-wrap">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <Badge tone={ARBITRATION_CATEGORY_TONE[c.category]}>{c.category}</Badge>
                    <Badge tone={c.status === 'Open' ? 'warning' : 'success'}>{c.status}</Badge>
                    <span className="text-xs text-muted-foreground">on {c.requirementId}</span>
                  </div>
                  <p className="text-sm text-foreground truncate">{c.title}</p>
                </div>
                <span className="text-xs text-muted-foreground shrink-0">{c.confidenceAgreement}% agreement</span>
              </li>
            ))}
          </ul>
        )}
      </Card>

      {isLive && <DartButton context="dashboard" />}
    </div>
  )
}
