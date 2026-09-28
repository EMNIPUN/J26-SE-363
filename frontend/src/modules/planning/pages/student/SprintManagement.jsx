import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  ListTodo,
  LayoutGrid,
  BarChart3,
  Layers,
  AlertTriangle,
  Users,
  Clock,
  CheckCircle2,
  Circle,
  Search,
  ChevronDown,
  Bookmark,
  SquareCheck,
  TrendingDown,
  Gauge,
  GraduationCap,
  UserCheck,
  Sparkles,
  BookOpen,
} from 'lucide-react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  Legend,
} from 'recharts'
import Card from '../../../../shared/components/Card.jsx'
import Badge from '../../../../shared/components/Badge.jsx'
import Button from '../../../../shared/components/Button.jsx'
import StatCard from '../../../../shared/components/StatCard.jsx'
import EmptyState from '../../../../shared/components/EmptyState.jsx'
import AvatarComp from '../../../../shared/components/Avatar.jsx'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import WorkflowStepper from '../../components/WorkflowStepper.jsx'
import DartButton from '../../components/DartButton.jsx'
import SupervisorConsultationModal from '../../components/SupervisorConsultationModal.jsx'
import { COURSE_INFO } from '../../data/lmsAcademicData.js'
import { usePlanningData } from '../../context/usePlanningData.js'
import { KANBAN_COLUMNS, BURNDOWN_SEED, VELOCITY_TREND } from '../../data/mockData.js'
import { showToast } from '@/shared/utils/toast.jsx'

const STATUS_TONE = { Todo: 'neutral', 'In Progress': 'primary', Blocked: 'danger', Done: 'success' }

const COLUMN_META = {
  Todo: { icon: Circle, iconClass: 'text-muted-foreground', bg: 'bg-muted/30' },
  'In Progress': { icon: null, iconClass: 'bg-primary', bg: 'bg-primary/5' },
  Blocked: { icon: AlertTriangle, iconClass: 'text-destructive', bg: 'bg-destructive/5' },
  Done: { icon: CheckCircle2, iconClass: 'text-emerald-500', bg: 'bg-emerald-500/5' },
}

const EPIC_CHIP_COLORS = [
  'bg-purple-100 text-purple-700 dark:bg-purple-950/40 dark:text-purple-400',
  'bg-blue-100 text-blue-700 dark:bg-blue-950/40 dark:text-blue-400',
  'bg-amber-100 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400',
  'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400',
  'bg-rose-100 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400',
  'bg-cyan-100 text-cyan-700 dark:bg-cyan-950/40 dark:text-cyan-400',
]

function epicChipClass(reqId, requirements) {
  const idx = requirements.findIndex((r) => r.id === reqId)
  return EPIC_CHIP_COLORS[(idx >= 0 ? idx : 0) % EPIC_CHIP_COLORS.length]
}

function memberFor(teamMembers, id) {
  return teamMembers.find((m) => m.id === id) || null
}

