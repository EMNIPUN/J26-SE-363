import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Sparkles,
  Plus,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  ArrowRight,
  AlertTriangle,
  Gavel,
  Lock,
  Bug,
  PenLine,
} from 'lucide-react'
import PageHeader from '../../../../../shared/components/PageHeader.jsx'
import Card from '../../../../../shared/components/Card.jsx'
import Badge from '../../../../../shared/components/Badge.jsx'
import EmptyState from '../../../../../shared/components/EmptyState.jsx'
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
import WorkflowStepper from '../../../components/WorkflowStepper.jsx'
import DartButton from '../../../components/DartButton.jsx'
import RequirementListPanel from '../../../components/RequirementListPanel.jsx'
import { usePlanningData } from '../../../context/usePlanningData.js'
import { getArbitrationForRequirement } from '../../../data/mockData.js'
import { evaluateUserStory, STORY_STATUS_TONE } from '../../../utils.js'
import { showToast } from '@/shared/utils/toast.jsx'

let genIdCounter = 5000
function genId(prefix) {
  genIdCounter += 1
  return `${prefix}-${genIdCounter}`
}

const BUG_SEVERITY_TONE = { Low: 'neutral', Medium: 'warning', High: 'danger' }

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
              <button
                type="button"
                onClick={() => toggleBugStatus(reqId, storyId, b.id)}
                className="cursor-pointer"
              >
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

function StoryCard({ reqId, story }) {
  const { updateStoryText, evaluateStory, acceptStory, addTask } = usePlanningData()
  const [editing, setEditing] = useState(false)
  const [draftTitle, setDraftTitle] = useState(story.title)
  const [draftCriteria, setDraftCriteria] = useState(story.acceptanceCriteria)
  const [evaluating, setEvaluating] = useState(false)
  const [newTask, setNewTask] = useState('')

  const unlocked = story.status === 'Validated' || story.status === 'Accepted'

  function runEvaluation(title, acceptanceCriteria) {
    setEvaluating(true)
    setTimeout(() => {
      const issues = evaluateUserStory(title, acceptanceCriteria)
      evaluateStory(reqId, story.id, issues)
      setEvaluating(false)
      setEditing(false)
      showToast.success(issues.length > 0 ? 'AI evaluation complete — issues found' : 'AI evaluation complete — no issues', {
        description: issues.length > 0 ? `${issues.length} issue(s) to address on ${story.id}.` : `${story.id} is ready to break down.`,
      })
    }, 900)
  }

  function saveAndReEvaluate() {
    updateStoryText(reqId, story.id, { title: draftTitle, acceptanceCriteria: draftCriteria })
    runEvaluation(draftTitle, draftCriteria)
  }

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3 mb-2 flex-wrap">
        <span className="text-xs font-semibold text-muted-foreground">{story.id}</span>
        <Badge tone={STORY_STATUS_TONE[story.status]}>{story.status}</Badge>
      </div>

      {editing ? (
        <div className="space-y-2 mb-3">
          <Input value={draftTitle} onChange={(e) => setDraftTitle(e.target.value)} className="text-sm font-medium" placeholder="As a …, I want …, so that …" />
          <Textarea value={draftCriteria} onChange={(e) => setDraftCriteria(e.target.value)} className="text-xs" placeholder="Given …, when …, then …" />
          <div className="flex gap-2 justify-end">
            <Button size="sm" variant="outline" onClick={() => setEditing(false)}>Cancel</Button>
            <Button size="sm" onClick={saveAndReEvaluate} disabled={evaluating || !draftTitle.trim()}>
              <Sparkles className={`h-3.5 w-3.5 ${evaluating ? 'animate-pulse' : ''}`} />
              {evaluating ? 'Evaluating…' : 'Save & re-run AI evaluation'}
            </Button>
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

      {!editing && story.status === 'Needs Revision' && (
        <div className="mb-4 rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400">
              AI evaluation — {story.issues.length} issue{story.issues.length === 1 ? '' : 's'} found
            </span>
          </div>
          <div className="space-y-2.5">
            {story.issues.map((issue) => (
              <div key={issue.id} className="p-2.5 rounded-md bg-card border border-border">
                <div className="flex items-center gap-1.5 mb-1">
                  <Badge tone="warning">{issue.dimension}</Badge>
                </div>
                <p className="text-xs text-foreground"><span className="font-semibold">Problem: </span>{issue.problem}</p>
                <p className="text-xs text-muted-foreground mt-0.5"><span className="font-semibold text-foreground">Suggestion: </span>{issue.suggestion}</p>
              </div>
            ))}
          </div>
          <p className="text-[11px] text-muted-foreground mt-2.5">
            The agent won't rewrite this for you — edit the story above yourself, then re-run the evaluation.
          </p>
        </div>
      )}

      {!editing && (story.status === 'Validated' || story.status === 'Accepted') && (
        <div className="mb-4 flex items-center gap-2 p-2.5 rounded-lg border border-emerald-500/20 bg-emerald-500/5">
          <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />
          <span className="text-xs text-emerald-700 dark:text-emerald-400">AI evaluation passed — no issues found.</span>
        </div>
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
            Tasks, sub-tasks and bugs unlock once this story passes AI evaluation.
          </p>
        )
      )}
    </Card>
  )
}

