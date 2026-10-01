import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ChevronDown,
  CheckCircle2,
  Sparkles,
  Lock,
  ArrowRight,
  Gauge,
  GraduationCap,
  BookOpen,
  UserCheck,
  Check,
  FileText,
  KanbanSquare,
} from 'lucide-react'
import PageHeader from '../../../../../shared/components/PageHeader.jsx'
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
import { STORY_POINT_SCALE } from '../../../data/mockData.js'
import { COURSE_INFO } from '../../../data/lmsAcademicData.js'
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

  const [consultOpen, setConsultOpen] = useState(false)
  const [guideOpen, setGuideOpen] = useState(false)
  const navigate = useNavigate()

  const estimationProgressPercent = acceptedStories.length
    ? Math.round((estimatedCount / acceptedStories.length) * 100)
    : 0

  function getEstimationMeta(r) {
    if (r.status !== 'Passing') return { percent: 0, tone: 'neutral', locked: true }
    const accepted = (userStories[r.id] || []).filter((s) => s.status === 'Accepted')
    if (accepted.length === 0) return { percent: 0, tone: 'neutral', locked: false }
    const done = accepted.filter((s) => estimations[s.id]?.confirmed).length
    const percent = Math.round((done / accepted.length) * 100)
    return { percent, tone: percent === 100 ? 'success' : 'warning', locked: false }
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Top Academic Breadcrumb Header */}
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

        {/* Action Toolbar */}
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
            onClick={() => navigate('/planning/sprint-management')}
            className="text-xs cursor-pointer gap-1.5"
          >
            <KanbanSquare className="h-3.5 w-3.5" /> Sprint Board
          </Button>
        </div>
      </div>

      {/* LMS Project Banner Card with Round Progress Bar (no left border) */}
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
              <span>Protocol: <strong className="text-foreground">Consensus Planning Poker</strong></span>
            </div>

            <h2 className="text-xl sm:text-2xl font-bold text-foreground tracking-tight">
              Consensus-Based Effort Estimation Studio
            </h2>

            <p className="text-xs text-muted-foreground leading-relaxed">
              Estimate each accepted user story yourself before revealing the AI agent reference point. This double-blind protocol prevents cognitive anchoring bias and builds calibrated engineering judgment.
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
                {totalStudentSP} Story Points Assigned
              </span>
            </div>
          </div>

          {/* Round Progress Bar with Percentage in Middle */}
          <div className="flex flex-col items-center justify-center shrink-0 self-center sm:self-center px-3 py-1">
            <div className="relative flex items-center justify-center" style={{ width: 92, height: 92 }}>
              <svg className="w-full h-full -rotate-90 transform" viewBox="0 0 92 92">
                <circle
                  cx="46"
                  cy="46"
                  r="38"
                  className="stroke-muted"
                  strokeWidth="7"
                  fill="transparent"
                />
                <circle
                  cx="46"
                  cy="46"
                  r="38"
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

      {/* Supervisor Consultation Modal */}
      <SupervisorConsultationModal
        open={consultOpen}
        onOpenChange={setConsultOpen}
        requirements={requirements}
      />

      {/* Fibonacci Sizing Guide Dialog */}
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
              Academic principles for sizing software work units and mitigating estimation bias.
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

            <div className="p-3.5 rounded-xl border border-amber-500/25 bg-amber-500/5 space-y-1 text-xs">
              <h4 className="font-bold text-amber-700 dark:text-amber-300 flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5" /> Preventing Cognitive Anchoring Bias
              </h4>
              <p className="text-muted-foreground text-[11px] leading-relaxed">
                Students must submit their own point estimate first. Seeing an AI or peer estimate beforehand anchors human judgment and degrades pedagogical estimation accuracy.
              </p>
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
