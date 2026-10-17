import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  ChevronDown,
  CheckCircle2,
  Lock,
  ArrowRight,
  Gauge,
  GraduationCap,
  BookOpen,
  UserCheck,
  Check,
  KanbanSquare,
  Sparkles,
} from 'lucide-react'
import { useTeamPath } from '@/shared/hooks/useTeamPath.js'
import Card from '../../../../../shared/components/Card.jsx'
import Badge from '../../../../../shared/components/Badge.jsx'
import EmptyState from '../../../../../shared/components/EmptyState.jsx'
import AvatarComp from '../../../../../shared/components/Avatar.jsx'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import WorkflowStepper from '../../../components/WorkflowStepper.jsx'
import DartButton from '../../../components/DartButton.jsx'
import RequirementListPanel from '../../../components/RequirementListPanel.jsx'
import SupervisorConsultationModal from '../../../components/SupervisorConsultationModal.jsx'
import { usePlanningData } from '../../../context/usePlanningData.js'
import { useStories, useTaskValidation } from '../../../hooks/useDecomposition.js'
import { useEstimates, useSaveEstimate, useConfirmEstimate } from '../../../hooks/useEstimates.js'
import { mapStoryRows, mapTaskValidationResult } from '../../../adapters/decomposition.js'
import { STORY_POINT_SCALE } from '../../../data/mockData.js'
import { COURSE_INFO } from '../../../data/lmsAcademicData.js'
import { showToast } from '@/shared/utils/toast.jsx'

const TASK_READINESS_TONE = {
  Valid: 'success',
  'Needs Improvement': 'warning',
  'Coverage Warning': 'primary',
}

