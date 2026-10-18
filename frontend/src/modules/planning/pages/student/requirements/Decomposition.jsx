import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import {
  Sparkles,
  Plus,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  ArrowRight,
  Gavel,
  Lock,
  Bug,
  PenLine,
  Brain,
  GraduationCap,
  BookOpen,
  UserCheck,
  Check,
  ShieldCheck,
  Layers,
  FileEdit,
  Lightbulb,
  History,
  Trash2,
  AlertTriangle,
  CheckSquare,
  Circle,
  Save,
  X,
  ShieldAlert,
} from 'lucide-react'
import { useTeamPath } from '@/shared/hooks/useTeamPath.js'
import Card from '../../../../../shared/components/Card.jsx'
import Badge from '../../../../../shared/components/Badge.jsx'
import EmptyState from '../../../../../shared/components/EmptyState.jsx'
import AvatarComp from '../../../../../shared/components/Avatar.jsx'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
} from '@/components/ui/dialog'
import WorkflowStepper from '../../../components/WorkflowStepper.jsx'
import DartButton from '../../../components/DartButton.jsx'
import RequirementListPanel from '../../../components/RequirementListPanel.jsx'
import SupervisorConsultationModal from '../../../components/SupervisorConsultationModal.jsx'
import DecompositionEvidencePanel from '../../../components/DecompositionEvidencePanel.jsx'
import TaskValidationEvidencePanel from '../../../components/TaskValidationEvidencePanel.jsx'
import { usePlanningData } from '../../../context/usePlanningData.js'
import { useDartCases } from '../../../hooks/useDart.js'
import { useQualityResults } from '../../../hooks/useQuality.js'
import { mapDartCases, getDartCasesForRequirement } from '../../../adapters/dart.js'
import { COURSE_INFO } from '../../../data/lmsAcademicData.js'
import {
  useAnalyzeDecomposition,
  useStories,
  useDecompositionResults,
  useCreateStory,
  useCreateStoryTask,
  useUpdateStoryTask,
  useDeleteStoryTask,
  useValidateTasks,
  useTaskValidation,
  useUpdateStory,
  useDeleteStory,
} from '../../../hooks/useDecomposition.js'
import {
  mapDecompositionResult,
  mapStoryRows,
  mapPersistedDecompositions,
  mapTaskValidationResult,
} from '../../../adapters/decomposition.js'
import { showToast } from '@/shared/utils/toast.jsx'
import { QUALITY_GATE_THRESHOLD, formatRelativeTime } from '../../../utils.js'

const INVEST_CRITERIA = [
  { key: 'independent', code: 'I', label: 'Independent', description: 'The story can be built and delivered independently of other stories.' },
  { key: 'negotiable', code: 'N', label: 'Negotiable', description: 'The story describes the desired outcome, not a fixed technical implementation.' },
  { key: 'valuable', code: 'V', label: 'Valuable', description: 'The story delivers clear, stated value to a stakeholder or user persona.' },
  { key: 'estimable', code: 'E', label: 'Estimable', description: 'The story is concrete enough for the team to size effort with confidence.' },
  { key: 'small', code: 'S', label: 'Small', description: 'The story is scoped to a single concern and completable within a single sprint.' },
  { key: 'testable', code: 'T', label: 'Testable', description: 'The story describes observable behavior that can be verified.' },
]

const TASK_UNLOCK_PASS_COUNT = 4

const BUG_SEVERITY_TONE = { Low: 'neutral', Medium: 'warning', High: 'danger' }

function normalizeAcceptanceCriteria(value) {
  if (Array.isArray(value)) return value.filter((item) => String(item).trim())
  return typeof value === 'string' && value.trim() ? [value.trim()] : []
}

function AcceptanceCriteriaFields({ criteria, onChange }) {
  const updateCriterion = (index, value) => {
    onChange(criteria.map((criterion, currentIndex) => (currentIndex === index ? value : criterion)))
  }

  const removeCriterion = (index) => onChange(criteria.filter((_, currentIndex) => currentIndex !== index))

  return (
    <div className="space-y-2">
      {criteria.map((criterion, index) => (
        <div key={index} className="flex items-start gap-2">
          <Textarea
            value={criterion}
            onChange={(event) => updateCriterion(index, event.target.value)}
            placeholder="Given …, when …, then …"
            rows={2}
            className="text-xs leading-relaxed font-sans bg-background"
            aria-label={`Acceptance criterion ${index + 1}`}
          />
          <Button
            type="button"
            size="icon"
            variant="ghost"
            className="h-8 w-8 shrink-0 text-muted-foreground hover:text-destructive"
            onClick={() => removeCriterion(index)}
            aria-label={`Remove acceptance criterion ${index + 1}`}
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      ))}
      <Button
        type="button"
        size="sm"
        variant="outline"
        className="h-8 text-xs gap-1"
        onClick={() => onChange([...criteria, ''])}
      >
        <Plus className="h-3.5 w-3.5" /> Add acceptance criterion
      </Button>
    </div>
  )
}

const TASK_STATUS_META = {
  todo: { label: 'To Do', tone: 'neutral' },
  in_progress: { label: 'In Progress', tone: 'primary' },
  blocked: { label: 'Blocked', tone: 'danger' },
  done: { label: 'Done', tone: 'success' },
}

const TASK_PRIORITY_META = {
  critical: { label: 'Critical', tone: 'danger' },
  high: { label: 'High', tone: 'warning' },
  medium: { label: 'Medium', tone: 'primary' },
  low: { label: 'Low', tone: 'neutral' },
}

// Normalizes both the real backend's lowercase/underscore status values and
// the legacy Title-Case seed-data values to one label/tone pair.
function taskStatusMeta(status) {
  const key = (status || 'todo').toLowerCase().replace(/\s+/g, '_')
  return TASK_STATUS_META[key] || { label: status || 'To Do', tone: 'neutral' }
}

function taskPriorityMeta(priority) {
  return TASK_PRIORITY_META[(priority || 'medium').toLowerCase()] || TASK_PRIORITY_META.medium
}

// Legacy mock-data subtasks use a `done` boolean; real backend subtasks are
// just tasks with a `status` field — support both shapes.
function isSubtaskDone(st) {
  if (st.status) return st.status.toLowerCase() === 'done'
  return Boolean(st.done)
}

const TASK_CRITERIA_META = {
  relevance: 'Relevance',
  scope: 'Scope',
  actionability: 'Actionability',
  duplication: 'Duplication',
}

function TaskValidationBadges({ validation }) {
  if (!validation) return null
  return (
    <div className="flex items-center gap-1 flex-wrap mt-1.5">
      {Object.entries(TASK_CRITERIA_META).map(([key, label]) => {
        const c = validation[key]
        if (!c) return null
        const pass = c.result === 'Pass' || c.result === 'Needs Improvement'
        return (
          <span
            key={key}
            title={`${label}: ${c.result}${c.note ? ` — ${c.note}` : ''}`}
            className={`inline-flex items-center gap-0.5 text-[9px] font-bold px-1.5 py-0.5 rounded border ${
              c.result === 'Cannot Assess'
                ? 'border-border text-muted-foreground'
                : pass
                  ? 'border-emerald-500/30 text-emerald-600 dark:text-emerald-400 bg-emerald-500/5'
                  : 'border-destructive/30 text-destructive bg-destructive/5'
            }`}
          >
            {label[0]}
          </span>
        )
      })}
    </div>
  )
}

