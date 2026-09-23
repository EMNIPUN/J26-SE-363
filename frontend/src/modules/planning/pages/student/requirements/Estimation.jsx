import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ChevronDown, CheckCircle2, Sparkles, Lock, ArrowRight, Gauge } from 'lucide-react'
import PageHeader from '../../../../../shared/components/PageHeader.jsx'
import Card from '../../../../../shared/components/Card.jsx'
import Badge from '../../../../../shared/components/Badge.jsx'
import EmptyState from '../../../../../shared/components/EmptyState.jsx'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import WorkflowStepper from '../../../components/WorkflowStepper.jsx'
import DartButton from '../../../components/DartButton.jsx'
import RequirementListPanel from '../../../components/RequirementListPanel.jsx'
import { usePlanningData } from '../../../context/usePlanningData.js'
import { STORY_POINT_SCALE } from '../../../data/mockData.js'
import { showToast } from '@/shared/utils/toast.jsx'

const CONFIDENCE_TONE = { High: 'success', Medium: 'primary', Low: 'warning' }

function computeAiPoints(story) {
  const taskCount = story.tasks.length
  if (taskCount <= 1) return 3
  if (taskCount === 2) return 5
  return 8
}

function computeAiFactors(story) {
  return [
    `${story.tasks.length} implementation task(s) identified`,
    story.tasks.length >= 3 ? 'Multiple dependent tasks increase coordination effort' : 'Small, well-scoped task set',
    story.investResult?.overallPass ? 'Story passed INVEST validation cleanly' : 'Story required revision before it passed INVEST',
  ]
}

