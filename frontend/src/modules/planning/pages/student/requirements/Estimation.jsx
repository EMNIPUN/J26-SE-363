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
  CheckSquare,
  ListTodo,
  Pencil,
  Save,
  Clock,
  RotateCcw,
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

const FIBONACCI_SCALE = STORY_POINT_SCALE || [1, 2, 3, 5, 8, 13]

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

  const est = estimations[story.id]
  const savedPoints = est?.finalPoints ?? est?.studentPoints ?? story.student_story_points ?? null
  const savedReason = est?.reason ?? ''
  const isEstimated = savedPoints != null
  const isConfirmed = Boolean(est?.confirmed)

  const [expanded, setExpanded] = useState(!isEstimated)
  const [selectedPoints, setSelectedPoints] = useState(savedPoints)
  const [reason, setReason] = useState(savedReason)
  const [isEditing, setIsEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [confirming, setConfirming] = useState(false)

  const taskEvaluation = getTaskValidationEvaluation(story.id)

  // Sync state if persisted points change from backend
  useEffect(() => {
    if (savedPoints != null && selectedPoints == null) {
      setSelectedPoints(savedPoints)
    }
    if (savedReason && !reason) {
      setReason(savedReason)
    }
  }, [savedPoints, savedReason]) // eslint-disable-line react-hooks/exhaustive-deps

  // Hydrate task validation if needed
  const taskValidationQuery = useTaskValidation(story.id, (story.tasks || []).length > 0 && !taskEvaluation)
  useEffect(() => {
    if (!taskValidationQuery.data?.assessment) return
    const mapped = mapTaskValidationResult(taskValidationQuery.data)
    if (mapped) recordTaskValidation(story.id, mapped)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskValidationQuery.data])

  // Normalize acceptance criteria
  const rawCriteria = story.acceptanceCriteria || story.acceptance_criteria || []
  const criteriaList = Array.isArray(rawCriteria)
    ? rawCriteria.map((c) => (typeof c === 'string' ? c : c?.text || c?.criterion || JSON.stringify(c))).filter(Boolean)
    : typeof rawCriteria === 'string' && rawCriteria.trim()
    ? rawCriteria.split('\n').map((s) => s.trim()).filter(Boolean)
    : []

  const taskList = story.tasks || []

  async function handleSave() {
    if (selectedPoints == null) {
      showToast.error('Please select a story point estimate (1, 2, 3, 5, 8, or 13).')
      return
    }
    setSaving(true)
    try {
      await saveEstimate.mutateAsync({
        story_ref: story.id,
        story_points: Number(selectedPoints),
        basis: reason || '',
      })
      setEstimation(story.id, {
        studentPoints: Number(selectedPoints),
        finalPoints: Number(selectedPoints),
        reason: reason || '',
        confirmed: isConfirmed,
      })
      setIsEditing(false)
      showToast.success(isEstimated ? 'Estimate updated' : 'Estimate saved', {
        description: `${story.id} saved at ${selectedPoints} SP. Eligible for Sprint Creation & Jira Backlog.`,
      })
    } catch (err) {
      showToast.error('Failed to save estimate', {
        description: err?.response?.data?.detail || err?.message || 'Server error',
      })
    } finally {
      setSaving(false)
    }
  }

  async function handleConfirm() {
    const finalPoints = selectedPoints ?? savedPoints ?? 3
    setConfirming(true)
    try {
      await saveEstimate.mutateAsync({
        story_ref: story.id,
        story_points: Number(finalPoints),
        basis: reason || '',
      })
      await confirmEstimateMut.mutateAsync(story.id)
      confirmEstimation(req.id, story.id, story.title, Number(finalPoints), reason)
      setIsEditing(false)
      showToast.success('Effort confirmed', {
        description: `${story.id} confirmed at ${finalPoints} SP. Ready for Jira Backlog & Sprint Planning.`,
      })
    } catch (err) {
      showToast.error('Failed to confirm estimation', {
        description: err?.response?.data?.detail || err?.message || 'Server error',
      })
    } finally {
      setConfirming(false)
    }
  }

  return (
    <Card className={`w-full min-w-0 p-0 overflow-hidden border transition-all ${isEstimated ? 'border-l-4 border-l-emerald-500' : 'border-l-4 border-l-amber-500'}`}>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between gap-3 p-4 text-left cursor-pointer hover:bg-muted/30 transition-colors"
      >
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span className="font-mono text-xs font-bold text-primary">{story.id}</span>
            <span className="text-xs text-muted-foreground">·</span>
            <span className="text-xs text-muted-foreground font-medium">{req.id}</span>
            <span className="text-xs text-muted-foreground">·</span>
            <span className="text-xs text-muted-foreground">{taskList.length} task(s)</span>
            <span className="text-xs text-muted-foreground">·</span>
            <span className="text-xs text-muted-foreground">{criteriaList.length} criteria</span>
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
          <p className="text-sm font-semibold text-foreground truncate">{story.title}</p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <div className="text-right">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Points</p>
            <p className="text-sm font-bold text-foreground">
              {savedPoints != null ? `${savedPoints} SP` : '—'}
            </p>
          </div>
          {isEstimated ? (
            <Badge tone="success" className="gap-1 text-xs">
              <CheckCircle2 className="h-3 w-3" /> Estimated
            </Badge>
          ) : (
            <Badge tone="warning" className="gap-1 text-xs">
              <Clock className="h-3 w-3" /> Pending
            </Badge>
          )}
          {isConfirmed && (
            <Badge tone="primary" className="text-xs">
              Confirmed
            </Badge>
          )}
          <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${expanded ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-4 animate-fade-rise border-t border-border/40 pt-3">
          {/* User Story Statement */}
          <div className="p-3 rounded-lg border border-border bg-muted/20 space-y-1">
            <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">User Story Statement</p>
            {story.as_a || story.i_want ? (
              <p className="text-xs text-foreground font-medium leading-relaxed">
                <span className="text-primary font-bold">As a</span> {story.as_a || 'user'},{' '}
                <span className="text-primary font-bold">I want</span> {story.i_want || story.title}
                {story.so_that ? (
                  <>
                    , <span className="text-primary font-bold">so that</span> {story.so_that}
                  </>
                ) : null}.
              </p>
            ) : (
              <p className="text-xs text-foreground font-medium leading-relaxed">
                {story.description || story.title}
              </p>
            )}
            {story.description && story.description !== story.title && (story.as_a || story.i_want) && (
              <p className="text-[11px] text-muted-foreground pt-1 border-t border-border/40 mt-1.5">{story.description}</p>
            )}
          </div>

          {/* Acceptance Criteria Breakdown */}
          <div className="p-3 rounded-lg border border-border bg-muted/15 space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <CheckSquare className="h-3.5 w-3.5 text-primary" /> Acceptance Criteria
              </p>
              <Badge tone="neutral" className="text-[10px]">{criteriaList.length} criteria</Badge>
            </div>
            {criteriaList.length > 0 ? (
              <ul className="space-y-1.5 text-xs text-muted-foreground">
                {criteriaList.map((criterion, idx) => (
                  <li key={idx} className="flex items-start gap-2 bg-background/70 p-2 rounded border border-border/50">
                    <span className="text-[10px] font-mono font-bold text-primary px-1.5 py-0.5 rounded bg-primary/10 shrink-0 mt-0.5">AC-{idx + 1}</span>
                    <span className="min-w-0 break-words text-foreground/90 leading-snug">{criterion}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-muted-foreground italic">No acceptance criteria defined for this story.</p>
            )}
          </div>

          {/* Implementation Tasks Breakdown */}
          <div className="p-3 rounded-lg border border-border bg-muted/15 space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <ListTodo className="h-3.5 w-3.5 text-primary" /> Implementation Tasks
              </p>
              <Badge tone="neutral" className="text-[10px]">{taskList.length} task(s)</Badge>
            </div>
            {taskList.length > 0 ? (
              <div className="space-y-1.5 text-xs">
                {taskList.map((task) => (
                  <div key={task.id} className="flex items-center justify-between p-2 rounded bg-background/70 border border-border/50 text-foreground/90 flex-wrap gap-2">
                    <div className="flex items-center gap-2 truncate">
                      <span className="font-mono text-[10px] font-semibold text-muted-foreground">{task.id}</span>
                      <span className="truncate">{task.title}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-[10px] text-muted-foreground">
                        {(task.subtasks || []).length} subtask{(task.subtasks || []).length === 1 ? '' : 's'}
                      </span>
                      <Badge tone={task.status === 'done' ? 'success' : 'neutral'} className="text-[9px] uppercase px-1.5 py-0">
                        {task.status || 'todo'}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground italic">No implementation tasks decomposed yet.</p>
            )}
          </div>

          {/* Effort Estimation Panel */}
          {isEstimated && !isEditing ? (
            <div className="p-3.5 rounded-lg border border-emerald-500/30 bg-emerald-500/5 space-y-2.5">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div className="flex items-center gap-2.5">
                  <span className="p-1 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="h-4 w-4" />
                  </span>
                  <div>
                    <p className="text-xs font-semibold text-emerald-700 dark:text-emerald-300">
                      Saved Estimate: <span className="text-sm font-bold">{savedPoints} Story Points</span>
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      Persisted in database · Eligible for Sprint Creation Backlog
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedPoints(savedPoints)
                      setReason(savedReason)
                      setIsEditing(true)
                    }}
                    className="text-xs h-8 cursor-pointer"
                  >
                    <Pencil className="h-3 w-3 mr-1" /> Edit Estimate
                  </Button>
                  {!isConfirmed && (
                    <Button
                      size="sm"
                      onClick={handleConfirm}
                      disabled={confirming}
                      className="text-xs h-8 cursor-pointer"
                    >
                      <KanbanSquare className="h-3 w-3 mr-1" />
                      {confirming ? 'Confirming…' : 'Confirm to Sprint'}
                    </Button>
                  )}
                </div>
              </div>
              {savedReason && (
                <div className="pt-2 border-t border-emerald-500/20 text-xs">
                  <span className="text-muted-foreground font-medium">Estimation basis / reasoning: </span>
                  <span className="text-foreground">{savedReason}</span>
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 rounded-lg border border-border bg-card space-y-3.5 shadow-xs">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs font-semibold text-foreground">
                    {isEstimated ? 'Update Story Point Estimate' : 'Assign Fibonacci Story Points'}
                  </p>
                  <p className="text-[11px] text-muted-foreground">
                    Allowed Fibonacci scale: 1, 2, 3, 5, 8, 13
                  </p>
                </div>
                {isEditing && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => {
                      setSelectedPoints(savedPoints)
                      setReason(savedReason)
                      setIsEditing(false)
                    }}
                    className="text-xs h-7 cursor-pointer"
                  >
                    <RotateCcw className="h-3 w-3 mr-1" /> Cancel
                  </Button>
                )}
              </div>

              {/* Fibonacci Quick Buttons */}
              <div>
                <p className="text-xs font-semibold text-muted-foreground mb-2">Select Story Points</p>
                <div className="flex items-center gap-2 flex-wrap">
                  {FIBONACCI_SCALE.map((p) => {
                    const isSel = selectedPoints === p
                    return (
                      <button
                        key={p}
                        type="button"
                        onClick={() => {
                          setSelectedPoints(p)
                          setEstimation(story.id, { studentPoints: p, finalPoints: p })
                        }}
                        className={`px-3.5 py-1.5 rounded-md text-xs font-bold transition-all cursor-pointer ${
                          isSel
                            ? 'bg-primary text-primary-foreground shadow-sm ring-2 ring-primary ring-offset-1 scale-105'
                            : 'bg-muted/70 hover:bg-muted text-foreground border border-border/80'
                        }`}
                      >
                        {p} SP
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Dropdown alternative */}
              <div className="pt-1">
                <Select
                  value={selectedPoints != null ? String(selectedPoints) : ''}
                  onValueChange={(v) => {
                    const val = Number(v)
                    setSelectedPoints(val)
                    setEstimation(story.id, { studentPoints: val, finalPoints: val })
                  }}
                >
                  <SelectTrigger className="w-full text-xs">
                    <SelectValue placeholder="Or choose story points from dropdown" />
                  </SelectTrigger>
                  <SelectContent>
                    {FIBONACCI_SCALE.map((p) => (
                      <SelectItem key={p} value={String(p)}>{p} SP</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <p className="text-xs font-semibold text-muted-foreground mb-1.5">Estimation Basis / Reasoning (optional)</p>
                <Textarea
                  value={reason}
                  onChange={(e) => {
                    setReason(e.target.value)
                    setEstimation(story.id, { reason: e.target.value })
                  }}
                  placeholder="e.g. Depends on authentication API, requires database migration and automated unit tests…"
                  className="text-xs min-h-[70px]"
                />
              </div>

              <div className="flex items-center justify-between pt-1 flex-wrap gap-2">
                <span className="text-xs text-muted-foreground">
                  {selectedPoints ? (
                    <span className="font-medium text-foreground">Selected: <strong className="text-primary">{selectedPoints} SP</strong></span>
                  ) : (
                    <span className="text-amber-600 dark:text-amber-400 font-medium">Select points above to save</span>
                  )}
                </span>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    onClick={handleSave}
                    disabled={selectedPoints == null || saving}
                    className="text-xs h-8 cursor-pointer"
                  >
                    <Save className="h-3.5 w-3.5 mr-1" />
                    {saving ? 'Saving to Database…' : isEstimated ? 'Update Estimate' : 'Save Estimate'}
                  </Button>
                  {!isConfirmed && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleConfirm}
                      disabled={selectedPoints == null || confirming}
                      className="text-xs h-8 cursor-pointer"
                    >
                      <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                      {confirming ? 'Confirming…' : 'Save & Send to Sprint'}
                    </Button>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  )
}

export default function Estimation() {
  const { requirements, userStories, estimations, setEstimation, loadStories, loadEstimations } = usePlanningData()
  const [searchParams] = useSearchParams()
  const reqParam = searchParams.get('req')
  const [activeFilter, setActiveFilter] = useState('all') // 'all' | 'pending' | 'estimated'

  function isDecompComplete(r) {
    if (!r || r.status !== 'Passing') return false
    // Effort access requires the student's persisted explicit handoff from
    // decomposition; stories alone do not unlock this stage.
    return Boolean(r.effortAuthorized)
  }

  // Sort requirements: decomposition-completed requirements first, then passing SRS, then others
  const sortedRequirements = [...requirements].sort((a, b) => {
    const aComplete = isDecompComplete(a) ? 1 : 0
    const bComplete = isDecompComplete(b) ? 1 : 0
    if (aComplete !== bComplete) return bComplete - aComplete
    const aPassing = a.status === 'Passing' ? 1 : 0
    const bPassing = b.status === 'Passing' ? 1 : 0
    return bPassing - aPassing
  })

  const eligibleReqs = sortedRequirements.filter(isDecompComplete)
  const unlockedCount = eligibleReqs.length
  const defaultReqId = (reqParam && requirements.some((r) => r.id === reqParam && isDecompComplete(r)))
    ? reqParam
    : (eligibleReqs[0]?.id || sortedRequirements[0]?.id || '')

  const [userSelectedReqId, setUserSelectedReqId] = useState(null)
  const selectedReqId = userSelectedReqId || defaultReqId
  const { data: storiesResp } = useStories()
  const { data: estimatesResp } = useEstimates()

  useEffect(() => {
    const stories = storiesResp?.data?.stories || storiesResp?.stories
    if (!Array.isArray(stories)) return
    const mapped = mapStoryRows(stories)
    loadStories(mapped, { replace: true })
  }, [storiesResp]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const rows = estimatesResp?.data?.estimates || estimatesResp?.estimates
    if (!Array.isArray(rows)) return
    const estMap = {}
    for (const row of rows) {
      const storyRef = row.story_ref || row.user_story_id
      if (!storyRef) continue
      estMap[storyRef] = {
        studentPoints: row.estimated_story_points ?? row.story_points ?? null,
        finalPoints: row.final_story_points ?? row.story_points ?? row.estimated_story_points ?? null,
        reason: row.estimation_basis ?? row.reason ?? '',
        confirmed: row.confirmed ?? false,
      }
    }
    loadEstimations(estMap)
  }, [estimatesResp]) // eslint-disable-line react-hooks/exhaustive-deps

  // Collect all decomposed user stories (ignoring rejected ones)
  const allDecomposedStories = []
  for (const req of requirements) {
    for (const story of userStories[req.id] || []) {
      if (story.status !== 'rejected' && story.status !== 'Rejected') {
        allDecomposedStories.push({ req, story })
      }
    }
  }

  const isStoryEstimated = (story) => {
    const est = estimations[story.id]
    return (
      est?.studentPoints != null ||
      est?.finalPoints != null ||
      story.student_story_points != null ||
      est?.confirmed
    )
  }

  const estimatedCount = allDecomposedStories.filter(({ story }) => isStoryEstimated(story)).length
  const pendingCount = allDecomposedStories.length - estimatedCount
  const totalSP = allDecomposedStories.reduce((s, { story }) => {
    const est = estimations[story.id]
    const pts = est?.finalPoints ?? est?.studentPoints ?? story.student_story_points ?? 0
    return s + (Number(pts) || 0)
  }, 0)

  const requirement = requirements.find((r) => r.id === selectedReqId)
  const isRequirementUnlocked = isDecompComplete(requirement)
  const reqStories = isRequirementUnlocked ? allDecomposedStories.filter(({ req }) => req.id === selectedReqId) : []
  const reqPending = reqStories.filter(({ story }) => !isStoryEstimated(story))
  const reqEstimated = reqStories.filter(({ story }) => isStoryEstimated(story))

  const displayedStories =
    activeFilter === 'pending'
      ? reqPending
      : activeFilter === 'estimated'
      ? reqEstimated
      : reqStories

  const [consultOpen, setConsultOpen] = useState(false)
  const [guideOpen, setGuideOpen] = useState(false)
  const navigate = useNavigate()
  const team = useTeamPath()

  const estimationProgressPercent = allDecomposedStories.length
    ? Math.round((estimatedCount / allDecomposedStories.length) * 100)
    : 0

  function getEstimationMeta(r) {
    const isComplete = isDecompComplete(r)
    if (!isComplete) {
      return {
        percent: 0,
        tone: 'neutral',
        locked: true,
        finalized: false,
      }
    }

    const stories = (userStories[r.id] || []).filter(
      (s) => s.status !== 'rejected' && s.status !== 'Rejected',
    )
    if (stories.length === 0) {
      return { percent: 0, tone: 'neutral', locked: true, finalized: false }
    }
    const done = stories.filter((s) => isStoryEstimated(s)).length
    const percent = Math.round((done / stories.length) * 100)
    return {
      percent,
      tone: percent === 100 ? 'success' : 'warning',
      locked: false,
      finalized: Boolean(r.decompFinalized),
    }
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
              Scale: 1 to 13 SP
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
            <KanbanSquare className="h-3.5 w-3.5" /> Sprint Backlog &amp; Board
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
              <span>Protocol: <strong className="text-foreground">Manual Fibonacci Sizing (1, 2, 3, 5, 8, 13)</strong></span>
            </div>

            <h2 className="text-lg sm:text-xl font-semibold text-foreground tracking-tight">
              Effort Estimation Studio
            </h2>

            <p className="text-xs text-muted-foreground leading-relaxed">
              Assign story points to decomposed user stories using the Fibonacci scale (1, 2, 3, 5, 8, 13). Persisted estimates become immediately eligible for the Sprint Creation Backlog.
            </p>

            <div className="flex items-center gap-4 flex-wrap pt-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5 font-medium text-foreground">
                <AvatarComp name={COURSE_INFO.supervisor.name} size={20} className="ring-1 ring-border" />
                Supervisor: {COURSE_INFO.supervisor.name}
              </span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span className="flex items-center gap-1.5">
                <Gauge className="h-3.5 w-3.5 text-primary" />
                {estimatedCount} of {allDecomposedStories.length} Stories Sized
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

      {/* 2-Column Responsive Layout mirroring Decomposition Page */}
      <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] xl:grid-cols-[320px_1fr] gap-6 items-start">
        {/* Column 1 — Requirements Directory (Sticky on scroll) */}
        <div className="space-y-3 lg:sticky lg:top-4 self-start">
          <div className="flex items-center justify-between px-1">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Requirements Catalog
            </span>
            <span className="text-xs text-muted-foreground font-medium">
              {unlockedCount}/{requirements.length} Unlocked
            </span>
          </div>
          <RequirementListPanel
            requirements={sortedRequirements}
            selectedId={selectedReqId}
            onSelect={setUserSelectedReqId}
            getItemMeta={getEstimationMeta}
            maxHeight="calc(100vh - 12rem)"
          />
        </div>

        {/* Column 2 — Main Estimation Studio */}
        <div className="min-w-0 space-y-4">
          {requirement && !isRequirementUnlocked && (
            <EmptyState
              icon={Lock}
              title={`${requirement.id} is locked for effort estimation`}
              description={
                requirement.status !== 'Passing'
                  ? `This requirement hasn't passed SRS Quality yet (${requirement.overallScore}%). It must clear the SRS quality gate and complete backlog decomposition before it can be estimated.`
                  : `Backlog decomposition has not been completed for ${requirement.id}. Complete and finalize decomposition first in the Decomposition Studio to unlock effort estimation.`
              }
              actionLabel="Go to Decomposition"
              onAction={() => navigate(team(`/planning/requirements/decomposition?req=${requirement.id}`))}
            />
          )}

          {requirement && isRequirementUnlocked && reqStories.length === 0 && (
            <EmptyState
              icon={Sparkles}
              title="No stories to estimate yet"
              description={`No user stories have been decomposed for ${requirement.id} yet. Decompose the requirement first to generate user stories.`}
              actionLabel="Go to Decomposition"
              onAction={() => navigate(team(`/planning/requirements/decomposition?req=${requirement.id}`))}
            />
          )}

          {requirement && isRequirementUnlocked && reqStories.length > 0 && (
            <>
              <Card className="w-full min-w-0 p-4 flex items-center justify-between gap-3 flex-wrap">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">{requirement.id}</p>
                  <h3 className="truncate text-sm font-semibold text-foreground">{requirement.title}</h3>
                </div>
                <div className="flex items-center gap-3">
                  {/* Filter tabs */}
                  <div className="flex items-center rounded-lg border border-border p-0.5 bg-muted/40 text-xs">
                    <button
                      type="button"
                      onClick={() => setActiveFilter('all')}
                      className={`px-2.5 py-1 rounded-md font-medium transition-colors cursor-pointer ${
                        activeFilter === 'all' ? 'bg-background text-foreground shadow-xs' : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      All ({reqStories.length})
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveFilter('pending')}
                      className={`px-2.5 py-1 rounded-md font-medium transition-colors cursor-pointer ${
                        activeFilter === 'pending' ? 'bg-background text-amber-600 dark:text-amber-400 shadow-xs' : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      Pending ({reqPending.length})
                    </button>
                    <button
                      type="button"
                      onClick={() => setActiveFilter('estimated')}
                      className={`px-2.5 py-1 rounded-md font-medium transition-colors cursor-pointer ${
                        activeFilter === 'estimated' ? 'bg-background text-emerald-600 dark:text-emerald-400 shadow-xs' : 'text-muted-foreground hover:text-foreground'
                      }`}
                    >
                      Estimated ({reqEstimated.length})
                    </button>
                  </div>
                  <Link to={team('/planning/sprint-management')} className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline shrink-0">
                    Sprint Backlog <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
              </Card>

              {displayedStories.length === 0 ? (
                <EmptyState
                  title={activeFilter === 'pending' ? 'All stories are estimated!' : 'No estimated stories yet'}
                  description={
                    activeFilter === 'pending'
                      ? 'Every user story for this requirement has an effort estimate assigned.'
                      : 'Assign story points to user stories below to see them here.'
                  }
                />
              ) : (
                <div className="space-y-3">
                  {displayedStories.map(({ req, story }) => (
                    <StoryRow key={story.id} req={req} story={story} />
                  ))}
                </div>
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
              Academic principles for sizing software work units (1, 2, 3, 5, 8, 13 SP).
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
                <Check className="h-3.5 w-3.5 text-primary" /> Predefined Fibonacci Scale
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
                  <span className="font-bold text-amber-600 dark:text-amber-400 block">13 SP</span>
                  <span className="text-muted-foreground">High complexity: Maximum single story size.</span>
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