function NewStoryForm({ reqId, onDone }) {
  const { addStory, evaluateStory } = usePlanningData()
  const [title, setTitle] = useState('')
  const [acceptanceCriteria, setAcceptanceCriteria] = useState('')
  const [submitting, setSubmitting] = useState(false)

  function submit() {
    if (!title.trim()) return
    const story = {
      id: genId('US'),
      title: title.trim(),
      acceptanceCriteria: acceptanceCriteria.trim(),
      evaluated: false,
      issues: [],
      status: 'Draft',
      tasks: [],
      bugs: [],
    }
    addStory(reqId, story)
    setSubmitting(true)
    setTimeout(() => {
      const issues = evaluateUserStory(story.title, story.acceptanceCriteria)
      evaluateStory(reqId, story.id, issues)
      setSubmitting(false)
      setTitle('')
      setAcceptanceCriteria('')
      showToast.success(issues.length > 0 ? 'AI evaluation complete — issues found' : 'AI evaluation complete — no issues', {
        description: issues.length > 0 ? `${issues.length} issue(s) to address on ${story.id}.` : `${story.id} is ready to break down.`,
      })
      onDone?.()
    }, 900)
  }

  return (
    <Card>
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Write a user story</p>
      <p className="text-xs text-muted-foreground mb-3">You write it — the Decomposition agent only reviews it and lists issues, it never rewrites your story.</p>
      <div className="space-y-2.5">
        <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="As a …, I want …, so that …" />
        <Textarea value={acceptanceCriteria} onChange={(e) => setAcceptanceCriteria(e.target.value)} placeholder="Given …, when …, then … (acceptance criteria)" />
      </div>
      <div className="flex justify-end mt-3">
        <Button size="sm" onClick={submit} disabled={submitting || !title.trim()} className="active:scale-[0.98]">
          <Sparkles className={`h-3.5 w-3.5 ${submitting ? 'animate-pulse' : ''}`} />
          {submitting ? 'AI is evaluating…' : 'Submit for AI evaluation'}
        </Button>
      </div>
    </Card>
  )
}

