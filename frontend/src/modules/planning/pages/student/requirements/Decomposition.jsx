import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
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
  SkipForward,
  RefreshCcw,
  GraduationCap,
  BookOpen,
  UserCheck,
  Check,
  ShieldCheck,
} from 'lucide-react'
import { useTeamPath } from '@/shared/hooks/useTeamPath.js'
import Card from '../../../../../shared/components/Card.jsx'
import Badge from '../../../../../shared/components/Badge.jsx'
import EmptyState from '../../../../../shared/components/EmptyState.jsx'
import AvatarComp from '../../../../../shared/components/Avatar.jsx'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
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
import { getArbitrationForRequirement } from '../../../data/mockData.js'
import { COURSE_INFO } from '../../../data/lmsAcademicData.js'
import { runDecompositionAnalysis, INVEST_CRITERIA } from '../../../decompositionEngine.js'
import { showToast } from '@/shared/utils/toast.jsx'

let genIdCounter = 5000
function genId(prefix) {
  genIdCounter += 1
  return `${prefix}-${genIdCounter}`
}

const BUG_SEVERITY_TONE = { Low: 'neutral', Medium: 'warning', High: 'danger' }

const TOOL_ICON = {
  coverage_analyzer: Brain,
  invest_validator: CheckCircle2,
  pattern_retriever: Sparkles,
  decomposition_scorer: Gavel,
}

function TraceStep({ step }) {
  const Icon = step.tool ? TOOL_ICON[step.tool] || Brain : step.phase === 'skip' ? SkipForward : RefreshCcw
  const isSkip = step.phase === 'skip'
  const isReflect = step.phase === 'reflect'
  return (
    <div className={`p-2.5 rounded-lg border animate-fade-rise ${isSkip ? 'border-dashed border-border bg-muted/20' : isReflect ? 'border-primary/20 bg-primary/5' : 'border-border bg-muted/30'}`}>
      <div className="flex items-center gap-2 mb-1">
        <Icon className={`h-3.5 w-3.5 shrink-0 ${isSkip ? 'text-muted-foreground' : isReflect ? 'text-primary' : 'text-foreground'}`} />
        <span className="text-xs font-semibold text-foreground">
          Iteration {step.iteration}{step.tool ? ` — ${step.tool}` : isReflect ? ' — reflect' : ' — adaptive skip'}
        </span>
        {step.toolType && <span className="text-[10px] text-muted-foreground ml-auto">{step.toolType}</span>}
      </div>
      <p className="text-xs text-muted-foreground leading-snug mb-1">{step.reasoning}</p>
      <p className="text-xs text-foreground leading-snug font-medium">{step.result}</p>
    </div>
  )
}