function StoryRow({ req, story }) {
  const { estimations, setEstimation, confirmEstimation, getTaskValidationEvaluation, recordTaskValidation } =
    usePlanningData()
  const saveEstimate = useSaveEstimate()
  const confirmEstimateMut = useConfirmEstimate()
  const [expanded, setExpanded] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const est = estimations[story.id]
  const taskEvaluation = getTaskValidationEvaluation(story.id)

  // Display-only hydration: fetches the story's latest stored task
  // validation if the student navigated here without visiting Decomposition
  // first in this session (and nothing is cached in local storage yet).
  const taskValidationQuery = useTaskValidation(story.id, (story.tasks || []).length > 0 && !taskEvaluation)
  useEffect(() => {
    if (!taskValidationQuery.data?.assessment) return
    const mapped = mapTaskValidationResult(taskValidationQuery.data)
    if (mapped) recordTaskValidation(story.id, mapped)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskValidationQuery.data])

  async function confirm() {
    const finalPoints = est?.finalPoints ?? est?.studentPoints ?? 3
    setConfirming(true)
    try {
      await saveEstimate.mutateAsync({
        story_ref: story.id,
        estimated_story_points: finalPoints,
        estimation_basis: est?.reason || '',
      })

      await confirmEstimateMut.mutateAsync(story.id)

      confirmEstimation(req.id, story.id, story.title, finalPoints, est?.reason)
      showToast.success('Effort confirmed', { description: `${story.id} is now on the Sprint Board at ${finalPoints} SP.` })
    } catch {
      showToast.error('Failed to confirm estimation')
    } finally {
      setConfirming(false)
    }
  }

  return (
    <Card className="p-0 overflow-hidden">
      <button type="button" onClick={() => setExpanded((v) => !v)} className="w-full flex items-center justify-between gap-3 p-4 text-left cursor-pointer hover:bg-muted/30 transition-colors">
        <div className="min-w-0 flex-1">
          <p className="text-sm text-foreground truncate">{story.title}</p>
          <div className="flex items-center gap-1.5 flex-wrap mt-0.5">
            <p className="text-xs text-muted-foreground">{story.id} · {req.id} · {(story.tasks || []).length} task(s)</p>
            {taskEvaluation && !taskEvaluation.analysisFailed && !taskEvaluation.malformed && (
              <Badge
                tone={TASK_READINESS_TONE[taskEvaluation.readiness] || 'neutral'}
                className="text-[9px] px-1.5 py-0"
                title={taskEvaluation.readinessReason}
              >
                Tasks: {taskEvaluation.readiness}
              </Badge>
            )}
          </div>
        </div>
        <div className="flex items-center gap-4 shrink-0">
          <div className="text-center">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Points</p>
            <p className="text-sm font-semibold text-foreground">{est?.confirmed ? `${est.finalPoints} SP` : est?.studentPoints ? `${est.studentPoints} SP` : '—'}</p>
          </div>
          {est?.confirmed && (
            <Badge tone="success">Confirmed</Badge>
          )}
          <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {expanded && !est?.confirmed && (
        <div className="px-4 pb-4 space-y-4 animate-fade-rise">
          <div className="p-3 rounded-lg border border-border">
            <p className="text-xs font-semibold text-muted-foreground mb-2">Assign story points</p>
            <Select
              value={String(est?.studentPoints ?? '')}
              onValueChange={(v) => setEstimation(story.id, { studentPoints: Number(v), finalPoints: Number(v) })}
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

          <div>
            <p className="text-xs font-semibold text-muted-foreground mb-1.5">Reason (optional)</p>
            <Textarea
              value={est?.reason || ''}
              onChange={(e) => setEstimation(story.id, { reason: e.target.value })}
              placeholder="e.g. Complex API integration with multiple dependencies…"
              className="text-xs"
            />
          </div>

          {(story.tasks || []).length > 0 && (
            <div className="p-3 rounded-lg border border-border bg-muted/20">
              <p className="text-xs font-semibold text-muted-foreground mb-2">Tasks breakdown</p>
              <ul className="text-[11px] text-muted-foreground space-y-1 list-disc list-inside">
                {story.tasks.map((t) => (
                  <li key={t.id}>{t.title} ({(t.subtasks || []).length} subtask{(t.subtasks || []).length === 1 ? '' : 's'})</li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex justify-end">
            <Button size="sm" onClick={confirm} disabled={est?.studentPoints == null || confirming} className="active:scale-[0.98]">
              <CheckCircle2 className="h-3.5 w-3.5" />
              {confirming ? 'Confirming…' : 'Confirm & send to Sprint Board'}
            </Button>
          </div>
        </div>
      )}

      {expanded && est?.confirmed && (
        <div className="px-4 pb-4 animate-fade-rise">
          <div className="p-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5">
            <div className="flex items-center gap-2 mb-1">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
              <p className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">Estimation confirmed — {est.finalPoints} SP</p>
            </div>
            {est.reason && <p className="text-[11px] text-muted-foreground">{est.reason}</p>}
          </div>
        </div>
      )}
    </Card>
  )
}

export default function Estimation() {
  const { requirements, userStories, estimations, setEstimation, loadStories, loadEstimations } = usePlanningData()
  const [searchParams] = useSearchParams()
  const reqParam = searchParams.get('req')

  // Sort requirements: finalized decompositions first, then passing SRS, then others
  const sortedRequirements = [...requirements].sort((a, b) => {
    const aFinal = a.decompFinalized ? 1 : 0
    const bFinal = b.decompFinalized ? 1 : 0
    if (aFinal !== bFinal) return bFinal - aFinal
    const aPassing = a.status === 'Passing' ? 1 : 0
    const bPassing = b.status === 'Passing' ? 1 : 0
    return bPassing - aPassing
  })

  const eligibleReqs = sortedRequirements.filter(
    (r) => r.decompFinalized || (r.status === 'Passing' && (userStories[r.id] || []).some((s) => s.status === 'Accepted'))
  )
  const defaultReqId = (reqParam && requirements.some((r) => r.id === reqParam))
    ? reqParam
    : (eligibleReqs[0]?.id || sortedRequirements[0]?.id || '')

  const [userSelectedReqId, setUserSelectedReqId] = useState(null)
  const selectedReqId = userSelectedReqId || defaultReqId
  const { data: storiesResp } = useStories()
  const { data: estimatesResp } = useEstimates()

  useEffect(() => {
    const stories = storiesResp?.data?.stories || storiesResp?.stories
    if (!stories) return
    const mapped = mapStoryRows(stories)
    loadStories(mapped)
  }, [storiesResp]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const rows = estimatesResp?.data?.estimates || estimatesResp?.estimates
    if (!rows || rows.length === 0) return
    const estMap = {}
    for (const row of rows) {
      const storyRef = row.story_ref || row.user_story_id
      if (!storyRef) continue
      estMap[storyRef] = {
        studentPoints: row.estimated_story_points ?? row.studentPoints ?? null,
        finalPoints: row.final_story_points ?? row.finalPoints ?? row.estimated_story_points ?? null,
        reason: row.estimation_basis ?? row.reason ?? '',
        confirmed: row.confirmed ?? false,
      }
    }
    if (Object.keys(estMap).length > 0) loadEstimations(estMap)
  }, [estimatesResp]) // eslint-disable-line react-hooks/exhaustive-deps

  const acceptedStories = []
  for (const req of requirements) {
    for (const story of userStories[req.id] || []) {
      if (story.status === 'accepted' || story.status === 'Accepted') acceptedStories.push({ req, story })
    }
  }

  useEffect(() => {
    acceptedStories.forEach(({ story }) => {
      if (!estimations[story.id]) {
        setEstimation(story.id, {
          studentPoints: null,
          finalPoints: null,
          reason: '',
          confirmed: false,
        })
      }
    })
  }, [acceptedStories.length]) // eslint-disable-line react-hooks/exhaustive-deps

  const estimatedCount = acceptedStories.filter(({ story }) => estimations[story.id]?.confirmed).length
  const pendingCount = acceptedStories.length - estimatedCount
  const totalSP = acceptedStories.reduce((s, { story }) => s + (estimations[story.id]?.finalPoints ?? 0), 0)

  const requirement = requirements.find((r) => r.id === selectedReqId)
  const isEligible = requirement?.status === 'Passing'
  const reqAccepted = isEligible ? acceptedStories.filter(({ req }) => req.id === selectedReqId) : []
  const reqPending = reqAccepted.filter(({ story }) => !estimations[story.id]?.confirmed)
  const reqDone = reqAccepted.filter(({ story }) => estimations[story.id]?.confirmed)

  const [consultOpen, setConsultOpen] = useState(false)
  const [guideOpen, setGuideOpen] = useState(false)
  const navigate = useNavigate()
  const team = useTeamPath()

  const estimationProgressPercent = acceptedStories.length
    ? Math.round((estimatedCount / acceptedStories.length) * 100)
    : 0

  function getEstimationMeta(r) {
    if (r.status !== 'Passing') return { percent: 0, tone: 'neutral', locked: true }
    const accepted = (userStories[r.id] || []).filter(
      (s) => s.status === 'accepted' || s.status === 'Accepted',
    )
    if (!r.decompFinalized && accepted.length === 0) {
      return { percent: 0, tone: 'neutral', locked: true }
    }
    if (accepted.length === 0) return { percent: 0, tone: 'neutral', locked: false }
    const done = accepted.filter((s) => estimations[s.id]?.confirmed).length
    const percent = Math.round((done / accepted.length) * 100)
    return { percent, tone: percent === 100 ? 'success' : 'warning', locked: false }
  }

  return (
    <div className="space-y-6 pb-12">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-border">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <GraduationCap className="h-3.5 w-3.5 text-primary" />
            <span>{COURSE_INFO.courseCode} · {COURSE_INFO.courseName}</span>
            <span className="text-border">/</span>
            <span className="text-foreground">Milestone M3</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            Effort Estimation &amp; Story Point Sizing
            <Badge tone="primary" className="text-xs font-medium">
              Scale: 1 to 21 SP
            </Badge>
          </h1>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setGuideOpen(true)}
            className="text-xs cursor-pointer gap-1.5"
          >
            <BookOpen className="h-3.5 w-3.5 text-primary" /> Fibonacci Sizing Guide
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setConsultOpen(true)}
            className="text-xs cursor-pointer gap-1.5"
          >
            <UserCheck className="h-3.5 w-3.5 text-primary" /> Supervisor Advisory
          </Button>
          <Button
            size="sm"
            onClick={() => navigate(team('/planning/sprint-management'))}
            className="text-xs cursor-pointer gap-1.5"
          >
            <KanbanSquare className="h-3.5 w-3.5" /> Sprint Board
          </Button>
        </div>
      </div>

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
              <span>Protocol: <strong className="text-foreground">Manual Story Point Assignment</strong></span>
            </div>

            <h2 className="text-lg sm:text-xl font-semibold text-foreground tracking-tight">
              Effort Estimation Studio
            </h2>

            <p className="text-xs text-muted-foreground leading-relaxed">
              Assign story points to accepted user stories using the Fibonacci scale. Confirmed stories flow directly to the Sprint Board for execution tracking.
            </p>

            <div className="flex items-center gap-4 flex-wrap pt-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5 font-medium text-foreground">
                <AvatarComp name={COURSE_INFO.supervisor.name} size={20} className="ring-1 ring-border" />
                Supervisor: {COURSE_INFO.supervisor.name}
              </span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span className="flex items-center gap-1.5">
                <Gauge className="h-3.5 w-3.5 text-primary" />
                {estimatedCount} of {acceptedStories.length} Stories Sized
              </span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span className="flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5 text-primary" />
                {totalSP} Story Points Assigned
              </span>
            </div>
          </div>

          <div className="flex flex-col items-center justify-center shrink-0 self-center sm:self-center px-3 py-1">
            <div className="relative flex items-center justify-center" style={{ width: 92, height: 92 }}>
              <svg className="w-full h-full -rotate-90 transform" viewBox="0 0 92 92">
                <circle cx="46" cy="46" r="38" className="stroke-muted" strokeWidth="7" fill="transparent" />
                <circle
                  cx="46" cy="46" r="38"
                  className="stroke-primary transition-all duration-700 ease-out"
                  strokeWidth="7"
                  strokeDasharray={2 * Math.PI * 38}
                  strokeDashoffset={(2 * Math.PI * 38) * (1 - estimationProgressPercent / 100)}
                  strokeLinecap="round"
                  fill="transparent"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-xl font-bold tracking-tight text-foreground">{estimationProgressPercent}%</span>
              </div>
            </div>
            <span className="text-xs font-semibold text-muted-foreground mt-1.5">Stories Sized</span>
          </div>
        </div>
      </Card>

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
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Story Point Summary</p>
          <p className="text-[11px] text-muted-foreground mb-3">Total effort committed to the sprint backlog so far.</p>
          <div className="flex items-center gap-3">
            <span className="text-xs text-muted-foreground w-16 shrink-0">Total</span>
            <div className="flex-1 h-3 rounded-full bg-muted overflow-hidden">
              <div className="h-full bg-primary rounded-full transition-all" style={{ width: `${Math.min(100, (totalSP / Math.max(totalSP, 40)) * 100)}%` }} />
            </div>
            <span className="text-xs font-semibold text-foreground w-16 text-right shrink-0">{totalSP} SP</span>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[280px_1fr] gap-5 items-start">
        <RequirementListPanel
          requirements={sortedRequirements}
          selectedId={selectedReqId}
          onSelect={setUserSelectedReqId}
          getItemMeta={getEstimationMeta}
        />

        <div className="space-y-4">
          {requirement && !isEligible && (
            <EmptyState
              icon={Lock}
              title={`${requirement.id} is blocked`}
              description={`This requirement hasn't passed SRS Quality yet (${requirement.overallScore}%). It must clear the SRS quality gate and be decomposed before it can be estimated.`}
              actionLabel="Go to SRS Quality"
              onAction={() => navigate(team(`/planning/requirements/srs-quality?req=${requirement.id}`))}
            />
          )}

          {requirement && isEligible && reqAccepted.length === 0 && (
            <EmptyState
              icon={Sparkles}
              title="Nothing to estimate yet"
              description={`No accepted user stories for ${requirement.id} yet. Clear the Decomposition Quality Gate and finalize decomposition first.`}
              actionLabel="Go to Decomposition"
              onAction={() => navigate(team(`/planning/requirements/decomposition?req=${requirement.id}`))}
            />
          )}

          {requirement && isEligible && reqAccepted.length > 0 && (
            <>
              <Card className="p-4 flex items-center justify-between gap-3 flex-wrap">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">{requirement.id}</p>
                  <h3 className="text-sm font-semibold text-foreground">{requirement.title}</h3>
                </div>
                <Link to={team('/planning/sprint-management')} className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline shrink-0">
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

      <SupervisorConsultationModal
        open={consultOpen}
        onOpenChange={setConsultOpen}
        requirements={requirements}
      />

      <Dialog open={guideOpen} onOpenChange={setGuideOpen}>
        <DialogContent className="sm:max-w-[620px] max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center gap-2 mb-1">
              <span className="p-1 rounded bg-primary/10 text-primary">
                <BookOpen className="h-4 w-4" />
              </span>
              <DialogTitle className="text-lg font-bold">Agile Story Point Estimation &amp; Fibonacci Scale</DialogTitle>
            </div>
            <DialogDescription className="text-xs">
              Academic principles for sizing software work units.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3.5 text-xs">
            <div className="p-3.5 rounded-xl border border-border bg-card space-y-1">
              <h4 className="font-bold text-foreground text-xs flex items-center gap-1.5">
                <Check className="h-3.5 w-3.5 text-primary" /> Relative Sizing over Absolute Hours
              </h4>
              <p className="text-muted-foreground text-[11px] leading-relaxed">
                Story points quantify combined effort, technical complexity, risk, and unknowns relative to a small reference baseline. Never treat 1 SP as a fixed number of hours.
              </p>
            </div>

            <div className="p-3.5 rounded-xl border border-border bg-card space-y-2">
              <h4 className="font-bold text-foreground text-xs flex items-center gap-1.5">
                <Check className="h-3.5 w-3.5 text-primary" /> Modified Fibonacci Reference Scale
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                <div className="p-2 rounded bg-muted/40 border border-border/50">
                  <span className="font-bold text-primary block">1 – 2 SP</span>
                  <span className="text-muted-foreground">Trivial task, well-understood implementation.</span>
                </div>
                <div className="p-2 rounded bg-muted/40 border border-border/50">
                  <span className="font-bold text-primary block">3 – 5 SP</span>
                  <span className="text-muted-foreground">Standard feature with minor dependencies.</span>
                </div>
                <div className="p-2 rounded bg-muted/40 border border-border/50">
                  <span className="font-bold text-primary block">8 SP</span>
                  <span className="text-muted-foreground">Substantial scope, cross-module integration.</span>
                </div>
                <div className="p-2 rounded bg-muted/40 border border-border/50">
                  <span className="font-bold text-destructive block">13 – 21 SP</span>
                  <span className="text-muted-foreground">Epic size: Must be decomposed before sprint.</span>
                </div>
              </div>
            </div>
          </div>

          <DialogFooter className="pt-2">
            <Button size="sm" onClick={() => setGuideOpen(false)} className="text-xs cursor-pointer">
              Understood
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
