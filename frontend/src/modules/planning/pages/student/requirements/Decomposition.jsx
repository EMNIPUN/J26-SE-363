import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Sparkles,
  Plus,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  ArrowLeftRight,
  Check,
  X,
  ArrowRight,
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
import { usePlanningData } from '../../../context/usePlanningData.js'
import { showToast } from '@/shared/utils/toast.jsx'

let genIdCounter = 5000
function genId(prefix) {
  genIdCounter += 1
  return `${prefix}-${genIdCounter}`
}

function TaskRow({ reqId, storyId, task }) {
  const { addSubtask, toggleSubtask } = usePlanningData()
  const [expanded, setExpanded] = useState(true)
  const [newSubtask, setNewSubtask] = useState('')

  return (
    <div className="rounded-lg border border-border/70 bg-muted/20 p-3">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-2 text-left cursor-pointer"
      >
        {expanded ? <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" /> : <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />}
        <span className="text-sm text-foreground flex-1">{task.title}</span>
        <Badge tone={task.status === 'Done' ? 'success' : task.status === 'In Progress' ? 'primary' : 'neutral'}>
          {task.status}
        </Badge>
      </button>
      {expanded && (
        <div className="mt-2 ml-5 space-y-1.5">
          {task.subtasks.map((st) => (
            <label key={st.id} className="flex items-center gap-2 text-xs cursor-pointer">
              <Checkbox
                checked={st.done}
                onCheckedChange={() => toggleSubtask(reqId, storyId, task.id, st.id)}
              />
              <span className={st.done ? 'text-muted-foreground line-through' : 'text-foreground'}>{st.title}</span>
            </label>
          ))}
          <div className="flex items-center gap-2 pt-1">
            <Input
              value={newSubtask}
              onChange={(e) => setNewSubtask(e.target.value)}
              placeholder="Add a sub-task…"
              className="h-7 text-xs"
            />
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

function StoryCard({ reqId, story }) {
  const { updateStory, applyAgentSuggestion, dismissAgentSuggestion, acceptStory, addTask } = usePlanningData()
  const [editing, setEditing] = useState(false)
  const [draftTitle, setDraftTitle] = useState(story.title)
  const [draftCriteria, setDraftCriteria] = useState(story.acceptanceCriteria)
  const [newTask, setNewTask] = useState('')

  function saveEdits() {
    updateStory(reqId, story.id, { title: draftTitle, acceptanceCriteria: draftCriteria })
    setEditing(false)
    showToast.success('User story updated')
  }

  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-3 mb-2 flex-wrap">
        <span className="text-xs font-semibold text-muted-foreground">{story.id}</span>
        <Badge tone={story.status === 'Accepted' ? 'success' : 'neutral'}>{story.status}</Badge>
      </div>

      {editing ? (
        <div className="space-y-2 mb-3">
          <Input value={draftTitle} onChange={(e) => setDraftTitle(e.target.value)} className="text-sm font-medium" />
          <Textarea value={draftCriteria} onChange={(e) => setDraftCriteria(e.target.value)} className="text-xs" />
          <div className="flex gap-2 justify-end">
            <Button size="sm" variant="outline" onClick={() => setEditing(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={saveEdits}>
              Save
            </Button>
          </div>
        </div>
      ) : (
        <div className="mb-3">
          <p className="text-sm font-medium text-foreground">{story.title}</p>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{story.acceptanceCriteria}</p>
          <button
            type="button"
            className="text-xs text-primary hover:underline mt-1 cursor-pointer"
            onClick={() => {
              setDraftTitle(story.title)
              setDraftCriteria(story.acceptanceCriteria)
              setEditing(true)
            }}
          >
            Edit
          </button>
        </div>
      )}

      {story.agentSuggestion && (
        <div className="mb-4 rounded-lg border border-primary/20 bg-primary/5 p-3">
          <div className="flex items-center gap-2 mb-2">
            <ArrowLeftRight className="h-3.5 w-3.5 text-primary" />
            <span className="text-xs font-semibold uppercase tracking-wider text-primary">Agent-suggested improvement</span>
            <span className="text-xs text-muted-foreground ml-auto">{story.agentSuggestion.confidence}% confidence</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-2">
            <div className="p-2.5 rounded-md border border-border bg-card">
              <p className="text-xs font-semibold text-muted-foreground mb-1">Your version</p>
              <p className="text-xs text-foreground leading-snug">{story.title}</p>
            </div>
            <div className="p-2.5 rounded-md border border-primary/30 bg-card">
              <p className="text-xs font-semibold text-primary mb-1">Agent suggestion</p>
              <p className="text-xs text-foreground leading-snug">{story.agentSuggestion.title}</p>
            </div>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed mb-3">{story.agentSuggestion.rationale}</p>
          <div className="flex gap-2 justify-end">
            <Button size="sm" variant="outline" onClick={() => dismissAgentSuggestion(reqId, story.id)}>
              <X className="h-3.5 w-3.5" />
              Keep mine
            </Button>
            <Button size="sm" onClick={() => applyAgentSuggestion(reqId, story.id)}>
              <Check className="h-3.5 w-3.5" />
              Apply suggestion
            </Button>
          </div>
        </div>
      )}

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

      {story.status !== 'Accepted' && (
        <div className="flex justify-end">
          <Button size="sm" onClick={() => { acceptStory(reqId, story.id); showToast.success('Story accepted', { description: 'Ready for effort estimation.' }) }}>
            <CheckCircle2 className="h-3.5 w-3.5" />
            Accept — ready for estimation
          </Button>
        </div>
      )}
    </Card>
  )
}

export default function Decomposition() {
  const { requirements, getStories, generateStories } = usePlanningData()
  const passing = requirements.filter((r) => r.status === 'Passing')
  const [selectedReqId, setSelectedReqId] = useState(passing[0]?.id ?? '')
  const [generating, setGenerating] = useState(false)

  const requirement = requirements.find((r) => r.id === selectedReqId)
  const stories = selectedReqId ? getStories(selectedReqId) : []

  function generateBreakdown() {
    setGenerating(true)
    setTimeout(() => {
      const s1 = genId('US')
      generateStories(selectedReqId, [
        {
          id: s1,
          title: `As a user, I want the core behavior of "${requirement.title.slice(0, 40)}${requirement.title.length > 40 ? '…' : ''}" to work end-to-end`,
          acceptanceCriteria: 'Given the described trigger, when it occurs, then the expected outcome is produced and observable.',
          status: 'Draft',
          agentSuggestion: {
            title: `As a user, I want ${requirement.title.slice(0, 30).toLowerCase()}… with clear error handling when it fails`,
            acceptanceCriteria: 'Given the trigger, when it occurs, then the outcome is produced; when it fails, an actionable error is shown.',
            rationale: 'Your version only covers the happy path — add the failure case so QA has something to test against.',
            confidence: 70 + Math.floor(Math.random() * 20),
          },
          tasks: [
            { id: genId('T'), title: 'Implement core behavior', status: 'Todo', subtasks: [] },
            { id: genId('T'), title: 'Add tests for happy path + edge cases', status: 'Todo', subtasks: [] },
          ],
        },
      ])
      setGenerating(false)
      showToast.ai('Decomposition Agent finished', {
        description: `Generated a user story for ${selectedReqId}.`,
      })
    }, 900)
  }

  if (passing.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Requirement Decomposition"
          breadcrumb={['Planning', 'Requirements', 'Decomposition']}
          description="Breaks a quality-gated requirement down into user stories, tasks and sub-tasks."
        />
        <EmptyState
          title="No requirements have passed the quality gate yet"
          description="Decomposition only unlocks for requirements that clear the SRS Quality gate. Fix or re-run a requirement there first."
          actionLabel="Go to SRS Quality"
          onAction={() => { window.location.href = '/planning/requirements/srs-quality' }}
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Requirement Decomposition"
        breadcrumb={['Planning', 'Requirements', 'Decomposition']}
        description="Only quality-gated requirements appear here. Break each one into user stories, tasks and sub-tasks."
        actions={
          <Select value={selectedReqId} onValueChange={setSelectedReqId}>
            <SelectTrigger className="w-[280px]">
              <SelectValue placeholder="Select a requirement" />
            </SelectTrigger>
            <SelectContent>
              {passing.map((r) => (
                <SelectItem key={r.id} value={r.id}>
                  {r.id} — {r.title.slice(0, 34)}
                  {r.title.length > 34 ? '…' : ''}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        }
      />

      {requirement && (
        <>
          <Card className="p-4 flex items-center justify-between gap-3 flex-wrap">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">{requirement.id}</p>
              <h3 className="text-sm font-semibold text-foreground">{requirement.title}</h3>
            </div>
            <Link
              to="/planning/requirements/estimation"
              className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline shrink-0"
            >
              Go to Effort Estimation <ArrowRight className="h-3 w-3" />
            </Link>
          </Card>

          {stories.length === 0 && !generating ? (
            <EmptyState
              title="No user stories yet"
              description="Generate a breakdown with the Decomposition agent to get user stories, tasks and sub-tasks for this requirement."
              actionLabel="Generate breakdown"
              onAction={generateBreakdown}
            />
          ) : (
            <div className="space-y-4">
              <div className="flex justify-end">
                <Button size="sm" variant="outline" onClick={generateBreakdown} disabled={generating} className="active:scale-[0.98]">
                  <Sparkles className={`h-3.5 w-3.5 ${generating ? 'animate-pulse' : ''}`} />
                  {generating ? 'Generating…' : 'Generate another story'}
                </Button>
              </div>
              {stories.map((story) => (
                <StoryCard key={story.id} reqId={selectedReqId} story={story} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
