import { useEffect } from 'react'
import { Gauge, Sparkles, CheckCircle2 } from 'lucide-react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  Legend,
} from 'recharts'
import PageHeader from '../../../../../shared/components/PageHeader.jsx'
import Card from '../../../../../shared/components/Card.jsx'
import Badge from '../../../../../shared/components/Badge.jsx'
import EmptyState from '../../../../../shared/components/EmptyState.jsx'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { usePlanningData } from '../../../context/usePlanningData.js'
import { VELOCITY_TREND, STORY_POINT_SCALE } from '../../../data/mockData.js'
import { showToast } from '@/shared/utils/toast.jsx'

function computeAiPoints(story) {
  const taskCount = story.tasks.length
  if (taskCount <= 1) return 3
  if (taskCount === 2) return 5
  return 8
}

export default function Estimation() {
  const { requirements, userStories, estimations, setEstimation, confirmEstimation } = usePlanningData()

  const acceptedStories = []
  for (const req of requirements) {
    for (const story of userStories[req.id] || []) {
      if (story.status === 'Accepted') acceptedStories.push({ req, story })
    }
  }

  useEffect(() => {
    acceptedStories.forEach(({ story }) => {
      if (!estimations[story.id]) {
        setEstimation(story.id, {
          points: null,
          aiPoints: computeAiPoints(story),
          aiRationale: `Based on ${story.tasks.length} task(s), similar stories historically took this long.`,
          confirmed: false,
        })
      }
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [acceptedStories.length])

  const pending = acceptedStories.filter(({ story }) => !estimations[story.id]?.confirmed)

  function confirm(reqId, story) {
    const est = estimations[story.id]
    const points = est?.points ?? est?.aiPoints ?? 3
    confirmEstimation(reqId, story.id, story.title, points)
    showToast.success('Effort assigned', {
      description: `${story.id} is now on the Sprint Management board at ${points} SP.`,
    })
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Effort Estimation"
        breadcrumb={['Planning', 'Requirements', 'Effort Estimation']}
        description="Assign story points to each accepted user story, compare against the Estimation agent's own view, and confirm to send it to Sprint Management."
      />

      <Card>
        <h3 className="text-base font-semibold text-foreground mb-4">Team velocity vs. plan (last 3 sprints)</h3>
        <div style={{ width: '100%', height: 220 }}>
          <ResponsiveContainer>
            <LineChart data={VELOCITY_TREND}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="sprint" tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }} />
              <YAxis tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }} />
              <RechartsTooltip
                contentStyle={{ backgroundColor: 'var(--popover)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="planned" name="Planned" stroke="var(--chart-2)" strokeWidth={2} dot={{ r: 3 }} />
              <Line type="monotone" dataKey="velocity" name="Actual velocity" stroke="var(--chart-1)" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      {pending.length === 0 ? (
        <EmptyState
          icon={Sparkles}
          title="Nothing waiting on estimation"
          description="Accept a user story in Decomposition first — it will show up here for effort estimation."
        />
      ) : (
        <Card className="p-0 overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Story</TableHead>
                <TableHead className="w-[100px]">Requirement</TableHead>
                <TableHead className="w-[190px]">AI suggestion</TableHead>
                <TableHead className="w-[140px]">Your points</TableHead>
                <TableHead className="w-[150px] text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pending.map(({ req, story }) => {
                const est = estimations[story.id]
                return (
                  <TableRow key={story.id}>
                    <TableCell className="max-w-sm">
                      <p className="text-sm text-foreground truncate">{story.title}</p>
                      <p className="text-xs text-muted-foreground">{story.id}</p>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">{req.id}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1.5">
                        <Badge tone="primary">{est?.aiPoints ?? '—'} SP</Badge>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1 leading-snug max-w-[170px]">{est?.aiRationale}</p>
                    </TableCell>
                    <TableCell>
                      <Select
                        value={String(est?.points ?? est?.aiPoints ?? '')}
                        onValueChange={(v) => setEstimation(story.id, { points: Number(v) })}
                      >
                        <SelectTrigger className="w-[100px]">
                          <SelectValue placeholder="SP" />
                        </SelectTrigger>
                        <SelectContent>
                          {STORY_POINT_SCALE.map((p) => (
                            <SelectItem key={p} value={String(p)}>
                              {p} SP
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button size="sm" onClick={() => confirm(req.id, story)} className="active:scale-[0.98]">
                        <CheckCircle2 className="h-3.5 w-3.5" />
                        Confirm
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </Card>
      )}

      {acceptedStories.length > pending.length && (
        <Card>
          <div className="flex items-center gap-2 mb-1">
            <Gauge className="h-4 w-4 text-emerald-500" />
            <h3 className="text-sm font-semibold text-foreground">Already estimated & on the sprint board</h3>
          </div>
          <p className="text-xs text-muted-foreground">
            {acceptedStories.length - pending.length} stor{acceptedStories.length - pending.length === 1 ? 'y is' : 'ies are'} now tracked in Sprint Management.
          </p>
        </Card>
      )}
    </div>
  )
}