export default function Decomposition() {
  const { requirements, userStories, getStories } = usePlanningData()
  const passing = requirements.filter((r) => r.status === 'Passing')
  const [selectedReqId, setSelectedReqId] = useState(passing[0]?.id ?? requirements[0]?.id ?? '')
  const [showNewStoryForm, setShowNewStoryForm] = useState(false)

  const requirement = requirements.find((r) => r.id === selectedReqId)
  const isEligible = requirement?.status === 'Passing'
  const stories = isEligible ? getStories(selectedReqId) : []

  const allStories = passing.flatMap((r) => userStories[r.id] || [])
  const totalTasks = allStories.reduce((s, story) => s + story.tasks.length, 0)
  const validatedStories = allStories.filter((s) => s.status === 'Validated' || s.status === 'Accepted').length
  const decomposedReqCount = passing.filter((r) => (userStories[r.id] || []).length > 0).length

  function getDecompositionMeta(r) {
    if (r.status !== 'Passing') return { percent: 0, tone: 'neutral', locked: true }
    const s = userStories[r.id] || []
    if (s.length === 0) return { percent: 0, tone: 'neutral', locked: false }
    const accepted = s.filter((story) => story.status === 'Accepted').length
    const percent = Math.round((accepted / s.length) * 100)
    return { percent, tone: percent === 100 ? 'success' : 'warning', locked: false }
  }

  const dartCases = getArbitrationForRequirement(selectedReqId).filter((c) => c.status === 'Open')

  return (
    <div className="space-y-6">
      <PageHeader
        title="Requirement Decomposition"
        breadcrumb={['Planning', 'Requirements', 'Decomposition']}
        description="Only quality-gated requirements appear here. Write your own user stories — the AI reviews and flags issues, it doesn't write them for you."
      />

      <WorkflowStepper current="decomposition" />

      <Card className="flex flex-wrap items-center gap-x-8 gap-y-2 text-sm">
        <span className="text-muted-foreground">
          Requirements ready <strong className="text-foreground">{decomposedReqCount}/{passing.length}</strong>
        </span>
        <span className="text-muted-foreground">
          User stories <strong className="text-foreground">{allStories.length}</strong>
        </span>
        <span className="text-muted-foreground">
          Tasks <strong className="text-foreground">{totalTasks}</strong>
        </span>
        <span className="text-muted-foreground">
          Validated <strong className="text-foreground">{validatedStories}/{allStories.length}</strong>
        </span>
      </Card>

      <div className="grid grid-cols-1 xl:grid-cols-[280px_1fr_260px] gap-5 items-start">
        {/* Column 1 — Requirements */}
        <RequirementListPanel
          requirements={requirements}
          selectedId={selectedReqId}
          onSelect={(id) => { setSelectedReqId(id); setShowNewStoryForm(false) }}
          getItemMeta={getDecompositionMeta}
        />

        {/* Column 2 — Work breakdown */}
        <div className="space-y-4">
          {requirement && !isEligible && (
            <EmptyState
              icon={Lock}
              title={`${requirement.id} is blocked`}
              description={`This requirement is ${requirement.status === 'Failing' ? 'failing' : 'still under review'} in SRS Quality (${requirement.overallScore}%). It must pass the quality gate before it can be decomposed.`}
              actionLabel="Go to SRS Quality"
              onAction={() => { window.location.href = '/planning/requirements/srs-quality' }}
            />
          )}

          {requirement && isEligible && (
            <>
              <Card className="p-4 flex items-center justify-between gap-3 flex-wrap">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">{requirement.id}</p>
                  <h3 className="text-sm font-semibold text-foreground">{requirement.title}</h3>
                </div>
                <Link to="/planning/requirements/estimation" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline shrink-0">
                  Go to Effort Estimation <ArrowRight className="h-3 w-3" />
                </Link>
              </Card>

              {stories.length === 0 && !showNewStoryForm ? (
                <EmptyState
                  title="No user stories yet"
                  description="Write your own user story for this requirement — the AI will review it and point out issues, not write it for you."
                  actionLabel="Write a user story"
                  onAction={() => setShowNewStoryForm(true)}
                />
              ) : (
                <div className="space-y-4">
                  {stories.map((story) => (
                    <StoryCard key={story.id} reqId={selectedReqId} story={story} />
                  ))}

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
                </div>
              )}
            </>
          )}
        </div>

        {/* Column 3 — AI feedback summary */}
        <div className="space-y-4">
          <Card>
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-3">AI feedback</p>
            {!isEligible ? (
              <p className="text-xs text-muted-foreground">This requirement isn't decomposable yet — resolve its quality gate first.</p>
            ) : stories.length === 0 ? (
              <p className="text-xs text-muted-foreground">Write a user story to see AI evaluation feedback here.</p>
            ) : (
              <ul className="space-y-2.5">
                {stories.map((s) => (
                  <li key={s.id} className="flex items-start gap-2 text-xs">
                    {s.status === 'Needs Revision' ? (
                      <AlertTriangle className="h-3.5 w-3.5 text-amber-500 mt-0.5 shrink-0" />
                    ) : s.status === 'Validated' || s.status === 'Accepted' ? (
                      <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 mt-0.5 shrink-0" />
                    ) : (
                      <Sparkles className="h-3.5 w-3.5 text-muted-foreground mt-0.5 shrink-0" />
                    )}
                    <span className="text-foreground">
                      {s.id} — {s.status === 'Needs Revision' ? `${s.issues.length} issue(s) found` : s.status === 'Validated' || s.status === 'Accepted' ? 'No issues' : 'Awaiting evaluation'}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          {dartCases.length > 0 && (
            <Card className="border-primary/20">
              <div className="flex items-center gap-2 mb-1">
                <Gavel className="h-3.5 w-3.5 text-primary" />
                <span className="text-xs font-semibold uppercase tracking-wider text-primary">DART flag</span>
              </div>
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
    </div>
  )
}