function TaskRow({ reqId, storyId, task, readOnly = false }) {
  const { toggleSubtask } = usePlanningData()
  const createTaskMutation = useCreateStoryTask()
  const updateTaskMutation = useUpdateStoryTask()
  const deleteTaskMutation = useDeleteStoryTask()
  const [expanded, setExpanded] = useState(true)
  const [newSubtask, setNewSubtask] = useState('')
  const [editing, setEditing] = useState(false)
  const [draftTitle, setDraftTitle] = useState(task.title)
  const [draftDescription, setDraftDescription] = useState(task.description || '')
  const statusMeta = taskStatusMeta(task.status)
  const priorityMeta = taskPriorityMeta(task.priority)

  function saveEdits() {
    if (!draftTitle.trim()) return
    updateTaskMutation.mutate(
      { ref: storyId, taskId: task.id, patch: { title: draftTitle.trim(), description: draftDescription } },
      {
        onSuccess: () => setEditing(false),
        onError: () => showToast.error('Could not update task'),
      },
    )
  }

  function handleDelete() {
    deleteTaskMutation.mutate(
      { ref: storyId, taskId: task.id },
      { onError: () => showToast.error('Could not delete task') },
    )
  }

  return (
    <div className="rounded-lg border border-border/70 bg-muted/20 p-3">
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-2 text-left cursor-pointer flex-1 min-w-0"
        >
          {expanded ? (
            <ChevronDown className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
          )}
          <span className="text-xs font-semibold text-foreground flex-1 truncate">{task.title}</span>
        </button>
        <Badge tone={statusMeta.tone} className="text-[10px] px-1.5 py-0 shrink-0">
          {statusMeta.label}
        </Badge>
        <Badge tone={priorityMeta.tone} className="text-[10px] px-1.5 py-0 shrink-0">
          {priorityMeta.label}
        </Badge>
        {!readOnly && (
          <div className="flex items-center gap-0.5 shrink-0">
            <button
              type="button"
              onClick={() => {
                setDraftTitle(task.title)
                setDraftDescription(task.description || '')
                setEditing((v) => !v)
              }}
              className="p-1 rounded text-muted-foreground hover:text-foreground hover:bg-muted cursor-pointer"
              title="Edit task"
            >
              <PenLine className="h-3 w-3" />
            </button>
            <button
              type="button"
              onClick={handleDelete}
              className="p-1 rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 cursor-pointer"
              title="Delete task"
            >
              <Trash2 className="h-3 w-3" />
            </button>
          </div>
        )}
      </div>

      {task.description && !editing && (
        <p className="text-[11px] text-muted-foreground mt-1 ml-5 pl-0.5">{task.description}</p>
      )}

      <div className="ml-5 pl-0.5">
        <TaskValidationBadges validation={task.validation} />
      </div>

      {editing && (
        <div className="mt-2 ml-5 space-y-1.5 p-2.5 rounded-lg border border-primary/20 bg-background">
          <Input
            value={draftTitle}
            onChange={(e) => setDraftTitle(e.target.value)}
            className="h-7 text-xs"
            placeholder="Task title"
          />
          <Textarea
            value={draftDescription}
            onChange={(e) => setDraftDescription(e.target.value)}
            rows={2}
            className="text-xs"
            placeholder="What exactly needs to be built…"
          />
          <div className="flex gap-1.5 justify-end">
            <Button size="sm" variant="outline" className="h-6 text-[11px] px-2" onClick={() => setEditing(false)}>
              <X className="h-3 w-3" /> Cancel
            </Button>
            <Button size="sm" className="h-6 text-[11px] px-2" onClick={saveEdits} disabled={!draftTitle.trim()}>
              <Save className="h-3 w-3" /> Save
            </Button>
          </div>
        </div>
      )}

      {expanded && (
        <div className="mt-2.5 ml-5 space-y-1.5">
          {task.subtasks.map((st) => (
            <label
              key={st.id}
              className={`flex items-center gap-2 text-xs text-foreground cursor-pointer ${
                isSubtaskDone(st) ? 'line-through text-muted-foreground' : ''
              }`}
            >
              <input
                type="checkbox"
                checked={isSubtaskDone(st)}
                disabled={readOnly}
                onChange={() => {
                  const nextStatus = isSubtaskDone(st) ? 'todo' : 'done'
                  updateTaskMutation.mutate(
                    { ref: storyId, taskId: st.id, patch: { status: nextStatus } },
                    {
                      onSuccess: () => toggleSubtask(reqId, storyId, task.id, st.id),
                      onError: () => showToast.error('Could not update sub-task'),
                    },
                  )
                }}
                className="rounded border-border"
              />
              {st.title}
            </label>
          ))}
          {!readOnly && (
            <div className="flex items-center gap-2 pt-1">
              <Input
                value={newSubtask}
                onChange={(e) => setNewSubtask(e.target.value)}
                placeholder="Add a sub-task…"
                className="h-7 text-xs"
              />
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs shrink-0"
                disabled={!newSubtask.trim()}
                  onClick={() => {
                    createTaskMutation.mutate(
                      { ref: storyId, task: { title: newSubtask.trim(), parent_task_id: task.id } },
                      { onSuccess: () => setNewSubtask('') },
                    )
                  }}
              >
                <Plus className="h-3 w-3" />
                Sub-task
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function BugSection({ reqId, storyId, bugs, readOnly = false }) {
  const { addBug, toggleBugStatus } = usePlanningData()
  const [title, setTitle] = useState('')
  const [severity, setSeverity] = useState('Medium')

  return (
    <div className="border-t border-border pt-3 mb-4">
      <div className="flex items-center gap-2 mb-2">
        <Bug className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Known issues &amp; bugs ({bugs.length})
        </span>
      </div>
      {bugs.length > 0 && (
        <ul className="space-y-1.5 mb-3">
          {bugs.map((b) => (
            <li
              key={b.id}
              className="flex items-center justify-between p-2 rounded-lg border border-border bg-card text-xs gap-2"
            >
              <span className={`flex-1 ${b.status === 'Fixed' ? 'line-through text-muted-foreground' : 'text-foreground font-medium'}`}>
                {b.title}
              </span>
              <div className="flex items-center gap-2 shrink-0">
                <Badge tone={BUG_SEVERITY_TONE[b.severity]} className="text-[10px] px-1.5 py-0">{b.severity}</Badge>
                <Badge
                  tone={b.status === 'Fixed' ? 'success' : 'warning'}
                  onClick={() => !readOnly && toggleBugStatus(reqId, storyId, b.id)}
                  className={`text-[10px] px-1.5 py-0 ${!readOnly ? 'cursor-pointer' : ''}`}
                >
                  {b.status}
                </Badge>
              </div>
            </li>
          ))}
        </ul>
      )}
      {!readOnly && (
        <div className="flex items-center gap-2">
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Report a potential issue / bug…"
            className="h-8 text-xs"
          />
          <Select value={severity} onValueChange={setSeverity}>
            <SelectTrigger className="w-[105px] h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Low">Low</SelectItem>
              <SelectItem value="Medium">Medium</SelectItem>
              <SelectItem value="High">High</SelectItem>
            </SelectContent>
          </Select>
          <Button
            size="sm"
            variant="outline"
            className="h-8 text-xs shrink-0 gap-1"
            disabled={!title.trim()}
            onClick={() => {
              addBug(reqId, storyId, title.trim(), severity)
              setTitle('')
            }}
          >
            <Plus className="h-3 w-3" />
            Bug
          </Button>
        </div>
      )}
    </div>
  )
}

function InvestBadges({ investResult }) {
  const [expandedKey, setExpandedKey] = useState(null)
  if (!investResult) return null

  return (
    <div className="space-y-2 mt-3 pt-2.5 border-t border-border/60">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
          <Sparkles className="h-3 w-3 text-primary" />
          INVEST 6-Criterion Verification
        </span>
        <Badge
          tone={investResult.overallPass ? 'success' : 'warning'}
          className="text-[10px] font-semibold px-2 py-0.5"
        >
          {Object.keys(investResult).filter((k) => k !== 'overallPass' && investResult[k]?.pass).length}/6 Pass
        </Badge>
      </div>

      <div className="flex items-center gap-1.5 flex-wrap">
        {INVEST_CRITERIA.map(({ key, code, label }) => {
          const c = investResult[key] || { pass: false, note: 'Not evaluated' }
          const isSelected = expandedKey === key
          return (
            <button
              key={key}
              type="button"
              onClick={() => setExpandedKey(isSelected ? null : key)}
              className={`inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-md cursor-pointer transition-all border ${
                c.pass
                  ? isSelected
                    ? 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border-emerald-500/40 ring-1 ring-emerald-500/30'
                    : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20'
                  : isSelected
                    ? 'bg-destructive/20 text-destructive border-destructive/40 ring-1 ring-destructive/30'
                    : 'bg-destructive/10 text-destructive border-destructive/20 hover:bg-destructive/20'
              }`}
              title={`${label}: ${c.note}`}
            >
              <span className="font-bold text-[10px]">{code}</span>
              <span>{label}</span>
              {c.pass ? (
                <Check className="h-2.5 w-2.5 stroke-[3]" />
              ) : (
                <XCircle className="h-2.5 w-2.5 stroke-[2.5]" />
              )}
            </button>
          )
        })}
      </div>

      {expandedKey && (
        <div
          className={`p-2.5 rounded-lg border text-xs leading-relaxed transition-all ${
            investResult[expandedKey]?.pass
              ? 'bg-emerald-500/5 border-emerald-500/20 text-foreground'
              : 'bg-destructive/5 border-destructive/20 text-foreground'
          }`}
        >
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="font-bold capitalize">{expandedKey} Criterion:</span>
            <Badge
              tone={investResult[expandedKey]?.pass ? 'success' : 'danger'}
              className="text-[9px] px-1.5 py-0"
            >
              {investResult[expandedKey]?.pass ? 'Pass' : 'Needs Work'}
            </Badge>
          </div>
          <p className="text-muted-foreground text-[11px]">
            {investResult[expandedKey]?.note || 'No notes provided by agent.'}
          </p>
        </div>
      )}
    </div>
  )
}

function StoryCard({ reqId, story, readOnly = false }) {
  const { updateStoryText, acceptStory, deleteStory, getTaskValidationEvaluation, recordTaskValidation } =
    usePlanningData()
  const updateMutation = useUpdateStory()
  const createTaskMutation = useCreateStoryTask()
  const deleteMutation = useDeleteStory()
  const validateTasksMutation = useValidateTasks()
  const [editing, setEditing] = useState(false)
  const [draftTitle, setDraftTitle] = useState(story.title)
  const [draftAcceptanceCriteria, setDraftAcceptanceCriteria] = useState(
    normalizeAcceptanceCriteria(story.acceptanceCriteria).join('\n'),
  )
  const [newTask, setNewTask] = useState('')
  const [newTaskPriority, setNewTaskPriority] = useState('medium')

  const accepted = story.status === 'accepted' || story.status === 'Accepted'
  const investPassCount = INVEST_CRITERIA.filter((criterion) => story.investResult?.[criterion.key]?.pass).length
  // Tasks may start once the story has a solid majority of INVEST signals.
  // Full INVEST compliance remains required before the story is accepted.
  const unlocked = investPassCount >= TASK_UNLOCK_PASS_COUNT || accepted
  const canAccept = story.investResult?.overallPass === true && !accepted
  const taskEvaluation = getTaskValidationEvaluation(story.id)

  // Hydrate this story's task-validation evaluation once (not on every
  // render) so it survives a page reload without waiting for a fresh
  // "Validate Tasks" click — mirrors the requirement/decomposition hydration
  // pattern elsewhere on this page, scoped per-story since there is no bulk
  // task-validation list endpoint.
  const taskValidationQuery = useTaskValidation(story.id, unlocked && story.tasks.length > 0 && !taskEvaluation)
  useEffect(() => {
    if (!taskValidationQuery.data?.assessment) return
    const mapped = mapTaskValidationResult(taskValidationQuery.data)
    if (mapped) recordTaskValidation(story.id, mapped)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [taskValidationQuery.data])

  function runTaskValidation() {
    const tasksPayload = story.tasks.map((t) => ({ id: t.id, title: t.title, description: t.description || '' }))
    validateTasksMutation.mutate(
      { ref: story.id, tasks: tasksPayload },
      {
        onSuccess: (data) => {
          if (data?.persisted === false) {
            showToast.warning('Validation complete, but not saved', {
              description: data.persist_error || 'Please re-run validation to retry saving.',
            })
          }
          const mapped = mapTaskValidationResult(data)
          if (mapped?.malformed) {
            showToast.error('Validation response was invalid', { description: mapped.persistError })
            return
          }
          if (mapped) {
            recordTaskValidation(story.id, mapped)
            if (mapped.reused) {
              showToast.info('Already up to date', {
                description: 'Your tasks haven’t changed since the last validation — showing that result.',
              })
            } else {
              showToast.success('Task validation complete', {
                description: `${mapped.readiness} · score ${mapped.score}/4 (${mapped.qualityBand}).`,
              })
            }
          }
        },
        onError: (err) =>
          showToast.error('Validation failed', { description: err?.response?.data?.detail || err.message }),
      },
    )
  }

  function saveEdits() {
    updateMutation.mutate(
      {
        ref: story.id,
        patch: {
          title: draftTitle,
          acceptance_criteria: draftAcceptanceCriteria.split('\n').map((item) => item.trim()).filter(Boolean),
        },
      },
      {
        onSuccess: () => {
          updateStoryText(reqId, story.id, {
            title: draftTitle,
            acceptanceCriteria: draftAcceptanceCriteria.split('\n').map((item) => item.trim()).filter(Boolean),
          })
          setEditing(false)
          showToast.info('Story updated', { description: 'Run decomposition analysis to re-check coverage and INVEST criteria.' })
        },
        onError: () => showToast.error('Could not update user story'),
      },
    )
  }

  function handleDelete() {
    deleteMutation.mutate(story.id, {
      onSuccess: () => {
        deleteStory(reqId, story.id)
        showToast.info('Story removed', { description: `${story.id} has been deleted from this requirement.` })
      },
      onError: () => showToast.error('Could not remove user story'),
    })
  }

  return (
    <Card className="p-4 border-border/80 bg-card">
      <div className="flex items-start justify-between gap-3 mb-2 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-primary/10 text-primary">
            {story.id}
          </span>
          <span className="text-[10px] text-muted-foreground">Parent: {story.parentRequirementRef || reqId}</span>
          <Badge
            tone={
              accepted
                ? 'success'
                : story.investResult
                  ? story.investResult.overallPass
                    ? 'success'
                    : 'warning'
                  : 'neutral'
            }
            className="text-[10px] px-2 py-0.5 font-medium"
          >
            {accepted
              ? 'Accepted Baseline'
              : story.investResult
                ? story.investResult.overallPass
                  ? 'Well-formed (Passes INVEST)'
                  : 'Needs Revision'
                : 'Not Evaluated'}
          </Badge>
        </div>

        {!readOnly && (
          <div className="flex items-center gap-1.5 ml-auto">
            {!editing && (
              <Button
                size="sm"
                variant="ghost"
                className="h-7 text-xs px-2 cursor-pointer gap-1 text-muted-foreground hover:text-foreground"
                onClick={() => {
                  setDraftTitle(story.title)
                  setDraftAcceptanceCriteria(normalizeAcceptanceCriteria(story.acceptanceCriteria).join('\n'))
                  setEditing(true)
                }}
              >
                <PenLine className="h-3 w-3" /> Edit
              </Button>
            )}
            <Button
              size="sm"
              variant="ghost"
              className="h-7 text-xs px-2 cursor-pointer gap-1 text-destructive hover:bg-destructive/10"
              onClick={handleDelete}
              title="Delete user story"
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
        )}
      </div>

      {editing ? (
        <div className="space-y-2.5 my-3 p-3 rounded-xl border border-primary/20 bg-muted/20">
          <div>
            <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
              User Story Specification
            </label>
            <Input
              value={draftTitle}
              onChange={(e) => setDraftTitle(e.target.value)}
              className="text-xs font-medium"
              placeholder="As a [persona], I want [action], so that [business value]…"
            />
          </div>
          <div>
            <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
              Acceptance Criteria (one per line)
            </label>
            <Textarea
              value={draftAcceptanceCriteria}
              onChange={(e) => setDraftAcceptanceCriteria(e.target.value)}
              rows={3}
              className="text-xs leading-relaxed font-sans"
              placeholder="Given …, when …, then …"
            />
          </div>
          <div className="flex gap-2 justify-end pt-1">
            <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => setEditing(false)}>
              Cancel
            </Button>
            <Button size="sm" className="h-7 text-xs" onClick={saveEdits} disabled={!draftTitle.trim()}>
              Save Story
            </Button>
          </div>
        </div>
      ) : (
        <div className="mb-3 space-y-1.5">
          <p className="text-xs font-semibold text-foreground leading-snug">{story.title}</p>
          {normalizeAcceptanceCriteria(story.acceptanceCriteria).length > 0 && (
            <div className="text-[11px] text-muted-foreground leading-relaxed p-2.5 rounded-lg bg-muted/30 border border-border/60">
              <span className="font-semibold text-foreground block mb-1">Acceptance Criteria:</span>
              <ul className="list-disc pl-4 space-y-0.5">
                {normalizeAcceptanceCriteria(story.acceptanceCriteria).map((criterion, index) => <li key={`${story.id}-ac-${index}`}>{criterion}</li>)}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* INVEST Criterion Chips */}
      {!editing && story.investResult ? (
        <InvestBadges investResult={story.investResult} />
      ) : (
        !editing && (
          <p className="text-[11px] text-muted-foreground italic my-2">
            Not yet evaluated — click "Run Decomposition Analysis" to check INVEST compliance and coverage.
          </p>
        )
      )}

      {/* Sprint Tasks & Subtasks */}
      <div className="mt-3.5 pt-3 border-t border-border/60">
        {unlocked ? (
          <>
            <div className="flex items-center justify-between gap-2 mb-2 flex-wrap">
              <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                Tasks ({story.tasks.length})
              </span>
              <div className="flex items-center gap-1.5">
                {taskEvaluation && !taskEvaluation.analysisFailed && !taskEvaluation.malformed && (
                  <Badge
                    tone={
                      taskEvaluation.readiness === 'Valid'
                        ? 'success'
                        : taskEvaluation.readiness === 'Coverage Warning'
                          ? 'primary'
                          : 'warning'
                    }
                    className="text-[10px] px-2 py-0.5"
                  >
                    {taskEvaluation.stale ? 'Stale · ' : ''}
                    {taskEvaluation.readiness}
                  </Badge>
                )}
                {!readOnly && story.tasks.length > 0 && (
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-6 text-[11px] px-2 gap-1 cursor-pointer"
                    disabled={validateTasksMutation.isPending}
                    onClick={runTaskValidation}
                    title="Check task relevance, scope, actionability, duplication, and story coverage"
                  >
                    <ShieldAlert className={`h-3 w-3 ${validateTasksMutation.isPending ? 'animate-pulse' : ''}`} />
                    {validateTasksMutation.isPending ? 'Validating…' : 'Validate Tasks'}
                  </Button>
                )}
              </div>
            </div>

            <div className="space-y-2 mb-3">
              {story.tasks.map((task) => (
                <TaskRow key={task.id} reqId={reqId} storyId={story.id} task={task} readOnly={readOnly} />
              ))}
              {story.tasks.length === 0 && (
                <p className="text-[11px] text-muted-foreground italic">
                  No tasks yet — break this story down into concrete development tasks below.
                </p>
              )}
            </div>

            <TaskValidationEvidencePanel evaluation={taskEvaluation} />

            {!readOnly && (
              <div className="flex items-center gap-2 mb-3">
                <Input
                  value={newTask}
                  onChange={(e) => setNewTask(e.target.value)}
                  placeholder="Add a sprint implementation task…"
                  className="h-8 text-xs"
                />
                <Select value={newTaskPriority} onValueChange={setNewTaskPriority}>
                  <SelectTrigger className="h-8 w-28 text-xs shrink-0">
                    <SelectValue placeholder="Priority" />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(TASK_PRIORITY_META).map(([value, meta]) => (
                      <SelectItem key={value} value={value}>{meta.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Button
                  size="sm"
                  variant="outline"
                  className="h-8 text-xs shrink-0 gap-1 cursor-pointer"
                  disabled={!newTask.trim()}
                  onClick={() => {
                    createTaskMutation.mutate(
                      { ref: story.id, task: { title: newTask.trim(), priority: newTaskPriority } },
                      {
                        onSuccess: () => {
                          setNewTask('')
                          setNewTaskPriority('medium')
                        },
                      },
                    )
                  }}
                >
                  <Plus className="h-3.5 w-3.5" />
                  Task
                </Button>
              </div>
            )}

            <BugSection reqId={reqId} storyId={story.id} bugs={story.bugs || []} readOnly={readOnly} />

            {!readOnly && canAccept && (
              <div className="flex justify-end pt-1">
                <Button
                  size="sm"
                  variant="outline"
                  className="text-xs h-7 gap-1.5 cursor-pointer text-emerald-600 hover:text-emerald-700 hover:bg-emerald-500/10"
                  onClick={() => {
                    updateMutation.mutate(
                      { ref: story.id, patch: { status: 'accepted' } },
                      {
                        onSuccess: () => {
                          acceptStory(reqId, story.id)
                          showToast.success('Story accepted', { description: `${story.id} accepted for effort estimation.` })
                        },
                        onError: () => showToast.error('Could not accept story'),
                      },
                    )
                  }}
                >
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  Accept Story
                </Button>
              </div>
            )}
          </>
        ) : (
          !editing && (
            <p className="text-[11px] text-muted-foreground italic flex items-center gap-1.5">
              <Lock className="h-3 w-3" />
              Tasks, sub-tasks and bug tracking unlock after at least {TASK_UNLOCK_PASS_COUNT} of 6 INVEST criteria pass.
            </p>
          )
        )}
      </div>
    </Card>
  )
}

function NewStoryForm({ reqId, initialTitle = '', onDone }) {
  const createMutation = useCreateStory()
  const [title, setTitle] = useState(initialTitle)
  const [acceptanceCriteria, setAcceptanceCriteria] = useState([''])

  function submit() {
    if (!title.trim()) return
    createMutation.mutate({
      requirement_ref: reqId,
      title: title.trim(),
      acceptance_criteria: acceptanceCriteria.map((item) => item.trim()).filter(Boolean),
    }, {
      onSuccess: () => {
        setTitle('')
        setAcceptanceCriteria([''])
        onDone?.()
        showToast.success('User story created', {
          description: 'Run decomposition analysis to evaluate INVEST criteria and parent coverage.',
        })
      },
      onError: () => showToast.error('Could not create user story'),
    })
  }

  function insertTemplate() {
    if (!title.trim()) {
      setTitle('As a [registered user], I want [capability], so that [business value].')
    }
  }

  return (
    <Card className="p-4 border-primary/30 bg-primary/5 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
            <Plus className="h-3.5 w-3.5" />
            Write User Story (Agile Format)
          </p>
          <p className="text-[11px] text-muted-foreground mt-0.5">
            Model concrete personas, observable behavior, and clear value to achieve high INVEST and coverage scores.
          </p>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={insertTemplate}
          className="text-xs h-7 px-2 cursor-pointer gap-1 text-primary border-primary/30"
          type="button"
        >
          <Sparkles className="h-3 w-3" /> Insert Template
        </Button>
      </div>

      <div className="space-y-4">
        <div>
          <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
            User Story (As a … I want … So that …)
          </label>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="As a [persona], I want [action], so that [outcome]…"
            className="text-xs bg-background"
          />
        </div>
        <div>
          <label className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground block mb-1">
            Acceptance Criteria <span className="normal-case font-normal">(optional)</span>
          </label>
          <p className="text-[11px] text-muted-foreground mb-2">Add each verifiable condition separately.</p>
          <AcceptanceCriteriaFields criteria={acceptanceCriteria} onChange={setAcceptanceCriteria} />
        </div>
      </div>

      <div className="flex items-center justify-end gap-2 pt-1 border-t border-border/60">
        <Button size="sm" variant="ghost" onClick={onDone} className="text-xs h-8 cursor-pointer">
          Cancel
        </Button>
        <Button
          size="sm"
          onClick={submit}
          disabled={!title.trim() || createMutation.isPending}
          className="text-xs h-8 cursor-pointer gap-1.5"
        >
          <Plus className="h-3.5 w-3.5" /> {createMutation.isPending ? 'Saving…' : 'Save User Story'}
        </Button>
      </div>
    </Card>
  )
}

const CHECK_LABELS = {
  C1: 'Parent linkage',
  C2: 'Functional coverage',
  C3: 'Data coverage',
  C4: 'Condition coverage',
  C5: 'Exception coverage',
  C6: 'No orphan stories',
  C7: 'No duplicate scope',
  C8: 'No scope loss',
  C9: 'No out-of-scope behavior',
  C10: 'Parent traceability & behavior coverage',
}

const INVEST_RESULT_TONE = {
  Pass: 'success',
  'Pass with note': 'success',
  Fail: 'danger',
  'Cannot Assess': 'neutral',
}

function CoverageAndInvestSection({ evaluation, onAddGapStory }) {
  if (!evaluation) return null
  const checks = evaluation.coverage?.checks || []
  const elements = evaluation.coverage?.elements || []
  const coveragePercent = Math.round(evaluation.coverage?.percentage || 0)
  const missingElements = elements.filter((e) => e.coverage_result === 'Missing')
  const investStories = Object.entries(evaluation.investResults || {})
  const passedChecks = checks.filter((c) => c.result === 'Pass').length
  const analysisFailed = Boolean(evaluation.analysisFailed)
  const analysisSkipped = Boolean(evaluation.analysisSkipped)

  return (
    <div className="space-y-4">
      {analysisFailed && (
        <Card className="p-3.5 border-destructive/30 bg-destructive/5 flex items-center gap-2.5">
          <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
          <p className="text-xs text-destructive">
            The checklist below is a placeholder — coverage analysis could not run
            {evaluation.failureReason ? ` (${evaluation.failureReason})` : ''}. Re-run analysis once the issue is resolved.
          </p>
        </Card>
      )}

      {/* Coverage Gate — C1 through C10 */}
      {!analysisSkipped && (
      <Card className="p-5">
        <div className="flex items-center justify-between gap-3 mb-2 flex-wrap">
          <div>
            <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
              <CheckSquare className="h-4 w-4 text-primary" />
              Coverage Checklist — C1 through C10
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              These checks focus on covering the parent requirement fully and traceably — the most important
              signal for readiness. Failing checks are improvement guidance, not a hard block.
            </p>
          </div>
          <Badge
            tone={passedChecks === 10 && checks.length === 10 ? 'success' : analysisFailed ? 'danger' : 'warning'}
            className="text-xs font-bold px-2.5 py-1"
          >
            {analysisFailed ? 'Analysis Failed' : `${passedChecks}/10 Checks Passing · ${coveragePercent}% Coverage`}
          </Badge>
        </div>

        <div className="mb-4 mt-2">
          <div className="h-2 rounded-full bg-muted overflow-hidden">
            <div
              className={`h-full transition-all duration-700 ease-out rounded-full ${
                coveragePercent >= 80 ? 'bg-emerald-500' : 'bg-amber-500'
              }`}
              style={{ width: `${coveragePercent}%` }}
            />
          </div>
        </div>

        <div className="space-y-1.5 mb-3">
          {checks.length === 0 ? (
            <p className="text-xs text-muted-foreground italic">No checks reported yet.</p>
          ) : (
            checks.map((c) => (
              <div
                key={c.check_id}
                className={`p-2.5 rounded-lg border text-xs ${
                  c.result === 'Pass' ? 'border-border/60 bg-card' : 'border-destructive/25 bg-destructive/5'
                }`}
              >
                <div className="flex items-center gap-2">
                  {c.result === 'Pass' ? (
                    <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                  ) : (
                    <XCircle className="h-3.5 w-3.5 text-destructive shrink-0" />
                  )}
                  <span className="font-mono text-[10px] font-bold px-1.5 py-0.5 rounded bg-muted text-muted-foreground shrink-0">
                    {c.check_id}
                  </span>
                  <span className="font-semibold text-foreground">
                    {CHECK_LABELS[c.check_id] || c.check_id}
                  </span>
                </div>
                {c.rationale && (
                  <p className="text-[11px] text-muted-foreground mt-1 ml-6">{c.rationale}</p>
                )}
              </div>
            ))
          )}
        </div>

        {missingElements.length > 0 ? (
          <div className="p-3.5 rounded-xl border border-amber-500/30 bg-amber-500/5">
            <div className="flex items-center gap-2 mb-1.5">
              <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0" />
              <p className="text-xs font-bold text-amber-800 dark:text-amber-300">
                Missing Coverage Elements ({missingElements.length})
              </p>
            </div>
            <p className="text-[11px] text-muted-foreground mb-2 leading-relaxed">
              The agent extracted these elements from the parent requirement, but found no matching user story covering them:
            </p>
            <ul className="space-y-1.5 text-xs text-foreground">
              {missingElements.map((el, idx) => (
                <li
                  key={idx}
                  className="flex items-center justify-between gap-2 p-2 rounded-lg bg-background/80 border border-border"
                >
                  <span>
                    <span className="font-mono text-[10px] text-muted-foreground uppercase mr-1.5">
                      {el.element_type}
                    </span>
                    <span className="font-medium text-foreground">{el.description}</span>
                  </span>
                  {onAddGapStory && (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => onAddGapStory(el.description)}
                      className="text-[11px] h-6 px-2 shrink-0 cursor-pointer text-primary border-primary/30"
                    >
                      <Plus className="h-3 w-3" /> Add Story for Gap
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ) : analysisFailed ? (
          <div className="flex items-center gap-2.5 p-3 rounded-xl border border-destructive/25 bg-destructive/5">
            <AlertTriangle className="h-4 w-4 text-destructive shrink-0" />
            <p className="text-xs font-bold text-destructive">
              Coverage analysis could not be completed — the checks above reflect an agent failure, not a real result. Re-run analysis.
            </p>
          </div>
        ) : checks.length > 0 ? (
          <div className="flex items-center gap-2.5 p-3 rounded-xl border border-emerald-500/20 bg-emerald-500/5">
            <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
            <p className="text-xs font-bold text-emerald-700 dark:text-emerald-400">
              Every coverage element is represented in your user story backlog.
            </p>
          </div>
        ) : null}
      </Card>
      )}

      {/* INVEST Readiness Matrix */}
      <Card className="p-5">
        <div className="flex items-center justify-between gap-2 mb-3 flex-wrap">
          <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            INVEST Improvement Guidance
          </h3>
          <span className="text-xs text-muted-foreground font-medium">
            Guidance, not a requirement — Pass or Pass with note on all six means polished
          </span>
        </div>
        {investStories.length === 0 ? (
          <p className="text-xs text-muted-foreground italic">No stories evaluated yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="text-[10px] uppercase tracking-wider text-muted-foreground">
                  <th className="text-left font-semibold pb-2 pr-2">Story</th>
                  {INVEST_CRITERIA.map((c) => (
                    <th key={c.key} className="text-center font-semibold pb-2 px-1" title={c.label}>
                      {c.code}
                    </th>
                  ))}
                  <th className="text-center font-semibold pb-2 pl-2">Ready</th>
                </tr>
              </thead>
              <tbody>
                {investStories.map(([storyRef, result]) => (
                  <tr key={storyRef} className="border-t border-border/60">
                    <td className="py-2 pr-2 font-medium text-foreground">{storyRef}</td>
                    {INVEST_CRITERIA.map((c) => {
                      const cell = result[c.key] || {}
                      return (
                        <td key={c.key} className="text-center px-1 py-2" title={cell.note || ''}>
                          <Badge
                            tone={INVEST_RESULT_TONE[cell.result] || 'neutral'}
                            className="text-[9px] px-1 py-0"
                          >
                            {cell.result === 'Pass with note'
                              ? 'Note'
                              : cell.result === 'Cannot Assess'
                                ? '—'
                                : cell.result || '—'}
                          </Badge>
                        </td>
                      )
                    })}
                    <td className="text-center pl-2">
                      {result.storyReady ? (
                        <CheckCircle2 className="h-4 w-4 text-emerald-500 inline" />
                      ) : (
                        <XCircle className="h-4 w-4 text-destructive inline" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}

function RevisionHistorySection({ history }) {
  if (!history || history.length === 0) {
    return (
      <Card className="p-5 text-center text-xs text-muted-foreground">
        No revision history yet. Run a decomposition analysis to begin tracking iteration progress.
      </Card>
    )
  }

  return (
    <Card className="p-5 space-y-3">
      <div className="flex items-center justify-between pb-2 border-b border-border/60">
        <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
          <History className="h-4 w-4 text-primary" />
          Decomposition Iteration &amp; Re-score History
        </h3>
        <span className="text-xs text-muted-foreground font-medium">
          {history.length} Analysis Iteration{history.length > 1 ? 's' : ''}
        </span>
      </div>

      <div className="space-y-2.5">
        {history.map((entry, idx) => (
          <div
            key={idx}
            className={`flex items-start justify-between gap-3 p-3 rounded-xl border text-xs ${
              entry.analysisFailed ? 'border-destructive/25 bg-destructive/5' : 'border-border/70 bg-card'
            }`}
          >
            <div className="space-y-1">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="font-mono font-bold text-primary px-1.5 py-0.5 rounded bg-primary/10 text-[11px]">
                  Rev {entry.version}
                </span>
                {entry.analysisFailed ? (
                  <Badge tone="danger" className="text-[10px] font-semibold px-2 py-0">
                    Analysis Failed
                  </Badge>
                ) : (
                  <>
                    <Badge
                      tone={entry.readiness === 'Ready' ? 'success' : entry.readiness === 'Needs Attention' ? 'warning' : 'primary'}
                      className="text-[10px] font-semibold px-2 py-0"
                    >
                      {entry.score}/4 · {entry.readiness || 'Needs Attention'}
                    </Badge>
                    {entry.qualityBand && (
                      <span className="text-[11px] text-muted-foreground">{entry.qualityBand}</span>
                    )}
                  </>
                )}
              </div>
              {entry.analysisFailed ? (
                <p className="text-xs text-destructive line-clamp-2 leading-relaxed">
                  System error — not a real evaluation
                  {entry.failureReason ? `: ${entry.failureReason}` : '.'}
                </p>
              ) : (
                entry.summary && (
                  <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
                    {entry.summary}
                  </p>
                )
              )}
            </div>
            <span className="text-[11px] text-muted-foreground shrink-0">
              {formatRelativeTime(entry.timestamp)}
            </span>
          </div>
        ))}
      </div>
    </Card>
  )
}

export default function Decomposition() {
  const navigate = useNavigate()
  const team = useTeamPath()
  const [searchParams] = useSearchParams()
  const reqParam = searchParams.get('req')

  const {
    requirements,
    getStories,
    getDecompositionEvaluation,
    recordDecompositionAnalysis,
    getDecompositionHistory,
    finalizeDecomposition,
    loadStories,
    getTaskValidationEvaluation,
  } = usePlanningData()

  // An active requirement in Decomposition must pass IEEE 830 quality (>=75%) AND have proceeded/finalized
  const isReqUnlocked = (r) => Boolean(r && r.status === 'Passing' && (r.finalized || r.decompUnlocked))

  // Sort requirements: only quality passed and proceeded requirements appear at the top.
  // Other requirements appear below and are greyed out / locked until "Proceed to Decomposition" is clicked.
  const sortedRequirements = [...requirements].sort((a, b) => {
    const aUnlocked = isReqUnlocked(a)
    const bUnlocked = isReqUnlocked(b)
    if (aUnlocked && !bUnlocked) return -1
    if (!aUnlocked && bUnlocked) return 1
    return 0
  })

  const unlockedReqs = sortedRequirements.filter(isReqUnlocked)

  const [userSelectedReqId, setUserSelectedReqId] = useState(null)
  const [showNewStoryForm, setShowNewStoryForm] = useState(false)
  const [gapInitialTitle, setGapInitialTitle] = useState('')
  const [mainTab, setMainTab] = useState('all')

  // Derive active requirement ID: student manual pick -> URL query param -> first unlocked -> first in catalog
  const selectedReqId =
    (userSelectedReqId && requirements.some((r) => r.id === userSelectedReqId) ? userSelectedReqId : null) ||
    (reqParam && requirements.some((r) => r.id === reqParam) ? reqParam : null) ||
    unlockedReqs[0]?.id ||
    sortedRequirements[0]?.id ||
    ''

  const analyzeMutation = useAnalyzeDecomposition()
  const qualityQuery = useQualityResults()
  const storiesQuery = useStories()
  const { data: dartData } = useDartCases()
  const allDartCases = mapDartCases(dartData?.cases || [])
  const decompositionQuery = useDecompositionResults()

  // Hydrate stories + decomposition results from DB on mount
  useEffect(() => {
    if (storiesQuery.isError) {
      showToast.error('Could not load your stories', {
        description: storiesQuery.error?.message || 'Please reload the page.',
      })
      return
    }
    if (storiesQuery.data?.stories) {
      const mapped = mapStoryRows(storiesQuery.data.stories)
      if (Object.keys(mapped).length > 0) loadStories(mapped)
    }
  }, [storiesQuery.data, storiesQuery.isError]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (decompositionQuery.isError) {
      showToast.error('Could not load decomposition results', {
        description: decompositionQuery.error?.message || 'Please reload the page.',
      })
      return
    }
    if (decompositionQuery.data?.results) {
      const mapped = mapPersistedDecompositions(decompositionQuery.data.results)
      for (const [reqId, eval_] of Object.entries(mapped)) {
        if (eval_ && !eval_.malformed) recordDecompositionAnalysis(reqId, eval_)
      }
    }
  }, [decompositionQuery.data, decompositionQuery.isError]) // eslint-disable-line react-hooks/exhaustive-deps

  const requirement = requirements.find((r) => r.id === selectedReqId) || null
  const isEligible = isReqUnlocked(requirement)
  const stories = isEligible ? getStories(selectedReqId) : []
  const evaluation = isEligible ? getDecompositionEvaluation(selectedReqId) : null
  const analyzing = analyzeMutation.isPending

  const isDecompFinalized = Boolean(requirement?.decompFinalized)
  // Readiness is a three-tier, NON-BLOCKING signal (Ready / Ready with
  // Improvements / Needs Attention) — the student can proceed to effort
  // estimation once any real analysis has run, regardless of tier. Only
  // "no analysis has run yet" and "the last run was a system error" withhold
  // the button; a low score or missing coverage never does.
  const readiness = evaluation?.readiness || null
  const isDecompPassed = readiness === 'Ready'
  const canProceedProvisionally = Boolean(evaluation) && !evaluation.analysisFailed && !evaluation.malformed
  const canRunAnalysis = stories.length > 0 && (!evaluation || evaluation.stale || evaluation.analysisFailed)

  // Task-validation readiness is tracked per story, not per requirement —
  // surface the worst tier across the requirement's stories so the proceed
  // confirmation can mention it too. Never blocks on its own, same as
  // decomposition readiness.
  const taskEvaluations = stories
    .map((s) => getTaskValidationEvaluation(s.id))
    .filter((e) => e && !e.analysisFailed && !e.malformed)
  const storiesWithCoverageWarning = taskEvaluations.filter((e) => e.readiness === 'Coverage Warning')

  // History tracking for the active requirement
  const rawHistory = getDecompositionHistory(selectedReqId) || []
  const history = [...rawHistory].sort((a, b) => {
    const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0
    const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0
    if (timeA && timeB && timeA !== timeB) return timeB - timeA
    return (b.version || 0) - (a.version || 0)
  })
  const scoreTrend = history.length >= 2 ? history[0].score - history[1].score : null

  function getDecompositionMeta(r) {
    const unlocked = isReqUnlocked(r)
    if (!unlocked) {
      return {
        percent: r.overallScore || 0,
        tone: 'neutral',
        locked: true,
        finalized: false,
      }
    }
    const eval_ = getDecompositionEvaluation(r.id)
    const isFinal = Boolean(r.decompFinalized)
    const percent = eval_ ? Math.round(((eval_.score ?? 0) / 4) * 100) : 0
    const isReady = eval_?.readiness === 'Ready'
    return {
      percent,
      tone: isFinal || isReady ? 'success' : percent > 0 ? 'warning' : 'neutral',
      locked: false,
      finalized: isFinal,
    }
  }

  function runAnalysis() {
    if (!requirement || stories.length === 0) return
    const storiesPayload = stories.map((s) => ({
      id: s.id,
      title: s.title,
      description: s.description || '',
    }))
    analyzeMutation.mutate(
      {
        requirement: { id: requirement.id, text: requirement.description || requirement.title },
        stories: storiesPayload,
      },
      {
        onSuccess: (data) => {
          if (data?.persisted === false) {
            showToast.warning('Analysis complete, but not saved', {
              description: data.persist_error || 'Please re-run analysis to retry saving.',
            })
          }
          const mapped = mapDecompositionResult(data)
          if (mapped?.malformed) {
            showToast.error('Analysis response was invalid', {
              description: mapped.persistError || 'Please try again or contact your supervisor.',
            })
            return
          }
          if (mapped) {
            recordDecompositionAnalysis(selectedReqId, mapped)
            if (mapped.reused) {
              showToast.info('Already up to date', {
                description: 'Your stories haven’t changed since the last analysis — showing that result.',
              })
            } else {
              showToast.success('Decomposition analysis complete', {
                description: `${mapped.readiness} · score ${mapped.score}/4 (${mapped.qualityBand}).`,
              })
            }
          }
        },
        onError: (err) => {
          showToast.error('Analysis failed', {
            description: err?.response?.data?.detail || err.message || 'Unknown error',
          })
        },
      },
    )
  }

  const [provisionalConfirmOpen, setProvisionalConfirmOpen] = useState(false)

  function completeProceedToEstimation(targetReq) {
    const target = targetReq || requirement
    if (!target) return
    finalizeDecomposition(target.id)
    showToast.success('Decomposition finalized', {
      description: `${target.id} stories finalized for Effort Estimation.`,
    })
    navigate(team(`/planning/requirements/estimation?req=${target.id}`))
  }

  // Ready proceeds immediately; Ready with Improvements / Needs Attention
  // still proceed — never a hard block — but ask for one explicit
  // confirmation first so the student has actually seen the warning instead
  // of clicking past it unnoticed.
  function handleProceedToEstimation(targetReq) {
    const target = targetReq || requirement
    if (!target) return
    if ((readiness && readiness !== 'Ready') || storiesWithCoverageWarning.length > 0) {
      setProvisionalConfirmOpen(true)
      return
    }
    completeProceedToEstimation(target)
  }

  function handleAddGapStory(gapLabel) {
    setGapInitialTitle(`As a user, I want ${gapLabel.toLowerCase()}, so that system integrity is maintained.`)
    setShowNewStoryForm(true)
    setMainTab('stories')
  }

  const [investGuideOpen, setInvestGuideOpen] = useState(false)
  const [consultOpen, setConsultOpen] = useState(false)

  const eligibleCount = unlockedReqs.length
  const decomposedCount = unlockedReqs.filter(
    (r) => Boolean(r.decompFinalized) || getDecompositionEvaluation(r.id)?.readiness === 'Ready',
  ).length
  const overallDecompPercent = eligibleCount ? Math.round((decomposedCount / eligibleCount) * 100) : 0

  const dartCases = getDartCasesForRequirement(allDartCases, selectedReqId).filter((c) => c.status === 'open')

  const DECOMP_TABS = [
    { id: 'all', label: 'All', icon: Layers },
    { id: 'stories', label: 'Stories & Tasks', icon: FileEdit, count: stories.length },
    {
      id: 'coverage',
      label: 'User Story Quality',
      icon: Sparkles,
      count: evaluation
        ? evaluation.analysisFailed
          ? 'Error'
          : `${Object.keys(evaluation.investResults || {}).length} stories`
        : undefined,
    },
    { id: 'evidence', label: 'Agent Evidence & Patterns', icon: Lightbulb },
    { id: 'history', label: 'Revision History', icon: History, count: history.length },
  ]

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
            Backlog Decomposition &amp; INVEST Story Modeling
            <Badge tone="primary" className="text-xs font-medium">
              Two-Level Gate: Coverage + INVEST Readiness
            </Badge>
          </h1>
        </div>

        {/* Action Toolbar */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setInvestGuideOpen(true)}
            className="text-xs cursor-pointer gap-1.5"
          >
            <BookOpen className="h-3.5 w-3.5 text-primary" /> INVEST Standards Guide
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setConsultOpen(true)}
            className="text-xs cursor-pointer gap-1.5"
          >
            <UserCheck className="h-3.5 w-3.5 text-primary" /> Supervisor Advisory
          </Button>
          {isEligible && !isDecompFinalized && (
            <Button
              size="sm"
              onClick={() => {
                setGapInitialTitle('')
                setShowNewStoryForm(true)
                setMainTab('stories')
              }}
              className="text-xs cursor-pointer gap-1.5"
            >
              <Plus className="h-3.5 w-3.5" /> + Write User Story
            </Button>
          )}
        </div>
      </div>

      {/* LMS Project Banner Card with Round Progress Bar */}
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
              <span>Methodology: <strong className="text-foreground">INVEST Agile Framework</strong></span>
            </div>

            <h2 className="text-lg sm:text-xl font-semibold text-foreground tracking-tight">
              Backlog Decomposition &amp; Story Traceability Studio
            </h2>

            <p className="text-xs text-muted-foreground leading-relaxed">
              Decompose quality-gated functional requirements into atomic user stories with acceptance criteria and parent-requirement traceability. The agent validates INVEST compliance and detects unrepresented requirement scope.
            </p>

            <div className="flex items-center gap-4 flex-wrap pt-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5 font-medium text-foreground">
                <AvatarComp name={COURSE_INFO.supervisor.name} size={20} className="ring-1 ring-border" />
                Supervisor: {COURSE_INFO.supervisor.name}
              </span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span className="flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                {eligibleCount} of {requirements.length} Requirements Unlocked
              </span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span className="flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5 text-primary" />
                {decomposedCount} of {eligibleCount} Passing Gate
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
                  strokeDashoffset={(2 * Math.PI * 38) * (1 - overallDecompPercent / 100)}
                  strokeLinecap="round"
                  fill="transparent"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-xl font-bold tracking-tight text-foreground">{overallDecompPercent}%</span>
              </div>
            </div>
            <span className="text-xs font-semibold text-muted-foreground mt-1.5">Decomp. Progress</span>
          </div>
        </div>
      </Card>

      <WorkflowStepper current="decomposition" />

      {requirements.length === 0 && qualityQuery.isLoading ? (
        <Card className="p-12 text-center flex flex-col items-center justify-center space-y-4">
          <div className="relative flex items-center justify-center">
            <div className="h-10 w-10 border-4 border-primary/20 border-t-primary rounded-full animate-spin" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">Loading requirements...</h3>
            <p className="text-xs text-muted-foreground mt-1">Retrieving IEEE 830 quality scores and decomposition backlog.</p>
          </div>
        </Card>
      ) : requirements.length === 0 ? (
        <EmptyState
          icon={Lock}
          title="No requirements available"
          description="Upload an SRS document or add requirements in SRS Quality first to begin backlog decomposition."
          actionLabel="Go to SRS Quality"
          onAction={() => navigate(team('/planning/requirements/srs-quality'))}
        />
      ) : (
        /* 2-Column Responsive Layout mirroring SRS Quality */
        <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] xl:grid-cols-[320px_1fr] gap-6 items-start">
          {/* Column 1 — Requirements Directory (Sticky on scroll) */}
          <div className="space-y-3 lg:sticky lg:top-4 self-start">
            <div className="flex items-center justify-between px-1">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Requirements Catalog
              </span>
              <span className="text-xs text-muted-foreground font-medium">
                {eligibleCount}/{requirements.length} Unlocked
              </span>
            </div>
            <RequirementListPanel
              requirements={sortedRequirements}
              selectedId={selectedReqId}
              onSelect={(id) => {
                setUserSelectedReqId(id)
                setShowNewStoryForm(false)
              }}
              getItemMeta={getDecompositionMeta}
              maxHeight="calc(100vh - 12rem)"
            />
          </div>

          {/* Column 2 — Main Decomposition Studio */}
          {requirement ? (
            !isEligible ? (
              <EmptyState
                icon={Lock}
                title={`${requirement.id} is locked for decomposition`}
                description={
                  requirement.status === 'Passing'
                    ? `This requirement scored ${requirement.overallScore}% in SRS Quality and meets the IEEE 830 quality threshold, but has not been finalized yet. Open SRS Quality and click "Proceed to Decomposition" to unlock it.`
                    : `This requirement scored ${requirement.overallScore}% in SRS Quality (${requirement.status}). Requirements must achieve ≥${QUALITY_GATE_THRESHOLD}% quality and be finalized before backlog decomposition.`
                }
                actionLabel="Go to SRS Quality"
                onAction={() => navigate(team('/planning/requirements/srs-quality'))}
              />
            ) : (
              <div className="space-y-4">
                {/* Top Filter Tabs + Top-Right "Go to Next Step" Button */}
                <div className="flex items-center justify-between gap-3 flex-wrap pb-1">
                  {/* Left: Tab Switcher to filter visible sections */}
                  <div className="flex items-center gap-1.5 p-1 bg-muted/40 rounded-xl border border-border/50 flex-wrap">
                    {DECOMP_TABS.map((tab) => {
                      const Icon = tab.icon
                      const isActive = mainTab === tab.id
                      return (
                        <button
                          key={tab.id}
                          type="button"
                          onClick={() => setMainTab(tab.id)}
                          className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                            isActive
                              ? 'bg-background text-foreground shadow-xs border border-border/80'
                              : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
                          }`}
                        >
                          <Icon className={`h-3.5 w-3.5 ${isActive ? 'text-primary' : 'text-muted-foreground'}`} />
                          <span>{tab.label}</span>
                          {tab.count !== undefined && (
                            <span
                              className={`text-[10px] font-bold px-1.5 py-0.2 rounded-full ${
                                isActive ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'
                              }`}
                            >
                              {tab.count}
                            </span>
                          )}
                        </button>
                      )
                    })}
                  </div>

                  {/* Right: Top-Right Corner "Go to Next Step" Button */}
                  <div className="flex items-center gap-2">
                    {isDecompFinalized ? (
                      <Link
                        to={team(`/planning/requirements/estimation?req=${requirement.id}`)}
                        className="inline-flex items-center gap-1.5 text-xs font-bold px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition-all shrink-0 cursor-pointer"
                        title="Decomposition quality is finalized. Go to Effort Estimation."
                      >
                        <ShieldCheck className="h-3.5 w-3.5" />
                        <span>View in Effort Estimation</span>
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    ) : isDecompPassed ? (
                      <Button
                        size="sm"
                        onClick={() => handleProceedToEstimation(requirement)}
                        className="text-xs font-bold gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white cursor-pointer shadow-sm transition-all shrink-0"
                        title="Finalize decomposition quality and proceed to Effort Estimation."
                      >
                        <span>Proceed to Effort Estimation</span>
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Button>
                    ) : canProceedProvisionally ? (
                      <Button
                        size="sm"
                        onClick={() => handleProceedToEstimation(requirement)}
                        className={`text-xs font-bold gap-1.5 cursor-pointer shadow-sm transition-all shrink-0 ${
                          readiness === 'Needs Attention'
                            ? 'bg-amber-600 hover:bg-amber-700 text-white'
                            : 'bg-primary hover:bg-primary/90 text-primary-foreground'
                        }`}
                        title="Decomposition is not required to be perfect before estimation — review the suggestions, or proceed provisionally."
                      >
                        <span>
                          {readiness === 'Needs Attention' ? 'Proceed Anyway' : 'Proceed to Effort Estimation'}
                        </span>
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Button>
                    ) : (
                      <div
                        className="flex items-center gap-1.5"
                        title="Run a decomposition analysis first so the agent's feedback can guide your stories."
                      >
                        <Button
                          disabled
                          size="sm"
                          variant="outline"
                          className="text-xs gap-1.5 opacity-60 cursor-not-allowed bg-muted text-muted-foreground"
                        >
                          <Lock className="h-3.5 w-3.5" />
                          Run Analysis First
                        </Button>
                      </div>
                    )}
                  </div>
                </div>

                {/* Requirement Overview Card */}
                <Card className="p-5">
                  <div className="flex items-start justify-between gap-3 mb-3 flex-wrap">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-primary/10 text-primary">
                        {requirement.id}
                      </span>
                      <Badge tone={requirement.priority === 'High' ? 'danger' : requirement.priority === 'Medium' ? 'warning' : 'neutral'}>
                        {requirement.priority} Priority
                      </Badge>
                      {isDecompFinalized ? (
                        <Badge tone="success" className="text-xs font-semibold px-2 py-0.5 gap-1">
                          <ShieldCheck className="h-3 w-3" /> Decomposition Finalized &amp; Locked
                        </Badge>
                      ) : null}
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {scoreTrend !== null && scoreTrend !== 0 && (
                        <span
                          className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                            scoreTrend > 0
                              ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                              : 'bg-destructive/10 text-destructive'
                          }`}
                        >
                          {scoreTrend > 0 ? '↑ +' : '↓ '}{scoreTrend}% Delta
                        </span>
                      )}
                      {evaluation ? (
                        <>
                          {evaluation.stale && !evaluation.analysisFailed && (
                            <Badge tone="warning" className="text-[10px] gap-1">
                              <AlertTriangle className="h-3 w-3" /> Stale
                            </Badge>
                          )}
                          <Badge
                            tone={
                              evaluation.analysisFailed || evaluation.malformed
                                ? 'danger'
                                : evaluation.readiness === 'Ready'
                                  ? 'success'
                                  : evaluation.readiness === 'Needs Attention'
                                    ? 'warning'
                                    : 'primary'
                            }
                            className="text-xs font-semibold px-2.5 py-0.5"
                          >
                            {evaluation.analysisFailed
                              ? 'Analysis Failed'
                              : evaluation.malformed
                                ? 'Analysis Error'
                                : `${evaluation.score}/4 · ${evaluation.readiness}`}
                          </Badge>
                        </>
                      ) : (
                        <Badge tone="neutral" className="text-xs">Not Evaluated</Badge>
                      )}
                    </div>
                  </div>

                  {evaluation?.analysisFailed && (
                    <div className="mb-4 flex items-center gap-2.5 p-3 rounded-xl bg-destructive/10 border border-destructive/25 text-destructive">
                      <AlertTriangle className="h-4 w-4 shrink-0" />
                      <div className="flex-1">
                        <p className="text-xs font-bold">Analysis could not be completed — this is not a real result</p>
                        <p className="text-[11px] opacity-90 leading-tight">
                          A system error prevented the agent from evaluating coverage
                          {evaluation.failureReason ? ` (${evaluation.failureReason})` : ''}. The checklist and score
                          below are placeholders, not findings about your stories — please re-run analysis once the
                          issue is resolved.
                        </p>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={runAnalysis}
                        disabled={analyzing}
                        className="text-xs cursor-pointer gap-1.5 shrink-0 border-destructive/40"
                      >
                        <Brain className="h-3.5 w-3.5" /> Re-run now
                      </Button>
                    </div>
                  )}

                  {evaluation?.stale && !evaluation.analysisFailed && (
                    <div className="mb-4 flex items-center gap-2.5 p-3 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-800 dark:text-amber-300">
                      <AlertTriangle className="h-4 w-4 shrink-0" />
                      <p className="text-xs flex-1">
                        Stories changed since this analysis — showing the last result. Re-run analysis to refresh.
                      </p>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={runAnalysis}
                        disabled={analyzing}
                        className="text-xs cursor-pointer gap-1.5 shrink-0 border-amber-500/40"
                      >
                        <Brain className="h-3.5 w-3.5" /> Re-run now
                      </Button>
                    </div>
                  )}

                  {evaluation?.needsReviewReason && !evaluation.stale && !evaluation.analysisFailed && (
                    <div className="mb-4 flex items-center gap-2.5 p-3 rounded-xl bg-blue-500/10 border border-blue-500/25 text-blue-800 dark:text-blue-300">
                      <UserCheck className="h-4 w-4 shrink-0" />
                      <p className="text-xs">
                        Sent for supervisor review
                        {evaluation.needsReviewReason ? `: ${evaluation.needsReviewReason}` : '.'}
                      </p>
                    </div>
                  )}

                  {/* Finalized Approved Banner */}
                  {isDecompFinalized && (
                    <div className="mb-4 flex items-center justify-between gap-3 p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-emerald-800 dark:text-emerald-300">
                      <div className="flex items-center gap-2.5 min-w-0">
                        <div className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 shrink-0">
                          <ShieldCheck className="h-4 w-4" />
                        </div>
                        <div className="min-w-0">
                          <p className="text-xs font-bold truncate">Decomposition Quality Gate Approved &amp; Locked</p>
                          <p className="text-[11px] opacity-90 leading-tight">
                            User stories have passed coverage and INVEST verification and are frozen for Effort Estimation. Story editing is disabled.
                          </p>
                        </div>
                      </div>
                      <Link
                        to={team(`/planning/requirements/estimation?req=${requirement.id}`)}
                        className="text-xs font-semibold underline hover:no-underline shrink-0 flex items-center gap-1 text-emerald-700 dark:text-emerald-300"
                      >
                        View in Estimation <ArrowRight className="h-3 w-3" />
                      </Link>
                    </div>
                  )}

                  {/* Parent Requirement Specification Preview */}
                  <div>
                    <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-1">
                      Parent IEEE 830 Specification Baseline
                    </p>
                    <p className="text-xs text-foreground leading-relaxed p-3.5 rounded-xl bg-muted/30 border border-border/80 font-sans">
                      {requirement.description || requirement.title}
                    </p>
                  </div>
                </Card>

                {/* SECTION 1: User Stories Breakdown & Refinement (shown on 'all' or 'stories') */}
                {(mainTab === 'all' || mainTab === 'stories') && (
                  <div className="space-y-4">
                    {/* Story Action Bar */}
                    <Card className="p-4 flex items-center justify-between gap-3 flex-wrap">
                      <div>
                        <p className="text-xs font-bold text-foreground">
                          User Story Backlog ({stories.length} stor{stories.length === 1 ? 'y' : 'ies'})
                        </p>
                        <p className="text-[11px] text-muted-foreground mt-0.5">
                          {isDecompFinalized
                            ? 'All user stories are finalized and approved for Effort Estimation.'
                            : 'Write atomic stories covering all requirement capabilities. Re-analyze to verify INVEST compliance.'}
                        </p>
                      </div>

                      <div className="flex items-center gap-2 shrink-0">
                        <Button
                          size="sm"
                          variant={!analyzing && evaluation && !canRunAnalysis ? 'outline' : 'default'}
                          onClick={runAnalysis}
                          disabled={analyzing || stories.length === 0}
                          className="text-xs cursor-pointer gap-1.5"
                          title={
                            !analyzing && evaluation && !canRunAnalysis
                              ? 'Your stories haven’t changed since the last analysis — running again will reuse that result.'
                              : 'Evaluate current user stories against INVEST quality checks'
                          }
                        >
                          <Brain className={`h-3.5 w-3.5 ${analyzing ? 'animate-pulse' : ''}`} />
                          {analyzing
                            ? 'Analyzing with Agent…'
                            : evaluation && !canRunAnalysis
                              ? 'Up to Date — Re-run Anyway'
                              : 'Run Decomposition Analysis'}
                        </Button>

                        {!isDecompFinalized && !showNewStoryForm && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setGapInitialTitle('')
                              setShowNewStoryForm(true)
                            }}
                            className="text-xs cursor-pointer gap-1.5"
                          >
                            <Plus className="h-3.5 w-3.5" /> Write Story
                          </Button>
                        )}
                      </div>
                    </Card>

                    {/* New Story Form */}
                    {showNewStoryForm && !isDecompFinalized && (
                      <NewStoryForm
                        reqId={selectedReqId}
                        initialTitle={gapInitialTitle}
                        onDone={() => {
                          setShowNewStoryForm(false)
                          setGapInitialTitle('')
                        }}
                      />
                    )}

                    {/* Empty Stories State */}
                    {stories.length === 0 && !showNewStoryForm ? (
                      <EmptyState
                        title="No user stories created yet"
                        description="Write your first user story for this requirement using the agile INVEST framework. The agent will check its quality, including testability and independence."
                        actionLabel="Write a user story"
                        onAction={() => setShowNewStoryForm(true)}
                      />
                    ) : (
                      /* Stories List */
                      <div className="space-y-3.5">
                        {stories.map((story) => (
                          <StoryCard
                            key={story.id}
                            reqId={selectedReqId}
                            story={story}
                            readOnly={isDecompFinalized}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* SECTION 2: Coverage Analysis & INVEST Matrix (shown on 'all' or 'coverage') */}
                {(mainTab === 'all' || mainTab === 'coverage') && (
                  evaluation ? (
                    <CoverageAndInvestSection
                      evaluation={evaluation}
                      onAddGapStory={!isDecompFinalized ? handleAddGapStory : null}
                    />
                  ) : (
                    <Card className="p-6 text-center space-y-2">
                      <Sparkles className="h-6 w-6 text-muted-foreground mx-auto" />
                      <p className="text-xs font-semibold text-foreground">No User Story Quality Analysis Yet</p>
                      <p className="text-[11px] text-muted-foreground max-w-md mx-auto">
                        Add user stories and click "Run Decomposition Analysis" above to view the INVEST quality check.
                      </p>
                    </Card>
                  )
                )}

                {/* SECTION 3: Agent Evidence & Patterns (shown on 'all' or 'evidence') */}
                {(mainTab === 'all' || mainTab === 'evidence') && (
                  <div className="space-y-4">
                    <DecompositionEvidencePanel evaluation={evaluation} />

                    {/* DART Reasoning Flag Callout (if active) */}
                    {dartCases.length > 0 && (
                      <Card className="p-4 border-amber-500/30 bg-amber-500/5 animate-pulse-slow">
                        <div className="flex items-center gap-2 mb-2">
                          <Gavel className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                          <span className="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-300">
                            DART Activated — Ambiguity or Low Confidence Detected
                          </span>
                        </div>
                        {dartCases.map((c) => (
                          <div key={c.id} className="text-xs space-y-1.5 mb-2 last:mb-0">
                            <div className="flex items-center gap-2">
                              <Badge tone="warning">{c.categoryLabel}</Badge>
                              <span className="text-[10px] text-muted-foreground">{c.caseRef}</span>
                            </div>
                            {c.resolution?.actionableFeedback && (
                              <p className="text-xs text-foreground leading-snug">{c.resolution.actionableFeedback}</p>
                            )}
                            {c.consultation?.question && (
                              <p className="text-[11px] text-blue-700 dark:text-blue-400 italic">
                                "{c.consultation.question}"
                              </p>
                            )}
                          </div>
                        ))}
                      </Card>
                    )}
                  </div>
                )}

                {/* SECTION 4: Revision History (shown on 'all' or 'history') */}
                {(mainTab === 'all' || mainTab === 'history') && (
                  <RevisionHistorySection history={history} />
                )}
              </div>
            )
          ) : (
            <Card className="p-8 text-center text-xs text-muted-foreground">
              Select a requirement from the catalog on the left to begin story decomposition.
            </Card>
          )}
        </div>
      )}

      <DartButton context="decomposition" />

      {/* Supervisor Consultation Modal */}
      <SupervisorConsultationModal
        open={consultOpen}
        onOpenChange={setConsultOpen}
        requirements={requirements}
      />

      {/* INVEST Standards Guide Dialog */}
      <Dialog open={investGuideOpen} onOpenChange={setInvestGuideOpen}>
        <DialogContent className="sm:max-w-[640px] max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center gap-2 mb-1">
              <span className="p-1 rounded bg-primary/10 text-primary">
                <BookOpen className="h-4 w-4" />
              </span>
              <DialogTitle className="text-lg font-bold">INVEST Agile Story Quality Standards</DialogTitle>
            </div>
            <DialogDescription className="text-xs">
              Academic guidelines used by the Decomposition Agent to evaluate user stories and unlock the quality gate.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 pt-2">
            {INVEST_CRITERIA.map((criterion) => (
              <div key={criterion.key} className="p-3 rounded-lg border border-border bg-card space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-foreground flex items-center gap-2">
                    <span className="px-1.5 py-0.5 rounded bg-primary/10 text-primary font-mono text-[11px]">
                      {criterion.code}
                    </span>
                    {criterion.label}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">{criterion.description}</p>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      {/* Provisional Progression Confirmation Dialog */}
      <Dialog open={provisionalConfirmOpen} onOpenChange={setProvisionalConfirmOpen}>
        <DialogContent className="sm:max-w-[520px]">
          <DialogHeader>
            <div className="flex items-center gap-2 mb-1">
              <span className="p-1 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400">
                <AlertTriangle className="h-4 w-4" />
              </span>
              <DialogTitle className="text-lg font-bold">Proceed with Open Improvements?</DialogTitle>
            </div>
            <DialogDescription className="text-xs">
              {evaluation?.readinessReason ||
                'A few quality improvements are still suggested for this decomposition.'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 pt-1">
            {(evaluation?.studentFeedback || []).slice(0, 3).length > 0 && (
              <ul className="space-y-1.5">
                {evaluation.studentFeedback.slice(0, 3).map((bullet, i) => (
                  <li key={i} className="flex items-start gap-2 text-xs text-foreground">
                    <Circle className="h-2.5 w-2.5 mt-1 text-amber-500 shrink-0 fill-current" />
                    <span>{bullet}</span>
                  </li>
                ))}
              </ul>
            )}
            {storiesWithCoverageWarning.length > 0 && (
              <div className="p-2.5 rounded-lg border border-blue-500/25 bg-blue-500/5">
                <p className="text-[11px] font-bold text-blue-700 dark:text-blue-400 mb-1">
                  {storiesWithCoverageWarning.length} stor{storiesWithCoverageWarning.length === 1 ? 'y has' : 'ies have'} a task
                  coverage warning
                </p>
                <ul className="space-y-1">
                  {storiesWithCoverageWarning.slice(0, 3).map((e, i) => (
                    <li key={i} className="text-[11px] text-muted-foreground">{e.readinessReason}</li>
                  ))}
                </ul>
              </div>
            )}
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              You can proceed to Effort Estimation now and address these later, or go back and refine your stories
              first. Your stories and this analysis will not be lost either way.
            </p>
          </div>

          <div className="flex items-center justify-end gap-2 pt-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setProvisionalConfirmOpen(false)}
              className="text-xs cursor-pointer"
            >
              Go Back &amp; Refine
            </Button>
            <Button
              size="sm"
              onClick={() => {
                setProvisionalConfirmOpen(false)
                completeProceedToEstimation(requirement)
              }}
              className="text-xs font-bold cursor-pointer bg-amber-600 hover:bg-amber-700 text-white"
            >
              Proceed Anyway
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
