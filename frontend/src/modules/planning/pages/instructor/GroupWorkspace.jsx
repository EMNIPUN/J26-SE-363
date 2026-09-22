import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import PageHeader from '../../../../shared/components/PageHeader.jsx'
import Card from '../../../../shared/components/Card.jsx'
import Badge from '../../../../shared/components/Badge.jsx'
import EmptyState from '../../../../shared/components/EmptyState.jsx'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import QualityRadarChart from '../../components/QualityRadarChart.jsx'
import {
  GROUPS,
  REQUIREMENTS,
  USER_STORIES_SEED,
  STORY_ESTIMATIONS_SEED,
  ARBITRATION_CASES,
  QUALITY_DIMENSIONS,
} from '../../data/mockData.js'
import { GATE_STATUS_TONE, RISK_TONE, ARBITRATION_CATEGORY_TONE } from '../../utils.js'

export default function GroupWorkspace() {
  const { groupId } = useParams()
  const group = GROUPS.find((g) => g.id === groupId)

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

  const requirements = REQUIREMENTS.filter((r) => group.requirementIds.includes(r.id))
  const cases = ARBITRATION_CASES.filter((c) => group.requirementIds.includes(c.requirementId))

  const avgDimensionScores = QUALITY_DIMENSIONS.reduce((acc, dim) => {
    acc[dim.key] = requirements.length
      ? Math.round(requirements.reduce((sum, r) => sum + r.dimensionScores[dim.key], 0) / requirements.length)
      : 0
    return acc
  }, {})

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
                  const stories = USER_STORIES_SEED[r.id] || []
                  const estimatedPoints = stories.reduce((sum, s) => {
                    const est = STORY_ESTIMATIONS_SEED[s.id]
                    return sum + (est ? est.points ?? est.aiPoints ?? 0 : 0)
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
    </div>
  )
}