function StoryRow({ req, story }) {
  const { estimations, setEstimation, confirmEstimation } = usePlanningData()
  const [expanded, setExpanded] = useState(false)
  const [revealing, setRevealing] = useState(false)
  const est = estimations[story.id]
  const revealed = !!est?.aiRevealed
  const diff = revealed && est?.studentPoints != null ? est.studentPoints - est.aiPoints : null

  function getAiEstimate() {
    setRevealing(true)
    setTimeout(() => {
      setEstimation(story.id, {
        aiPoints: computeAiPoints(story),
        aiConfidence: story.tasks.length >= 3 ? 'Medium' : 'High',
        aiFactors: computeAiFactors(story),
        aiRevealed: true,
      })
      setRevealing(false)
      showToast.success('AI estimate ready', { description: `Compare it against your ${est?.studentPoints} SP estimate for ${story.id}.` })
    }, 900)
  }

  function confirm() {
    const finalPoints = est?.finalPoints ?? est?.studentPoints ?? 3
    confirmEstimation(req.id, story.id, story.title, finalPoints, est?.reason)
    showToast.success('Effort assigned', { description: `${story.id} is now on the Sprint Management board at ${finalPoints} SP.` })
  }

  return (
    <Card className="p-0 overflow-hidden">
      <button type="button" onClick={() => setExpanded((v) => !v)} className="w-full flex items-center justify-between gap-3 p-4 text-left cursor-pointer hover:bg-muted/30 transition-colors">
        <div className="min-w-0 flex-1">
          <p className="text-sm text-foreground truncate">{story.title}</p>
          <p className="text-xs text-muted-foreground">{story.id} · {req.id}</p>
        </div>
        <div className="flex items-center gap-4 shrink-0">
          <div className="text-center">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Student</p>
            <p className="text-sm font-semibold text-foreground">{est?.studentPoints ?? '—'}</p>
          </div>
          <div className="text-center">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">AI</p>
            <p className="text-sm font-semibold text-primary flex items-center justify-center gap-1">
              {revealed ? `${est.aiPoints}` : <Lock className="h-3 w-3 text-muted-foreground" />}
            </p>
          </div>
          <div className="text-center w-12">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Diff</p>
            <p className={`text-sm font-semibold ${diff > 0 ? 'text-amber-600 dark:text-amber-400' : diff < 0 ? 'text-primary' : 'text-muted-foreground'}`}>
              {diff == null ? '—' : diff > 0 ? `+${diff}` : diff}
            </p>
          </div>
          <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-4 animate-fade-rise">
          <div className="p-3 rounded-lg border border-border">
            <p className="text-xs font-semibold text-muted-foreground mb-2">Your estimate — give this first</p>
            <Select
              value={String(est?.studentPoints ?? '')}
              onValueChange={(v) => setEstimation(story.id, { studentPoints: Number(v) })}
              disabled={revealed}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select story points" />
              </SelectTrigger>
              <SelectContent>
                {STORY_POINT_SCALE.map((p) => (
                  <SelectItem key={p} value={String(p)}>{p} SP</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {!revealed ? (
            <div className="p-4 rounded-lg border border-dashed border-border bg-muted/20 flex flex-col items-center text-center gap-2">
              <Lock className="h-4 w-4 text-muted-foreground" />
              <p className="text-xs text-muted-foreground max-w-xs">
                The AI estimate stays hidden until you commit your own — that way it can't anchor your judgment.
              </p>
              <Button
                size="sm"
                onClick={getAiEstimate}
                disabled={est?.studentPoints == null || revealing}
                className="active:scale-[0.98] mt-1"
              >
                <Gauge className={`h-3.5 w-3.5 ${revealing ? 'animate-pulse' : ''}`} />
                {revealing ? 'AI is estimating…' : 'Get AI estimate'}
              </Button>
            </div>
          ) : (
            <>
              <div className="p-3 rounded-lg border border-primary/20 bg-primary/5">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-xs font-semibold text-primary">AI estimate</p>
                  <Badge tone={CONFIDENCE_TONE[est?.aiConfidence] || 'neutral'}>{est?.aiConfidence} confidence</Badge>
                </div>
                <p className="text-lg font-bold text-foreground mb-1">{est?.aiPoints} SP</p>
                <ul className="text-[11px] text-muted-foreground list-disc list-inside space-y-0.5">
                  {est?.aiFactors?.map((f) => <li key={f}>{f}</li>)}
                </ul>
              </div>

              <div>
                <p className="text-xs font-semibold text-muted-foreground mb-2">Final estimate</p>
                <div className="flex items-center gap-3 flex-wrap">
                  <Select value={String(est?.finalPoints ?? est?.studentPoints ?? '')} onValueChange={(v) => setEstimation(story.id, { finalPoints: Number(v) })}>
                    <SelectTrigger className="w-[120px]">
                      <SelectValue placeholder="SP" />
                    </SelectTrigger>
                    <SelectContent>
                      {STORY_POINT_SCALE.map((p) => (
                        <SelectItem key={p} value={String(p)}>{p} SP</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <span className="text-xs text-muted-foreground">This is what goes to the sprint board — the AI number is a reference, not the final word.</span>
                </div>
              </div>

              <div>
                <p className="text-xs font-semibold text-muted-foreground mb-1.5">Reason for your decision (optional)</p>
                <Textarea
                  value={est?.reason || ''}
                  onChange={(e) => setEstimation(story.id, { reason: e.target.value })}
                  placeholder="e.g. I kept my estimate because the API integration is already built…"
                  className="text-xs"
                />
              </div>

              <div className="flex justify-end">
                <Button size="sm" onClick={confirm} className="active:scale-[0.98]">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Confirm estimate
                </Button>
              </div>
            </>
          )}
        </div>
      )}
    </Card>
  )
}

export default function Estimation() {
  const { requirements, userStories, estimations, setEstimation } = usePlanningData()
  const [selectedReqId, setSelectedReqId] = useState(requirements[0]?.id ?? '')

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
          studentPoints: null,
          aiPoints: null,
          aiConfidence: null,
          aiFactors: null,
          aiRevealed: false,
          finalPoints: null,
          reason: '',
          confirmed: false,
        })
      }
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [acceptedStories.length])

  const estimatedCount = acceptedStories.filter(({ story }) => estimations[story.id]?.confirmed).length
  const pendingCount = acceptedStories.length - estimatedCount
  const totalStudentSP = acceptedStories.reduce((s, { story }) => s + (estimations[story.id]?.studentPoints ?? 0), 0)
  const totalAiSP = acceptedStories.reduce((s, { story }) => s + (estimations[story.id]?.aiPoints ?? 0), 0)
  const maxSP = Math.max(totalStudentSP, totalAiSP, 1)

  const requirement = requirements.find((r) => r.id === selectedReqId)
  const isEligible = requirement?.status === 'Passing'
  const reqAccepted = isEligible ? acceptedStories.filter(({ req }) => req.id === selectedReqId) : []
  const reqPending = reqAccepted.filter(({ story }) => !estimations[story.id]?.confirmed)
  const reqDone = reqAccepted.filter(({ story }) => estimations[story.id]?.confirmed)

  function getEstimationMeta(r) {
    if (r.status !== 'Passing') return { percent: 0, tone: 'neutral', locked: true }
    const accepted = (userStories[r.id] || []).filter((s) => s.status === 'Accepted')
    if (accepted.length === 0) return { percent: 0, tone: 'neutral', locked: false }
    const done = accepted.filter((s) => estimations[s.id]?.confirmed).length
    const percent = Math.round((done / accepted.length) * 100)
    return { percent, tone: percent === 100 ? 'success' : 'warning', locked: false }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Effort Estimation"
        breadcrumb={['Planning', 'Requirements', 'Effort Estimation']}
        description="Estimate each accepted user story yourself, compare against the AI's estimate, and confirm the final number that goes to Sprint Management."
      />

      <WorkflowStepper current="effort" />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Overview</p>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between"><span className="text-muted-foreground">Total stories</span><span className="font-medium text-foreground">{acceptedStories.length}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Estimated</span><span className="font-medium text-foreground">{estimatedCount}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Remaining</span><span className="font-medium text-foreground">{pendingCount}</span></div>
          </div>
        </Card>

        <Card className="lg:col-span-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Student vs. AI</p>
          <p className="text-[11px] text-muted-foreground mb-3">The AI estimate is a reference point, not the authority — you decide the final number.</p>
          <div className="space-y-2.5">
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground w-16 shrink-0">Student</span>
              <div className="flex-1 h-3 rounded-full bg-muted overflow-hidden">
                <div className="h-full bg-foreground rounded-full transition-all" style={{ width: `${(totalStudentSP / maxSP) * 100}%` }} />
              </div>
              <span className="text-xs font-semibold text-foreground w-16 text-right shrink-0">{totalStudentSP} SP</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground w-16 shrink-0">AI</span>
              <div className="flex-1 h-3 rounded-full bg-muted overflow-hidden">
                <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${(totalAiSP / maxSP) * 100}%` }} />
              </div>
              <span className="text-xs font-semibold text-primary w-16 text-right shrink-0">{totalAiSP} SP</span>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[280px_1fr] gap-5 items-start">
        {/* Column 1 — Requirements */}
        <RequirementListPanel
          requirements={requirements}
          selectedId={selectedReqId}
          onSelect={setSelectedReqId}
          getItemMeta={getEstimationMeta}
        />

        {/* Column 2 — Selected requirement's stories */}
        <div className="space-y-4">
          {requirement && !isEligible && (
            <EmptyState
              icon={Lock}
              title={`${requirement.id} is blocked`}
              description={`This requirement hasn't passed SRS Quality yet (${requirement.overallScore}%). It must clear the quality gate — and be decomposed — before it can be estimated.`}
              actionLabel="Go to SRS Quality"
              onAction={() => { window.location.href = '/planning/requirements/srs-quality' }}
            />
          )}

          {requirement && isEligible && reqAccepted.length === 0 && (
            <EmptyState
              icon={Sparkles}
              title="Nothing to estimate yet"
              description={`No accepted user stories for ${requirement.id} yet. Accept a story in Decomposition first.`}
              actionLabel="Go to Decomposition"
              onAction={() => { window.location.href = '/planning/requirements/decomposition' }}
            />
          )}

          {requirement && isEligible && reqAccepted.length > 0 && (
            <>
              <Card className="p-4 flex items-center justify-between gap-3 flex-wrap">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">{requirement.id}</p>
                  <h3 className="text-sm font-semibold text-foreground">{requirement.title}</h3>
                </div>
                <Link to="/planning/sprint-management" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline shrink-0">
                  Go to Sprint Management <ArrowRight className="h-3 w-3" />
                </Link>
              </Card>

              {reqPending.length > 0 && (
                <div className="space-y-3">
                  {reqPending.map(({ req, story }) => (
                    <StoryRow key={story.id} req={req} story={story} />
                  ))}
                </div>
              )}

              {reqDone.length > 0 && (
                <Card>
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Already estimated</p>
                  <ul className="space-y-1.5">
                    {reqDone.map(({ story }) => (
                      <li key={story.id} className="flex items-center justify-between text-sm">
                        <span className="text-foreground truncate">{story.title}</span>
                        <Badge tone="success">{estimations[story.id]?.finalPoints} SP</Badge>
                      </li>
                    ))}
                  </ul>
                </Card>
              )}
            </>
          )}
        </div>
      </div>

      <DartButton context="effort" />
    </div>
  )
}