function CoverageResults({ evaluation }) {
  return (
    <Card className="border-primary/20">
      <div className="flex items-center justify-between gap-3 mb-3 flex-wrap">
        <h3 className="text-sm font-semibold text-foreground">Decomposition analysis</h3>
        <Badge tone={evaluation.verdict === 'Validated' ? 'success' : 'warning'} className="text-sm px-2.5 py-1">
          Score {evaluation.score}/100 — {evaluation.verdict}
        </Badge>
      </div>
      <p className="text-xs text-muted-foreground mb-3">{evaluation.summary}</p>

      <div className="mb-3">
        <div className="flex items-center justify-between text-xs mb-1">
          <span className="font-medium text-foreground">Coverage</span>
          <span className="text-muted-foreground">{Math.round(evaluation.coverage * 100)}%</span>
        </div>
        <div className="h-2 rounded-full bg-muted overflow-hidden">
          <div className="h-full bg-primary rounded-full" style={{ width: `${Math.round(evaluation.coverage * 100)}%` }} />
        </div>
      </div>

      {evaluation.gaps.length > 0 ? (
        <div className="p-2.5 rounded-lg border border-amber-500/20 bg-amber-500/5 mb-3">
          <p className="text-xs font-semibold text-amber-700 dark:text-amber-400 mb-1">Missing from your stories</p>
          <ul className="text-xs text-foreground list-disc list-inside space-y-0.5">
            {evaluation.gaps.map((g) => (
              <li key={g.id}>{g.label}</li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="flex items-center gap-2 p-2.5 rounded-lg border border-emerald-500/20 bg-emerald-500/5 mb-3">
          <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
          <span className="text-xs text-emerald-700 dark:text-emerald-400">Every aspect of this requirement is represented.</span>
        </div>
      )}

      {evaluation.patternExamples && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Similar decompositions from the knowledge base
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {evaluation.patternExamples.map((ex) => (
              <div key={ex.id} className="p-2.5 rounded-lg border border-border bg-card">
                <p className="text-xs font-semibold text-foreground mb-1">{ex.title}</p>
                <ul className="text-[11px] text-muted-foreground list-disc list-inside space-y-0.5">
                  {ex.stories.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  )
}

function TaskRow({ reqId, storyId, task }) {
  const { addSubtask, toggleSubtask } = usePlanningData()
  const [expanded, setExpanded] = useState(true)
  const [newSubtask, setNewSubtask] = useState('')

  return (
    <div className="rounded-lg border border-border/70 bg-muted/20 p-3">
      <button type="button" onClick={() => setExpanded((v) => !v)} className="w-full flex items-center gap-2 text-left cursor-pointer">
        {expanded ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
        <span className="text-sm text-foreground flex-1">{task.title}</span>
        <Badge tone={task.status === 'Done' ? 'success' : task.status === 'In Progress' ? 'primary' : 'neutral'}>{task.status}</Badge>
      </button>
      {expanded && (
        <div className="mt-2 ml-5 space-y-1.5">
          {task.subtasks.map((st) => (
            <label key={st.id} className="flex items-center gap-2 text-xs cursor-pointer">
              <Checkbox checked={st.done} onCheckedChange={() => toggleSubtask(reqId, storyId, task.id, st.id)} />
              <span className={st.done ? 'text-muted-foreground line-through' : 'text-foreground'}>{st.title}</span>
            </label>
          ))}
          <div className="flex items-center gap-2 pt-1">
            <Input value={newSubtask} onChange={(e) => setNewSubtask(e.target.value)} placeholder="Add a sub-task…" className="h-7 text-xs" />
            <Button
              size="sm"
              variant="ghost"
              className="h-7 px-2"
              disabled={!newSubtask.trim()}
              onClick={() => {
                addSubtask(reqId, storyId, task.id, newSubtask.trim())
                setNewSubtask('')
              }}
            >
              <Plus className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

function BugSection({ reqId, storyId, bugs }) {
  const { addBug, toggleBugStatus } = usePlanningData()
  const [title, setTitle] = useState('')
  const [severity, setSeverity] = useState('Medium')

  return (
    <div className="space-y-2 mb-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Bugs</p>
      {bugs.length > 0 && (
        <ul className="space-y-1.5">
          {bugs.map((b) => (
            <li key={b.id} className="flex items-center gap-2 p-2 rounded-lg border border-border/70 bg-muted/20">
              <Bug className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
              <span className={`text-sm flex-1 ${b.status === 'Fixed' ? 'text-muted-foreground line-through' : 'text-foreground'}`}>
                {b.title}
              </span>
              <Badge tone={BUG_SEVERITY_TONE[b.severity]}>{b.severity}</Badge>
              <button type="button" onClick={() => toggleBugStatus(reqId, storyId, b.id)} className="cursor-pointer">
                <Badge tone={b.status === 'Fixed' ? 'success' : 'danger'}>{b.status}</Badge>
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="flex items-center gap-2">
        <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Report a bug…" className="h-8 text-xs" />
        <Select value={severity} onValueChange={setSeverity}>
          <SelectTrigger className="w-[100px] h-8 text-xs"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="Low">Low</SelectItem>
            <SelectItem value="Medium">Medium</SelectItem>
            <SelectItem value="High">High</SelectItem>
          </SelectContent>
        </Select>
        <Button
          size="sm"
          variant="outline"
          className="h-8 shrink-0"
          disabled={!title.trim()}
          onClick={() => {
            addBug(reqId, storyId, title.trim(), severity)
            setTitle('')
          }}
        >
          <Plus className="h-3.5 w-3.5" />
          Bug
        </Button>
      </div>
    </div>
  )
}

function InvestChecklist({ investResult }) {
  return (
    <div className="mb-4 space-y-1.5">
      <div className="flex items-center justify-between mb-1">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">INVEST</p>
        <Badge tone={investResult.overallPass ? 'success' : 'warning'}>
          {Object.keys(investResult).filter((k) => k !== 'overallPass' && investResult[k].pass).length}/6 pass
        </Badge>
      </div>
      {INVEST_CRITERIA.map(({ key, label }) => {
        const c = investResult[key]
        return (
          <div key={key} className="flex items-start gap-2 text-xs">
            {c.pass ? (
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 mt-0.5 shrink-0" />
            ) : (
              <XCircle className="h-3.5 w-3.5 text-destructive mt-0.5 shrink-0" />
            )}
            <div>
              <span className="font-medium text-foreground">{label}</span>
              <span className="text-muted-foreground"> — {c.note}</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function StoryCard({ reqId, story }) {
  const { updateStoryText, acceptStory, addTask } = usePlanningData()
  const [editing, setEditing] = useState(false)
  const [draftTitle, setDraftTitle] = useState(story.title)
  const [draftCriteria, setDraftCriteria] = useState(story.acceptanceCriteria)
  const [newTask, setNewTask] = useState('')

  const unlocked = story.investResult?.overallPass === true || story.status === 'Accepted'

  function saveEdits() {
    updateStoryText(reqId, story.id, { title: draftTitle, acceptanceCriteria: draftCriteria })
    setEditing(false)
    showToast.info('Story updated', { description: 'Run the decomposition analysis again to re-check coverage and INVEST.' })
  }

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3 mb-2 flex-wrap">
        <span className="text-xs font-semibold text-muted-foreground">{story.id}</span>
        <Badge tone={story.status === 'Accepted' ? 'primary' : story.investResult ? (story.investResult.overallPass ? 'success' : 'warning') : 'neutral'}>
          {story.status === 'Accepted' ? 'Accepted' : story.investResult ? (story.investResult.overallPass ? 'Well-formed' : 'Needs work') : 'Not yet evaluated'}
        </Badge>
      </div>

      {editing ? (
        <div className="space-y-2 mb-3">
          <Input value={draftTitle} onChange={(e) => setDraftTitle(e.target.value)} className="text-sm font-medium" placeholder="As a …, I want …, so that …" />
          <Textarea value={draftCriteria} onChange={(e) => setDraftCriteria(e.target.value)} className="text-xs" placeholder="Given …, when …, then …" />
          <div className="flex gap-2 justify-end">
            <Button size="sm" variant="outline" onClick={() => setEditing(false)}>Cancel</Button>
            <Button size="sm" onClick={saveEdits} disabled={!draftTitle.trim()}>Save</Button>
          </div>
        </div>
      ) : (
        <div className="mb-3">
          <p className="text-sm font-medium text-foreground">{story.title}</p>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{story.acceptanceCriteria}</p>
          <button
            type="button"
            className="text-xs text-primary hover:underline mt-1 cursor-pointer inline-flex items-center gap-1"
            onClick={() => {
              setDraftTitle(story.title)
              setDraftCriteria(story.acceptanceCriteria)
              setEditing(true)
            }}
          >
            <PenLine className="h-3 w-3" />
            Edit
          </button>
        </div>
      )}

      {!editing && story.investResult ? (
        <InvestChecklist investResult={story.investResult} />
      ) : (
        !editing && (
          <p className="text-xs text-muted-foreground italic mb-4">
            Not yet evaluated — run the decomposition analysis below to check INVEST and coverage.
          </p>
        )
      )}

      {unlocked ? (
        <>
          <div className="space-y-2 mb-3">
            {story.tasks.map((task) => (
              <TaskRow key={task.id} reqId={reqId} storyId={story.id} task={task} />
            ))}
          </div>

          <div className="flex items-center gap-2 mb-4">
            <Input value={newTask} onChange={(e) => setNewTask(e.target.value)} placeholder="Add a task…" className="h-8 text-xs" />
            <Button
              size="sm"
              variant="outline"
              className="h-8 shrink-0"
              disabled={!newTask.trim()}
              onClick={() => {
                addTask(reqId, story.id, newTask.trim())
                setNewTask('')
              }}
            >
              <Plus className="h-3.5 w-3.5" />
              Task
            </Button>
          </div>

          <BugSection reqId={reqId} storyId={story.id} bugs={story.bugs || []} />

          {story.status !== 'Accepted' && (
            <div className="flex justify-end">
              <Button size="sm" onClick={() => { acceptStory(reqId, story.id); showToast.success('Story accepted', { description: 'Ready for effort estimation.' }) }}>
                <CheckCircle2 className="h-3.5 w-3.5" />
                Accept — ready for estimation
              </Button>
            </div>
          )}
        </>
      ) : (
        !editing && (
          <p className="text-xs text-muted-foreground italic">
            Tasks, sub-tasks and bugs unlock once this story passes INVEST.
          </p>
        )
      )}
    </Card>
  )
}

function NewStoryForm({ reqId, onDone }) {
  const { addStory } = usePlanningData()
  const [title, setTitle] = useState('')
  const [acceptanceCriteria, setAcceptanceCriteria] = useState('')

  function submit() {
    if (!title.trim()) return
    const story = {
      id: genId('US'),
      title: title.trim(),
      acceptanceCriteria: acceptanceCriteria.trim(),
      investResult: null,
      status: 'Draft',
      tasks: [],
      bugs: [],
    }
    addStory(reqId, story)
    setTitle('')
    setAcceptanceCriteria('')
    onDone?.()
    showToast.success('Story added', { description: 'Run the decomposition analysis when your story set is ready.' })
  }

  return (
    <Card>
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Write a user story</p>
      <p className="text-xs text-muted-foreground mb-3">You write it — the Decomposition agent only checks coverage and INVEST, it never writes stories for you.</p>
      <div className="space-y-2.5">
        <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="As a …, I want …, so that …" />
        <Textarea value={acceptanceCriteria} onChange={(e) => setAcceptanceCriteria(e.target.value)} placeholder="Given …, when …, then … (acceptance criteria)" />
      </div>
      <div className="flex justify-end mt-3">
        <Button size="sm" onClick={submit} disabled={!title.trim()} className="active:scale-[0.98]">
          <Plus className="h-3.5 w-3.5" />
          Add story
        </Button>
      </div>
    </Card>
  )
}

export default function Decomposition() {
  const navigate = useNavigate()
  const team = useTeamPath()
  const { requirements, userStories, getStories, getDecompositionEvaluation, recordDecompositionAnalysis } = usePlanningData()
  const passing = requirements.filter((r) => r.status === 'Passing')
  const [selectedReqId, setSelectedReqId] = useState(passing[0]?.id ?? requirements[0]?.id ?? '')
  const [showNewStoryForm, setShowNewStoryForm] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [liveTrace, setLiveTrace] = useState([])

  const requirement = requirements.find((r) => r.id === selectedReqId)
  const isEligible = requirement?.status === 'Passing'
  const stories = isEligible ? getStories(selectedReqId) : []
  const evaluation = isEligible ? getDecompositionEvaluation(selectedReqId) : null
  const displayTrace = analyzing ? liveTrace : evaluation?.trace || []

  function getDecompositionMeta(r) {
    if (r.status !== 'Passing') return { percent: 0, tone: 'neutral', locked: true }
    const s = userStories[r.id] || []
    if (s.length === 0) return { percent: 0, tone: 'neutral', locked: false }
    const accepted = s.filter((story) => story.status === 'Accepted').length
    const percent = Math.round((accepted / s.length) * 100)
    return { percent, tone: percent === 100 ? 'success' : 'warning', locked: false }
  }

  function runAnalysis() {
    const result = runDecompositionAnalysis(requirement, stories)
    setAnalyzing(true)
    setLiveTrace([])
    result.trace.forEach((step, i) => {
      setTimeout(() => {
        setLiveTrace((prev) => [...prev, step])
        if (i === result.trace.length - 1) {
          recordDecompositionAnalysis(selectedReqId, result)
          setAnalyzing(false)
          showToast.success('Decomposition analysis complete', {
            description: `Coverage ${Math.round(result.coverage * 100)}% · score ${result.score}/100 (${result.verdict}).`,
          })
        }
      }, (i + 1) * 650)
    })
  }

  const [investGuideOpen, setInvestGuideOpen] = useState(false)
  const [consultOpen, setConsultOpen] = useState(false)

  const passingCount = passing.length
  const decomposedCount = passing.filter(
    (r) => (userStories[r.id] || []).length > 0 && (userStories[r.id] || []).every((s) => s.status === 'Accepted'),
  ).length
  const overallDecompPercent = passingCount ? Math.round((decomposedCount / passingCount) * 100) : 0

  const dartCases = getArbitrationForRequirement(selectedReqId).filter((c) => c.status === 'Open')

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
              INVEST Target: 100%
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
          {isEligible && (
            <Button
              size="sm"
              onClick={() => setShowNewStoryForm(true)}
              className="text-xs cursor-pointer gap-1.5"
            >
              <Plus className="h-3.5 w-3.5" /> + Write User Story
            </Button>
          )}
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
              <span>Methodology: <strong className="text-foreground">INVEST Agile Framework</strong></span>
            </div>

            <h2 className="text-lg sm:text-xl font-semibold text-foreground tracking-tight">
              Backlog Decomposition &amp; Story Traceability Studio
            </h2>

            <p className="text-xs text-muted-foreground leading-relaxed">
              Decompose quality-gated functional requirements into atomic, testable user stories with concrete acceptance criteria (Given / When / Then). The agent validates INVEST compliance and detects unrepresented requirement scope.
            </p>

            <div className="flex items-center gap-4 flex-wrap pt-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5 font-medium text-foreground">
                <AvatarComp name={COURSE_INFO.supervisor.name} size={20} className="ring-1 ring-border" />
                Supervisor: {COURSE_INFO.supervisor.name}
              </span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span className="flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                {passingCount} Eligible Requirements
              </span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span className="flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5 text-primary" />
                {decomposedCount} of {passingCount} Fully Decomposed
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

      <div className="grid grid-cols-1 xl:grid-cols-[280px_1fr_300px] gap-5 items-start">
        {/* Column 1 — Requirements (fixed while column 2 scrolls) */}
        <div className="xl:sticky xl:top-4 xl:self-start">
          <RequirementListPanel
            requirements={requirements}
            selectedId={selectedReqId}
            onSelect={(id) => { setSelectedReqId(id); setShowNewStoryForm(false) }}
            getItemMeta={getDecompositionMeta}
            maxHeight="calc(85vh - 90px)"
          />
        </div>

        {/* Column 2 — Work breakdown (the only part that scrolls) */}
        <div className="space-y-4 xl:max-h-[85vh] xl:overflow-y-auto column-scroll-contain xl:pr-1">
          {requirement && !isEligible && (
            <EmptyState
              icon={Lock}
              title={`${requirement.id} is blocked`}
              description={`This requirement is ${requirement.status === 'Failing' ? 'failing' : 'still under review'} in SRS Quality (${requirement.overallScore}%). It must pass the quality gate before it can be decomposed.`}
              actionLabel="Go to SRS Quality"
              onAction={() => navigate(team('/planning/requirements/srs-quality'))}
            />
          )}

          {requirement && isEligible && (
            <>
              <Card className="p-4 flex items-center justify-between gap-3 flex-wrap">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">{requirement.id}</p>
                  <h3 className="text-sm font-semibold text-foreground">{requirement.title}</h3>
                </div>
                <Link to={team('/planning/requirements/estimation')} className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline shrink-0">
                  Go to Effort Estimation <ArrowRight className="h-3 w-3" />
                </Link>
              </Card>

              {stories.length === 0 && !showNewStoryForm ? (
                <EmptyState
                  title="No user stories yet"
                  description="Write your own user story for this requirement — the agent will check coverage and INVEST, not write it for you."
                  actionLabel="Write a user story"
                  onAction={() => setShowNewStoryForm(true)}
                />
              ) : (
                <>
                  <Card className="flex items-center justify-between gap-3 flex-wrap">
                    <div>
                      <p className="text-sm font-medium text-foreground">Run decomposition analysis</p>
                      <p className="text-xs text-muted-foreground">Checks coverage across all {stories.length} stor{stories.length === 1 ? 'y' : 'ies'} and INVEST on each one.</p>
                    </div>
                    <Button size="sm" onClick={runAnalysis} disabled={analyzing || stories.length === 0} className="active:scale-[0.98] shrink-0">
                      <Brain className={`h-3.5 w-3.5 ${analyzing ? 'animate-pulse' : ''}`} />
                      {analyzing ? 'Analyzing…' : 'Run decomposition analysis'}
                    </Button>
                  </Card>

                  <div className="space-y-4">
                    {stories.map((story) => (
                      <StoryCard key={story.id} reqId={selectedReqId} story={story} />
                    ))}
                  </div>

                  {showNewStoryForm ? (
                    <NewStoryForm reqId={selectedReqId} onDone={() => setShowNewStoryForm(false)} />
                  ) : (
                    <div className="flex justify-end">
                      <Button size="sm" variant="outline" onClick={() => setShowNewStoryForm(true)} className="active:scale-[0.98]">
                        <Plus className="h-3.5 w-3.5" />
                        Write another user story
                      </Button>
                    </div>
                  )}
                </>
              )}
            </>
          )}
        </div>

        {/* Column 3 — AI feedback: reasoning trace, coverage/INVEST results, DART (fixed while column 2 scrolls) */}
        <div className="space-y-4 xl:sticky xl:top-4 xl:self-start xl:max-h-[85vh] xl:overflow-y-auto column-scroll-contain xl:pr-1">
          {!isEligible ? (
            <Card>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">AI feedback</p>
              <p className="text-xs text-muted-foreground">This requirement isn't decomposable yet — resolve its quality gate first.</p>
            </Card>
          ) : displayTrace.length === 0 && !evaluation ? (
            <Card>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">AI feedback</p>
              <p className="text-xs text-muted-foreground">Run the decomposition analysis to see coverage, INVEST and the agent's reasoning trace here.</p>
            </Card>
          ) : (
            <>
              {displayTrace.length > 0 && (
                <Card>
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">Agent reasoning trace</p>
                  <div className="space-y-2">
                    {displayTrace.map((step) => (
                      <TraceStep key={step.iteration} step={step} />
                    ))}
                  </div>
                </Card>
              )}

              {!analyzing && evaluation && <CoverageResults evaluation={evaluation} />}

              {!analyzing && evaluation && stories.length > 0 && (
                <Card>
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Story-by-story</p>
                  <ul className="space-y-1.5">
                    {stories.map((s) => (
                      <li key={s.id} className="flex items-center justify-between gap-2 text-xs">
                        <span className="text-foreground truncate">{s.id}</span>
                        {s.status === 'Accepted' ? (
                          <Badge tone="primary">Accepted</Badge>
                        ) : s.investResult ? (
                          <Badge tone={s.investResult.overallPass ? 'success' : 'warning'}>
                            {Object.keys(s.investResult).filter((k) => k !== 'overallPass' && s.investResult[k].pass).length}/6
                          </Badge>
                        ) : (
                          <Badge tone="neutral">Pending</Badge>
                        )}
                      </li>
                    ))}
                  </ul>
                </Card>
              )}
            </>
          )}

          {dartCases.length > 0 && (
            <Card className="border-primary/20">
              <div className="flex items-center gap-2 mb-1">
                <Gavel className="h-3.5 w-3.5 text-primary" />
                <span className="text-xs font-semibold uppercase tracking-wider text-primary">DART flag</span>
              </div>
              <p className="text-[11px] text-muted-foreground mb-2">
                Raised by the Quality Agent against the raw requirement text — before any stories were written.
              </p>
              {dartCases.map((c) => (
                <p key={c.id} className="text-xs text-muted-foreground leading-relaxed">
                  <Badge tone="warning" className="mr-1.5">{c.category}</Badge>
                  {c.title}
                </p>
              ))}
            </Card>
          )}
        </div>
      </div>

      <DartButton context="decomposition" />

      {/* Supervisor Consultation Modal */}
      <SupervisorConsultationModal
        open={consultOpen}
        onOpenChange={setConsultOpen}
        requirements={requirements}
      />

      {/* INVEST Standards Guide Dialog */}
      <Dialog open={investGuideOpen} onOpenChange={setInvestGuideOpen}>
        <DialogContent className="sm:max-w-[620px] max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center gap-2 mb-1">
              <span className="p-1 rounded bg-primary/10 text-primary">
                <BookOpen className="h-4 w-4" />
              </span>
              <DialogTitle className="text-lg font-bold">INVEST User Story Quality Standards</DialogTitle>
            </div>
            <DialogDescription className="text-xs">
              Academic guidelines used by the Decomposition Agent to validate agile user story quality.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 text-xs">
            {INVEST_CRITERIA.map((crit) => (
              <div key={crit.key} className="p-3 rounded-xl border border-border bg-card space-y-1">
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-foreground text-xs flex items-center gap-1.5">
                    <Check className="h-3.5 w-3.5 text-primary" /> {crit.label}
                  </h4>
                  <Badge tone="primary" className="text-[10px] px-1.5 py-0">INVEST Principle</Badge>
                </div>
                <p className="text-muted-foreground text-[11px] leading-relaxed">{crit.description}</p>
                <div className="p-2 rounded bg-muted/40 text-[11px] text-foreground font-medium border border-border/50">
                  <span className="text-primary font-bold">Standard: </span>
                  {crit.key === 'independent' && 'Avoid temporal or implementation couplings to other unfinished stories.'}
                  {crit.key === 'negotiable' && 'Describe what the user wants and why, without prescribing immutable UI/DB mechanics.'}
                  {crit.key === 'valuable' && 'Articulate clear business or pedagogical value for students, tutors, or supervisors.'}
                  {crit.key === 'estimable' && 'Provide enough clarity for team members to assign Fibonacci story points.'}
                  {crit.key === 'small' && 'Scope the deliverable so it can be designed, coded, and verified within one sprint.'}
                  {crit.key === 'testable' && 'Formulate clear Given / When / Then acceptance criteria.'}
                </div>
              </div>
            ))}
          </div>

          <DialogFooter className="pt-2">
            <Button size="sm" onClick={() => setInvestGuideOpen(false)} className="text-xs cursor-pointer">
              Understood
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