function formatShortDate(iso) {
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function IssueTypeIcon({ isStory, className = 'h-3.5 w-3.5' }) {
  return isStory ? (
    <Bookmark className={`${className} text-emerald-500 shrink-0`} />
  ) : (
    <SquareCheck className={`${className} text-primary shrink-0`} />
  )
}

/* ------------------------------------------------------------------ */
/* Issue card (Kanban board)                                          */
/* ------------------------------------------------------------------ */
function IssueCard({ task, member, requirements, onOpen }) {
  return (
    <div
      draggable
      onDragStart={(e) => e.dataTransfer.setData('text/plain', task.id)}
      onClick={() => onOpen(task)}
      className={`p-2.5 rounded-md bg-card card-elevated border border-border/60 cursor-grab active:cursor-grabbing card-hover-lift ${
        task.status === 'Blocked' ? 'border-l-2 border-l-destructive' : ''
      }`}
    >
      <p className="text-xs text-foreground leading-snug mb-2">{task.title}</p>
      {task.requirementId && (
        <span className={`inline-block text-[10px] font-medium px-1.5 py-0.5 rounded mb-2 ${epicChipClass(task.requirementId, requirements)}`}>
          {task.requirementId}
        </span>
      )}
      {task.status === 'Blocked' && task.blockedReason && (
        <p className="text-[10px] text-destructive mb-2 flex items-start gap-1">
          <AlertTriangle className="h-2.5 w-2.5 mt-0.5 shrink-0" />
          <span className="line-clamp-2">{task.blockedReason}</span>
        </p>
      )}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <IssueTypeIcon isStory={Boolean(task.storyId)} className="h-3 w-3" />
          <span className="text-[10px] font-medium text-muted-foreground">{task.id}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-5 min-w-5 px-1 rounded-full bg-muted text-[10px] font-semibold text-foreground flex items-center justify-center">
            {task.points}
          </span>
          {member ? (
            <AvatarComp name={member.name} size={22} />
          ) : (
            <span className="h-[22px] w-[22px] rounded-full border border-dashed border-border shrink-0" />
          )}
        </div>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Kanban columns — used for both the plain board and each swimlane   */
/* ------------------------------------------------------------------ */
function KanbanColumns({ tasks, teamMembers, requirements, onOpen, moveKanbanTask, assignKanbanTask, swimlaneAssigneeId, minHeight = 360 }) {
  const [dragOverCol, setDragOverCol] = useState(null)

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
      {KANBAN_COLUMNS.map((col) => {
        const colTasks = tasks.filter((t) => t.status === col.key)
        const points = colTasks.reduce((sum, t) => sum + t.points, 0)
        const meta = COLUMN_META[col.key]
        const Icon = meta.icon
        return (
          <div
            key={col.key}
            onDragOver={(e) => { e.preventDefault(); setDragOverCol(col.key) }}
            onDragLeave={() => setDragOverCol((c) => (c === col.key ? null : c))}
            onDrop={(e) => {
              e.preventDefault()
              const taskId = e.dataTransfer.getData('text/plain')
              if (taskId) {
                moveKanbanTask(taskId, col.key)
                if (swimlaneAssigneeId !== undefined) assignKanbanTask(taskId, swimlaneAssigneeId)
              }
              setDragOverCol(null)
            }}
            style={{ minHeight }}
            className={`rounded-lg p-2.5 space-y-2 transition-all ${meta.bg} ${
              dragOverCol === col.key ? 'ring-2 ring-primary ring-offset-1 ring-offset-background' : ''
            }`}
          >
            <div className="flex items-center justify-between px-0.5">
              <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                {Icon ? <Icon className={`h-3 w-3 shrink-0 ${meta.iconClass}`} /> : <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${meta.iconClass}`} />}
                {col.label} <span className="text-muted-foreground font-normal">{colTasks.length}</span>
              </span>
              <span className="text-[11px] text-muted-foreground">{points} SP</span>
            </div>
            {colTasks.map((task) => (
              <IssueCard key={task.id} task={task} member={memberFor(teamMembers, task.assigneeId)} requirements={requirements} onOpen={onOpen} />
            ))}
            {colTasks.length === 0 && (
              <div className="text-[11px] text-muted-foreground text-center py-4 border border-dashed border-border rounded-md">Drop here</div>
            )}
          </div>
        )
      })}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Flat issue row — shared between the Board "List" view and Backlog  */
/* ------------------------------------------------------------------ */
function IssueRow({ id, title, requirementId, requirements, points, statusLabel, statusTone, member, isStory, onClick }) {
  return (
    <div onClick={onClick} className="flex items-center gap-3 px-3 py-2 hover:bg-muted/40 transition-colors cursor-pointer">
      <IssueTypeIcon isStory={isStory} />
      <span className="text-xs text-muted-foreground font-medium w-20 shrink-0 truncate">{id}</span>
      <span className="text-sm text-foreground truncate flex-1 min-w-0">{title}</span>
      {requirementId && (
        <span className={`hidden sm:inline-block text-[10px] font-medium px-1.5 py-0.5 rounded shrink-0 ${epicChipClass(requirementId, requirements)}`}>
          {requirementId}
        </span>
      )}
      {points != null && (
        <span className="h-5 min-w-5 px-1 rounded-full bg-muted text-[10px] font-semibold text-foreground flex items-center justify-center shrink-0">
          {points}
        </span>
      )}
      {statusLabel && (
        <Badge tone={statusTone} className="shrink-0">{statusLabel}</Badge>
      )}
      {member ? (
        <AvatarComp name={member.name} size={24} />
      ) : (
        <span className="h-6 w-6 rounded-full border border-dashed border-border shrink-0" />
      )}
    </div>
  )
}

function TaskDetailDialog({ task, onClose, teamMembers, onAssign, onMove }) {
  if (!task) return null
  const member = memberFor(teamMembers, task.assigneeId)
  return (
    <Dialog open={!!task} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{task.id}</DialogTitle>
          <DialogDescription>{task.title}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-xs text-muted-foreground mb-1">Requirement</p>
              <p className="text-foreground font-medium">{task.requirementId || '—'}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Story points</p>
              <p className="text-foreground font-medium">{task.points} SP</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Status</p>
              <Select value={task.status} onValueChange={(v) => onMove(task.id, v)}>
                <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {KANBAN_COLUMNS.map((c) => <SelectItem key={c.key} value={c.key}>{c.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Assignee</p>
              <Select value={task.assigneeId || 'unassigned'} onValueChange={(v) => onAssign(task.id, v === 'unassigned' ? null : v)}>
                <SelectTrigger className="w-full"><SelectValue>{member ? member.name : 'Unassigned'}</SelectValue></SelectTrigger>
                <SelectContent>
                  <SelectItem value="unassigned">Unassigned</SelectItem>
                  {teamMembers.map((m) => <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
          </div>

          {task.blockedReason && (
            <div className="p-3 rounded-lg border border-destructive/20 bg-destructive/5">
              <p className="text-xs font-semibold text-destructive mb-1">Blocked — dependency</p>
              <p className="text-xs text-muted-foreground">{task.blockedReason}</p>
            </div>
          )}

          <div>
            <p className="text-xs font-semibold text-muted-foreground mb-2">Team workload this sprint</p>
            <div className="space-y-2">
              {teamMembers.map((m) => (
                <div key={m.id} className="flex items-center gap-2">
                  <AvatarComp name={m.name} size={22} />
                  <span className="text-xs text-foreground w-24 truncate">{m.name.split(' ')[0]}</span>
                  <Progress value={Math.min(100, (m.currentLoad / m.capacity) * 100)} className={`h-1.5 flex-1 ${m.currentLoad > m.capacity ? '[&>div]:bg-destructive' : ''}`} />
                  <span className={`text-xs w-16 text-right shrink-0 ${m.currentLoad > m.capacity ? 'text-destructive font-medium' : 'text-muted-foreground'}`}>
                    {m.currentLoad}/{m.capacity} SP
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

/* ------------------------------------------------------------------ */
/* Board tab — toolbar (search / assignee filter / group by / view    */
/* toggle / complete sprint), then columns or swimlanes or list        */
/* ------------------------------------------------------------------ */
function BoardToolbar({ search, setSearch, groupBy, setGroupBy, teamMembers, filterAssignees, toggleAssignee, viewMode, setViewMode, onCompleteSprint }) {
  return (
    <div className="flex items-center gap-3 flex-wrap mb-4">
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
        <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search board" className="pl-8 h-8 text-xs w-[170px]" />
      </div>

      <div className="flex -space-x-2">
        {teamMembers.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => toggleAssignee(m.id)}
            title={m.name}
            className={`rounded-full cursor-pointer transition-transform outline-none ${filterAssignees.has(m.id) ? 'ring-2 ring-primary z-10 scale-105' : 'hover:scale-105'}`}
          >
            <AvatarComp name={m.name} size={28} className="ring-2 ring-card" />
          </button>
        ))}
      </div>

      <div className="ml-auto flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button type="button" className="flex items-center gap-1.5 px-2.5 h-8 rounded-md border border-border text-xs font-medium text-foreground hover:bg-accent transition-colors cursor-pointer">
              Group: {groupBy === 'assignee' ? 'Assignee' : 'None'} <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuRadioGroup value={groupBy} onValueChange={setGroupBy}>
              <DropdownMenuRadioItem value="none">None</DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="assignee">Assignee</DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>

        <div className="flex items-center rounded-md border border-border overflow-hidden">
          <button
            type="button"
            onClick={() => setViewMode('board')}
            title="Board view"
            className={`h-8 w-8 flex items-center justify-center cursor-pointer transition-colors ${viewMode === 'board' ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-accent'}`}
          >
            <LayoutGrid className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setViewMode('list')}
            title="List view"
            className={`h-8 w-8 flex items-center justify-center cursor-pointer transition-colors border-l border-border ${viewMode === 'list' ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-accent'}`}
          >
            <ListTodo className="h-3.5 w-3.5" />
          </button>
        </div>

        <Button size="sm" onClick={onCompleteSprint}>Complete sprint</Button>
      </div>
    </div>
  )
}

function BoardView() {
  const { requirements, kanbanTasks, teamMembers, projectInfo, moveKanbanTask, assignKanbanTask } = usePlanningData()
  const [search, setSearch] = useState('')
  const [groupBy, setGroupBy] = useState('none')
  const [filterAssignees, setFilterAssignees] = useState(() => new Set())
  const [viewMode, setViewMode] = useState('board')
  const [openTask, setOpenTask] = useState(null)

  const toggleAssignee = (id) => {
    setFilterAssignees((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const totalPoints = kanbanTasks.reduce((s, t) => s + t.points, 0)
  const donePoints = kanbanTasks.filter((t) => t.status === 'Done').reduce((s, t) => s + t.points, 0)

  const filteredTasks = kanbanTasks.filter((t) => {
    const q = search.trim().toLowerCase()
    if (q && !(t.title.toLowerCase().includes(q) || t.id.toLowerCase().includes(q))) return false
    if (filterAssignees.size > 0 && !filterAssignees.has(t.assigneeId)) return false
    return true
  })

  const membersWithLoad = teamMembers.map((m) => ({
    ...m,
    currentLoad: kanbanTasks.filter((t) => t.assigneeId === m.id && t.status !== 'Done').reduce((s, t) => s + t.points, 0),
  }))

  function handleCompleteSprint() {
    showToast.success('Sprint marked complete', {
      description: `${donePoints} of ${totalPoints} SP were completed in ${projectInfo.sprintName}.`,
    })
  }

  return (
    <>
      <BoardToolbar
        search={search}
        setSearch={setSearch}
        groupBy={groupBy}
        setGroupBy={setGroupBy}
        teamMembers={teamMembers}
        filterAssignees={filterAssignees}
        toggleAssignee={toggleAssignee}
        viewMode={viewMode}
        setViewMode={setViewMode}
        onCompleteSprint={handleCompleteSprint}
      />

      {viewMode === 'list' ? (
        filteredTasks.length === 0 ? (
          <EmptyState title="No matching issues" description="Try a different search term or clear the assignee filter." />
        ) : (
          <Card className="p-0 overflow-hidden">
            <div className="divide-y divide-border">
              {filteredTasks.map((task) => (
                <IssueRow
                  key={task.id}
                  id={task.id}
                  title={task.title}
                  requirementId={task.requirementId}
                  requirements={requirements}
                  points={task.points}
                  statusLabel={task.status}
                  statusTone={STATUS_TONE[task.status]}
                  member={memberFor(teamMembers, task.assigneeId)}
                  isStory={Boolean(task.storyId)}
                  onClick={() => setOpenTask(task)}
                />
              ))}
            </div>
          </Card>
        )
      ) : groupBy === 'assignee' ? (
        filteredTasks.length === 0 ? (
          <EmptyState title="No matching issues" description="Try a different search term or clear the assignee filter." />
        ) : (
          <div className="space-y-5">
            {[...teamMembers, { id: null, name: 'Unassigned' }].map((m) => {
              const laneTasks = filteredTasks.filter((t) => (t.assigneeId || null) === m.id)
              if (laneTasks.length === 0) return null
              return (
                <div key={m.id ?? 'unassigned'}>
                  <div className="flex items-center gap-2 mb-2 px-0.5">
                    {m.id ? (
                      <AvatarComp name={m.name} size={22} />
                    ) : (
                      <span className="h-[22px] w-[22px] rounded-full bg-muted flex items-center justify-center shrink-0">
                        <Users className="h-3 w-3 text-muted-foreground" />
                      </span>
                    )}
                    <span className="text-xs font-semibold text-foreground">{m.name}</span>
                    <span className="text-[11px] text-muted-foreground">{laneTasks.length} issue{laneTasks.length === 1 ? '' : 's'}</span>
                  </div>
                  <KanbanColumns
                    tasks={laneTasks}
                    teamMembers={teamMembers}
                    requirements={requirements}
                    onOpen={setOpenTask}
                    moveKanbanTask={moveKanbanTask}
                    assignKanbanTask={assignKanbanTask}
                    swimlaneAssigneeId={m.id}
                    minHeight={90}
                  />
                </div>
              )
            })}
          </div>
        )
      ) : (
        <KanbanColumns
          tasks={filteredTasks}
          teamMembers={teamMembers}
          requirements={requirements}
          onOpen={setOpenTask}
          moveKanbanTask={moveKanbanTask}
          assignKanbanTask={assignKanbanTask}
          minHeight={380}
        />
      )}

      <TaskDetailDialog
        task={openTask}
        onClose={() => setOpenTask(null)}
        teamMembers={membersWithLoad}
        onAssign={assignKanbanTask}
        onMove={moveKanbanTask}
      />
    </>
  )
}

/* ------------------------------------------------------------------ */
/* Backlog tab — current sprint, then everything not yet pulled in     */
/* ------------------------------------------------------------------ */
function BacklogView() {
  const navigate = useNavigate()
  const { requirements, userStories, kanbanTasks, teamMembers, projectInfo, moveKanbanTask, assignKanbanTask } = usePlanningData()
  const [openTask, setOpenTask] = useState(null)

  const totalPoints = kanbanTasks.reduce((s, t) => s + t.points, 0)

  const inSprintStoryIds = new Set(kanbanTasks.map((t) => t.storyId).filter(Boolean))
  const backlogItems = []
  for (const req of requirements) {
    for (const s of userStories[req.id] || []) {
      if (!inSprintStoryIds.has(s.id)) backlogItems.push({ story: s, requirementId: req.id })
    }
  }

  const membersWithLoad = teamMembers.map((m) => ({
    ...m,
    currentLoad: kanbanTasks.filter((t) => t.assigneeId === m.id && t.status !== 'Done').reduce((s, t) => s + t.points, 0),
  }))

  return (
    <div className="space-y-4">
      <Card className="p-0 overflow-hidden">
        <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-border bg-muted/20 flex-wrap">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-sm font-semibold text-foreground">{projectInfo.sprintName}</h3>
            <span className="text-xs text-muted-foreground">
              {formatShortDate(projectInfo.sprintStartDate)} – {formatShortDate(projectInfo.sprintEndDate)}
            </span>
            <Badge tone="primary">{totalPoints} SP</Badge>
          </div>
          <Badge tone="success">Active</Badge>
        </div>
        {kanbanTasks.length === 0 ? (
          <EmptyState title="Sprint is empty" description="Confirm an effort estimate to send a task to this sprint." />
        ) : (
          <div className="divide-y divide-border">
            {kanbanTasks.map((task) => (
              <IssueRow
                key={task.id}
                id={task.id}
                title={task.title}
                requirementId={task.requirementId}
                requirements={requirements}
                points={task.points}
                statusLabel={task.status}
                statusTone={STATUS_TONE[task.status]}
                member={memberFor(teamMembers, task.assigneeId)}
                isStory={Boolean(task.storyId)}
                onClick={() => setOpenTask(task)}
              />
            ))}
          </div>
        )}
      </Card>

      <Card className="p-0 overflow-hidden">
        <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-border bg-muted/20">
          <h3 className="text-sm font-semibold text-foreground">Backlog</h3>
          <span className="text-xs text-muted-foreground">{backlogItems.length} item{backlogItems.length === 1 ? '' : 's'}</span>
        </div>
        {backlogItems.length === 0 ? (
          <EmptyState title="Backlog is clear" description="Every groomed story has already been pulled into the sprint." />
        ) : (
          <div className="divide-y divide-border">
            {backlogItems.map(({ story, requirementId }) => (
              <IssueRow
                key={story.id}
                id={story.id}
                title={story.title}
                requirementId={requirementId}
                requirements={requirements}
                points={null}
                statusLabel={story.status}
                statusTone={story.status === 'Accepted' ? 'success' : 'neutral'}
                member={null}
                isStory
                onClick={() => navigate(story.status === 'Accepted' ? '/planning/requirements/estimation' : '/planning/requirements/decomposition')}
              />
            ))}
          </div>
        )}
      </Card>

      <TaskDetailDialog
        task={openTask}
        onClose={() => setOpenTask(null)}
        teamMembers={membersWithLoad}
        onAssign={assignKanbanTask}
        onMove={moveKanbanTask}
      />
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Reports tab — Jira-style left nav of report types                  */
/* ------------------------------------------------------------------ */
const REPORTS_NAV = [
  { key: 'sprint', label: 'Sprint Report', icon: BarChart3 },
  { key: 'burndown', label: 'Burndown Chart', icon: TrendingDown },
  { key: 'velocity', label: 'Velocity Chart', icon: Gauge },
  { key: 'status', label: 'Status Breakdown', icon: LayoutGrid },
]

function SprintReportPanel() {
  const { kanbanTasks, requirements, userStories, estimations, projectInfo } = usePlanningData()
  const donePoints = kanbanTasks.filter((t) => t.status === 'Done').reduce((s, t) => s + t.points, 0)
  const inProgressPoints = kanbanTasks.filter((t) => t.status === 'In Progress').reduce((s, t) => s + t.points, 0)
  const todoPoints = kanbanTasks.filter((t) => t.status === 'Todo').reduce((s, t) => s + t.points, 0)
  const blockedCount = kanbanTasks.filter((t) => t.status === 'Blocked').length

  const passing = requirements.filter((r) => r.status === 'Passing')
  let completed = 0, inDevelopment = 0, blocked = 0
  for (const req of requirements) {
    if (req.status !== 'Passing') { blocked++; continue }
    const stories = userStories[req.id] || []
    if (stories.length > 0 && stories.every((s) => estimations[s.id]?.confirmed)) completed++
    else inDevelopment++
  }

  return (
    <div className="space-y-4">
      <Card>
        <h3 className="text-sm font-semibold text-foreground mb-1">Sprint Report</h3>
        <p className="text-xs text-muted-foreground mb-4">
          A snapshot of completed, in-progress and blocked work for {projectInfo.sprintName}.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard icon={BarChart3} label="Completed" value={`${donePoints} SP`} tone="success" />
          <StatCard icon={BarChart3} label="In Progress" value={`${inProgressPoints} SP`} tone="primary" />
          <StatCard icon={BarChart3} label="To Do" value={`${todoPoints} SP`} tone="warning" />
          <StatCard icon={AlertTriangle} label="Blocked" value={blockedCount} tone={blockedCount > 0 ? 'danger' : 'success'} />
        </div>
      </Card>

      <Card>
        <h3 className="text-sm font-semibold text-foreground mb-3">Requirement progress</h3>
        <div className="flex items-center gap-6 text-sm flex-wrap">
          <span className="flex items-center gap-1.5"><Badge tone="success">{completed}</Badge> Completed</span>
          <span className="flex items-center gap-1.5"><Badge tone="primary">{inDevelopment}</Badge> In development</span>
          <span className="flex items-center gap-1.5"><Badge tone="danger">{blocked}</Badge> Blocked</span>
          <span className="text-muted-foreground ml-auto">{passing.length + blocked} total</span>
        </div>
      </Card>
    </div>
  )
}

function BurndownPanel() {
  return (
    <Card>
      <h3 className="text-sm font-semibold text-foreground mb-1">Burndown Chart</h3>
      <p className="text-xs text-muted-foreground mb-4">
        Tracks remaining story points against the ideal pace needed to finish everything by the end of the sprint.
      </p>
      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer>
          <LineChart data={BURNDOWN_SEED}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="day" tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }} />
            <YAxis tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }} unit=" SP" />
            <RechartsTooltip contentStyle={{ backgroundColor: 'var(--popover)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Line type="monotone" dataKey="ideal" name="Ideal" stroke="var(--chart-2)" strokeDasharray="4 4" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="actual" name="Actual remaining" stroke="var(--chart-1)" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

function VelocityPanel() {
  return (
    <Card>
      <h3 className="text-sm font-semibold text-foreground mb-1">Velocity Chart</h3>
      <p className="text-xs text-muted-foreground mb-4">
        Story points completed per sprint over time — use it to estimate how much the team can realistically commit to next.
      </p>
      <div style={{ width: '100%', height: 220 }}>
        <ResponsiveContainer>
          <BarChart data={VELOCITY_TREND}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="sprint" tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }} />
            <YAxis tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }} />
            <RechartsTooltip contentStyle={{ backgroundColor: 'var(--popover)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }} />
            <Bar dataKey="velocity" name="Velocity" fill="var(--chart-1)" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

function StatusPanel() {
  const { kanbanTasks } = usePlanningData()
  const statusDistribution = KANBAN_COLUMNS.map((c) => ({
    status: c.label,
    points: kanbanTasks.filter((t) => t.status === c.key).reduce((s, t) => s + t.points, 0),
  }))

  return (
    <Card>
      <h3 className="text-sm font-semibold text-foreground mb-1">Status Breakdown</h3>
      <p className="text-xs text-muted-foreground mb-4">Story points currently sitting in each column of the board.</p>
      <div style={{ width: '100%', height: 220 }}>
        <ResponsiveContainer>
          <BarChart data={statusDistribution}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis dataKey="status" tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }} />
            <YAxis tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }} />
            <RechartsTooltip contentStyle={{ backgroundColor: 'var(--popover)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }} />
            <Bar dataKey="points" name="Story points" fill="var(--chart-3)" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  )
}

function ReportsView() {
  const [reportKey, setReportKey] = useState('sprint')

  return (
    <div className="flex flex-col sm:flex-row gap-4">
      <nav className="sm:w-[180px] shrink-0 space-y-0.5">
        {REPORTS_NAV.map((r) => {
          const Icon = r.icon
          const active = reportKey === r.key
          return (
            <button
              key={r.key}
              type="button"
              onClick={() => setReportKey(r.key)}
              className={`w-full flex items-center gap-2 px-2.5 py-2 rounded-md text-xs font-medium text-left transition-colors cursor-pointer ${
                active ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-accent hover:text-foreground'
              }`}
            >
              <Icon className="h-3.5 w-3.5 shrink-0" /> {r.label}
            </button>
          )
        })}
      </nav>
      <div className="flex-1 min-w-0">
        {reportKey === 'sprint' && <SprintReportPanel />}
        {reportKey === 'burndown' && <BurndownPanel />}
        {reportKey === 'velocity' && <VelocityPanel />}
        {reportKey === 'status' && <StatusPanel />}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */
export default function SprintManagement() {
  const { projectInfo, teamMembers, kanbanTasks, requirements } = usePlanningData()
  const [tab, setTab] = useState('board')
  const [today] = useState(() => Date.now())
  const [consultOpen, setConsultOpen] = useState(false)
  const [scrumGuideOpen, setScrumGuideOpen] = useState(false)

  const totalPoints = kanbanTasks.reduce((s, t) => s + t.points, 0)
  const donePoints = kanbanTasks.filter((t) => t.status === 'Done').reduce((s, t) => s + t.points, 0)
  const blockedCount = kanbanTasks.filter((t) => t.status === 'Blocked').length
  const progressPercent = totalPoints ? Math.round((donePoints / totalPoints) * 100) : 0
  const daysLeft = Math.max(0, Math.ceil((new Date(projectInfo.sprintEndDate).getTime() - today) / 86400000))

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
            Sprint Execution &amp; Agile Burndown
            <Badge tone="primary" className="text-xs font-medium">
              Sprint 1 of 4 Active
            </Badge>
          </h1>
        </div>

        {/* Action Toolbar */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setScrumGuideOpen(true)}
            className="text-xs cursor-pointer gap-1.5"
          >
            <BookOpen className="h-3.5 w-3.5 text-primary" /> Scrum Standards Guide
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
            onClick={() => showToast('Sprint completion dossier submitted for Dr. Amara Silva review', 'success')}
            className="text-xs cursor-pointer gap-1.5"
          >
            <Sparkles className="h-3.5 w-3.5" /> Complete Sprint
          </Button>
        </div>
      </div>

      {/* LMS Project Banner Card with Round Progress Bar (no left border) */}
      <Card className="p-5 relative overflow-hidden bg-card/90">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-5">
          <div className="space-y-2 min-w-0 max-w-2xl">
            <div className="flex items-center gap-2 flex-wrap text-xs text-muted-foreground">
              <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-bold flex items-center gap-1.5">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
                Active Sprint
              </span>
              <span>·</span>
              <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary font-bold">
                {COURSE_INFO.group.number} ({COURSE_INFO.group.code})
              </span>
              <span>·</span>
              <span className="font-semibold text-foreground">{COURSE_INFO.department}</span>
              <span>·</span>
              <span>
                {formatShortDate(projectInfo.sprintStartDate)} – {formatShortDate(projectInfo.sprintEndDate)} · {projectInfo.sprintName} of {projectInfo.totalSprints}
              </span>
            </div>

            <h2 className="text-xl sm:text-2xl font-bold text-foreground tracking-tight">
              {projectInfo.sprintName} · Agile Task Board &amp; Burndown
            </h2>

            <p className="text-xs text-muted-foreground leading-relaxed">
              Track real-time sprint execution across backlog user stories, subtasks, and Kanban columns. The DART audit engine monitors velocity compliance and flags blocked dependencies for academic evaluation.
            </p>

            <div className="flex items-center gap-4 flex-wrap pt-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5 font-medium text-foreground">
                <AvatarComp name={COURSE_INFO.supervisor.name} size={20} className="ring-1 ring-border" />
                Supervisor: {COURSE_INFO.supervisor.name}
              </span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span className="flex items-center gap-1.5">
                <Users className="h-3.5 w-3.5 text-primary" />
                {teamMembers.length} Members
              </span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span className="flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-amber-500" />
                {kanbanTasks.length} Tasks ({totalPoints} SP)
              </span>
              {blockedCount > 0 && (
                <>
                  <span className="h-1 w-1 rounded-full bg-border" />
                  <span className="flex items-center gap-1.5 text-destructive font-medium">
                    <AlertTriangle className="h-3.5 w-3.5" /> {blockedCount} Blocked
                  </span>
                </>
              )}
              <span className="h-1 w-1 rounded-full bg-border" />
              <Badge tone="primary" className="text-[11px] px-2 py-0.5">
                {daysLeft === 0 ? 'Ends today' : `${daysLeft} day${daysLeft === 1 ? '' : 's'} remaining`}
              </Badge>
              <div className="flex -space-x-2 ml-1">
                {teamMembers.map((m) => (
                  <AvatarComp key={m.id} name={m.name} size={22} className="ring-2 ring-card" />
                ))}
              </div>
            </div>
          </div>

          {/* Round Circular SVG Progress Bar with Percentage in Middle */}
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
                  strokeDashoffset={(2 * Math.PI * 38) * (1 - progressPercent / 100)}
                  strokeLinecap="round"
                  fill="transparent"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-xl font-bold tracking-tight text-foreground">{progressPercent}%</span>
              </div>
            </div>
            <span className="text-xs font-semibold text-muted-foreground mt-1.5">Sprint Burned</span>
          </div>
        </div>
      </Card>

      <WorkflowStepper current="sprint" />

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="w-full h-auto justify-start flex-wrap gap-1 rounded-none bg-transparent p-0 border-b border-border">
          <TabsTrigger
            value="backlog"
            className="rounded-none border-b-2 border-transparent px-3 py-2.5 text-sm font-medium gap-1.5 text-muted-foreground hover:text-foreground data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-primary data-[state=active]:shadow-none"
          >
            <Layers className="h-3.5 w-3.5" />Backlog
          </TabsTrigger>
          <TabsTrigger
            value="board"
            className="rounded-none border-b-2 border-transparent px-3 py-2.5 text-sm font-medium gap-1.5 text-muted-foreground hover:text-foreground data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-primary data-[state=active]:shadow-none"
          >
            <LayoutGrid className="h-3.5 w-3.5" />Board
          </TabsTrigger>
          <TabsTrigger
            value="reports"
            className="rounded-none border-b-2 border-transparent px-3 py-2.5 text-sm font-medium gap-1.5 text-muted-foreground hover:text-foreground data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-primary data-[state=active]:shadow-none"
          >
            <BarChart3 className="h-3.5 w-3.5" />Reports
          </TabsTrigger>
        </TabsList>
        <TabsContent value="backlog" className="mt-4"><BacklogView /></TabsContent>
        <TabsContent value="board" className="mt-4"><BoardView /></TabsContent>
        <TabsContent value="reports" className="mt-4"><ReportsView /></TabsContent>
      </Tabs>

      <DartButton context="sprint" />

      {/* Supervisor Consultation Modal */}
      <SupervisorConsultationModal
        open={consultOpen}
        onOpenChange={setConsultOpen}
        requirements={requirements}
      />

      {/* Scrum Standards Guide Dialog */}
      <Dialog open={scrumGuideOpen} onOpenChange={setScrumGuideOpen}>
        <DialogContent className="sm:max-w-[620px] max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center gap-2 mb-1">
              <span className="p-1 rounded bg-primary/10 text-primary">
                <BookOpen className="h-4 w-4" />
              </span>
              <DialogTitle className="text-lg font-bold">Scrum &amp; Sprint Execution Standards</DialogTitle>
            </div>
            <DialogDescription className="text-xs">
              Academic guidelines used for Milestone M3 sprint evaluation and agile ceremony compliance.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 text-xs">
            <div className="p-3 rounded-xl border border-border bg-card space-y-1">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-foreground text-xs flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-primary" /> Definition of Done (DoD)
                </h4>
                <Badge tone="primary" className="text-[10px] px-1.5 py-0">Criterion 1</Badge>
              </div>
              <p className="text-muted-foreground text-[11px] leading-relaxed">
                A user story or task is only marked Done when code is reviewed, unit/integration tests pass, and INVEST acceptance criteria (Given/When/Then) are confirmed.
              </p>
            </div>

            <div className="p-3 rounded-xl border border-border bg-card space-y-1">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-foreground text-xs flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-primary" /> Work-In-Progress (WIP) Limits
                </h4>
                <Badge tone="primary" className="text-[10px] px-1.5 py-0">Criterion 2</Badge>
              </div>
              <p className="text-muted-foreground text-[11px] leading-relaxed">
                Limit active tasks in &apos;In Progress&apos; per team member to prevent context switching and bottlenecks during sprint execution.
              </p>
            </div>

            <div className="p-3 rounded-xl border border-border bg-card space-y-1">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-foreground text-xs flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-primary" /> Impediment &amp; Blocked Escalation
                </h4>
                <Badge tone="primary" className="text-[10px] px-1.5 py-0">Criterion 3</Badge>
              </div>
              <p className="text-muted-foreground text-[11px] leading-relaxed">
                Tasks blocked for more than 24 hours must be annotated with a clear reason and escalated to Dr. Amara Silva or DART arbitration.
              </p>
            </div>

            <div className="p-3 rounded-xl border border-border bg-card space-y-1">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-foreground text-xs flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-primary" /> Velocity Consistency &amp; Burndown
                </h4>
                <Badge tone="primary" className="text-[10px] px-1.5 py-0">Criterion 4</Badge>
              </div>
              <p className="text-muted-foreground text-[11px] leading-relaxed">
                Burndown should track reasonably close to the ideal guideline. Sudden drop-offs at sprint end without steady progression will be flagged.
              </p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
