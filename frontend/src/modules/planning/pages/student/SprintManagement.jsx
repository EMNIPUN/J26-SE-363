import { useState } from 'react'
import { ListTodo, LayoutGrid, BarChart3, GripVertical, Layers, AlertTriangle } from 'lucide-react'
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
import PageHeader from '../../../../shared/components/PageHeader.jsx'
import Card from '../../../../shared/components/Card.jsx'
import Badge from '../../../../shared/components/Badge.jsx'
import StatCard from '../../../../shared/components/StatCard.jsx'
import EmptyState from '../../../../shared/components/EmptyState.jsx'
import AvatarComp from '../../../../shared/components/Avatar.jsx'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
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
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import WorkflowStepper from '../../components/WorkflowStepper.jsx'
import DartButton from '../../components/DartButton.jsx'
import { usePlanningData } from '../../context/usePlanningData.js'
import { KANBAN_COLUMNS, BURNDOWN_SEED, VELOCITY_TREND } from '../../data/mockData.js'

const STATUS_TONE = { Todo: 'neutral', 'In Progress': 'primary', Blocked: 'danger', Done: 'success' }

function memberFor(teamMembers, id) {
  return teamMembers.find((m) => m.id === id) || null
}

function KanbanCard({ task, member, onAssign, teamMembers, onOpen }) {
  return (
    <div
      draggable
      onDragStart={(e) => e.dataTransfer.setData('text/plain', task.id)}
      onClick={() => onOpen(task)}
      className="p-3 rounded-lg border border-border bg-card shadow-xs cursor-grab active:cursor-grabbing card-hover-lift"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <GripVertical className="h-3.5 w-3.5" />
          <span className="text-xs font-medium">{task.id}</span>
        </div>
        <Badge tone="primary">{task.points} SP</Badge>
      </div>
      <p className="text-sm text-foreground leading-snug mb-3">{task.title}</p>
      {task.status === 'Blocked' && task.blockedReason && (
        <p className="text-[11px] text-destructive mb-2 flex items-start gap-1">
          <AlertTriangle className="h-3 w-3 mt-0.5 shrink-0" />
          {task.blockedReason}
        </p>
      )}
      <div className="flex items-center justify-between gap-2">
        {task.requirementId && <span className="text-xs text-muted-foreground">{task.requirementId}</span>}
        <div onClick={(e) => e.stopPropagation()} className="ml-auto">
          <Select value={task.assigneeId || 'unassigned'} onValueChange={(v) => onAssign(task.id, v === 'unassigned' ? null : v)}>
            <SelectTrigger className="w-[130px] h-7">
              <SelectValue>
                <span className="flex items-center gap-1.5 text-xs">
                  {member ? <AvatarComp name={member.name} size={18} /> : null}
                  {member ? member.name.split(' ')[0] : 'Unassigned'}
                </span>
              </SelectValue>
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="unassigned">Unassigned</SelectItem>
              {teamMembers.map((m) => (
                <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
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

function BoardView() {
  const { kanbanTasks, teamMembers, moveKanbanTask, assignKanbanTask } = usePlanningData()
  const [dragOverCol, setDragOverCol] = useState(null)
  const [openTask, setOpenTask] = useState(null)

  const membersWithLoad = teamMembers.map((m) => ({
    ...m,
    currentLoad: kanbanTasks.filter((t) => t.assigneeId === m.id && t.status !== 'Done').reduce((s, t) => s + t.points, 0),
  }))

  return (
    <>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {KANBAN_COLUMNS.map((col) => {
          const tasks = kanbanTasks.filter((t) => t.status === col.key)
          const points = tasks.reduce((sum, t) => sum + t.points, 0)
          return (
            <div
              key={col.key}
              onDragOver={(e) => { e.preventDefault(); setDragOverCol(col.key) }}
              onDragLeave={() => setDragOverCol((c) => (c === col.key ? null : c))}
              onDrop={(e) => {
                e.preventDefault()
                const taskId = e.dataTransfer.getData('text/plain')
                if (taskId) moveKanbanTask(taskId, col.key)
                setDragOverCol(null)
              }}
              className={`rounded-xl border p-3 space-y-3 min-h-[420px] transition-colors ${
                dragOverCol === col.key ? 'border-primary bg-primary/5' : 'border-border bg-muted/20'
              }`}
            >
              <div className="flex items-center justify-between px-1">
                <h3 className="text-sm font-semibold text-foreground">
                  {col.label} <span className="text-muted-foreground font-normal">({tasks.length})</span>
                </h3>
                <span className="text-xs text-muted-foreground">{points} SP</span>
              </div>
              <div className="space-y-2.5">
                {tasks.map((task) => (
                  <KanbanCard key={task.id} task={task} member={memberFor(teamMembers, task.assigneeId)} teamMembers={teamMembers} onAssign={assignKanbanTask} onOpen={setOpenTask} />
                ))}
                {tasks.length === 0 && (
                  <div className="text-xs text-muted-foreground text-center py-8 border-2 border-dashed border-border rounded-lg">Drop tasks here</div>
                )}
              </div>
            </div>
          )
        })}
      </div>
      <TaskDetailDialog
        task={openTask ? { ...openTask, teamMembers: membersWithLoad } : null}
        onClose={() => setOpenTask(null)}
        teamMembers={membersWithLoad}
        onAssign={assignKanbanTask}
        onMove={moveKanbanTask}
      />
    </>
  )
}

function ListView() {
  const { kanbanTasks, teamMembers, moveKanbanTask, assignKanbanTask } = usePlanningData()

  if (kanbanTasks.length === 0) {
    return <EmptyState title="No tasks yet" description="Confirm an effort estimate to send a task to the sprint board." />
  }

  return (
    <Card className="p-0 overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>ID</TableHead>
            <TableHead>Task</TableHead>
            <TableHead className="w-[100px]">Requirement</TableHead>
            <TableHead className="w-[80px]">Points</TableHead>
            <TableHead className="w-[160px]">Assignee</TableHead>
            <TableHead className="w-[150px]">Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {kanbanTasks.map((task) => {
            const member = memberFor(teamMembers, task.assigneeId)
            return (
              <TableRow key={task.id}>
                <TableCell className="font-medium text-muted-foreground">{task.id}</TableCell>
                <TableCell className="max-w-sm truncate">{task.title}</TableCell>
                <TableCell className="text-xs text-muted-foreground">{task.requirementId || '—'}</TableCell>
                <TableCell>{task.points} SP</TableCell>
                <TableCell>
                  <Select value={task.assigneeId || 'unassigned'} onValueChange={(v) => assignKanbanTask(task.id, v === 'unassigned' ? null : v)}>
                    <SelectTrigger className="w-[150px]">
                      <SelectValue>
                        <span className="flex items-center gap-1.5 text-xs">
                          {member ? <AvatarComp name={member.name} size={18} /> : null}
                          {member ? member.name : 'Unassigned'}
                        </span>
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="unassigned">Unassigned</SelectItem>
                      {teamMembers.map((m) => <SelectItem key={m.id} value={m.id}>{m.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </TableCell>
                <TableCell>
                  <Select value={task.status} onValueChange={(v) => moveKanbanTask(task.id, v)}>
                    <SelectTrigger className="w-[130px]">
                      <SelectValue><Badge tone={STATUS_TONE[task.status]}>{task.status}</Badge></SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {KANBAN_COLUMNS.map((c) => <SelectItem key={c.key} value={c.key}>{c.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </Card>
  )
}

function BacklogView() {
  const { requirements, userStories } = usePlanningData()
  const passing = requirements.filter((r) => r.status === 'Passing')

  return (
    <div className="space-y-3">
      {passing.map((req) => {
        const stories = userStories[req.id] || []
        if (stories.length === 0) return null
        return (
          <Card key={req.id}>
            <p className="text-xs font-semibold text-muted-foreground mb-1">{req.id}</p>
            <p className="text-sm font-medium text-foreground mb-3">{req.title}</p>
            <ul className="space-y-2 ml-2 border-l border-border pl-4">
              {stories.map((s) => (
                <li key={s.id}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm text-foreground">{s.title}</span>
                    <Badge tone={s.status === 'Accepted' ? 'success' : 'neutral'}>{s.status}</Badge>
                  </div>
                  {s.tasks.length > 0 && (
                    <ul className="mt-1.5 ml-4 space-y-1 border-l border-border/60 pl-3">
                      {s.tasks.map((t) => (
                        <li key={t.id} className="text-xs text-muted-foreground flex items-center gap-2">
                          <Layers className="h-3 w-3 shrink-0" />
                          {t.title}
                          <Badge tone={STATUS_TONE[t.status] || 'neutral'} className="ml-auto">{t.status}</Badge>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          </Card>
        )
      })}
      {passing.every((req) => (userStories[req.id] || []).length === 0) && (
        <EmptyState title="Backlog is empty" description="Decompose a requirement into user stories to build up the backlog." />
      )}
    </div>
  )
}

function SummaryView() {
  const { kanbanTasks } = usePlanningData()
  const totalPoints = kanbanTasks.reduce((s, t) => s + t.points, 0)
  const donePoints = kanbanTasks.filter((t) => t.status === 'Done').reduce((s, t) => s + t.points, 0)
  const inProgressPoints = kanbanTasks.filter((t) => t.status === 'In Progress').reduce((s, t) => s + t.points, 0)
  const todoPoints = kanbanTasks.filter((t) => t.status === 'Todo').reduce((s, t) => s + t.points, 0)
  const blockedCount = kanbanTasks.filter((t) => t.status === 'Blocked').length
  const progressPercent = totalPoints ? Math.round((donePoints / totalPoints) * 100) : 0

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-base font-semibold text-foreground">Sprint progress</h3>
          <span className="text-sm font-semibold text-foreground">{progressPercent}%</span>
        </div>
        <Progress value={progressPercent} className="h-2.5" />
      </Card>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={BarChart3} label="Completed" value={`${donePoints} SP`} tone="success" />
        <StatCard icon={BarChart3} label="In Progress" value={`${inProgressPoints} SP`} tone="primary" />
        <StatCard icon={BarChart3} label="To Do" value={`${todoPoints} SP`} tone="warning" />
        <StatCard icon={AlertTriangle} label="Blocked" value={blockedCount} tone={blockedCount > 0 ? 'danger' : 'success'} />
      </div>
    </div>
  )
}

function ReportsView() {
  const { kanbanTasks, requirements, userStories, estimations } = usePlanningData()
  const statusDistribution = KANBAN_COLUMNS.map((c) => ({
    status: c.label,
    points: kanbanTasks.filter((t) => t.status === c.key).reduce((s, t) => s + t.points, 0),
  }))

  const passing = requirements.filter((r) => r.status === 'Passing')
  let completed = 0, inDevelopment = 0, blocked = 0
  for (const req of requirements) {
    if (req.status !== 'Passing') { blocked++; continue }
    const stories = userStories[req.id] || []
    if (stories.length > 0 && stories.every((s) => estimations[s.id]?.confirmed)) completed++
    else inDevelopment++
  }

  return (
    <div className="space-y-6">
      <Card>
        <h3 className="text-base font-semibold text-foreground mb-4">Sprint burndown</h3>
        <div style={{ width: '100%', height: 240 }}>
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <h3 className="text-base font-semibold text-foreground mb-4">Sprint velocity</h3>
          <div style={{ width: '100%', height: 200 }}>
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

        <Card>
          <h3 className="text-base font-semibold text-foreground mb-4">Task completion by status</h3>
          <div style={{ width: '100%', height: 200 }}>
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
      </div>

      <Card>
        <h3 className="text-base font-semibold text-foreground mb-4">Requirement progress</h3>
        <div className="flex items-center gap-6 text-sm">
          <span className="flex items-center gap-1.5"><Badge tone="success">{completed}</Badge> Completed</span>
          <span className="flex items-center gap-1.5"><Badge tone="primary">{inDevelopment}</Badge> In development</span>
          <span className="flex items-center gap-1.5"><Badge tone="danger">{blocked}</Badge> Blocked</span>
          <span className="text-muted-foreground ml-auto">{passing.length + blocked} total</span>
        </div>
      </Card>
    </div>
  )
}

export default function SprintManagement() {
  const { projectInfo } = usePlanningData()
  const [tab, setTab] = useState('summary')

  return (
    <div className="space-y-6">
      <PageHeader
        title="Sprint Management"
        breadcrumb={['Planning', 'Student', 'Sprint Management']}
        description={`${projectInfo.sprintName} of ${projectInfo.totalSprints} — plan the backlog, run the board, and track progress.`}
      />

      <WorkflowStepper current="sprint" />

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="flex-wrap h-auto">
          <TabsTrigger value="summary"><BarChart3 className="h-3.5 w-3.5" />Summary</TabsTrigger>
          <TabsTrigger value="backlog"><Layers className="h-3.5 w-3.5" />Backlog</TabsTrigger>
          <TabsTrigger value="board"><LayoutGrid className="h-3.5 w-3.5" />Kanban</TabsTrigger>
          <TabsTrigger value="list"><ListTodo className="h-3.5 w-3.5" />Task List</TabsTrigger>
          <TabsTrigger value="reports"><BarChart3 className="h-3.5 w-3.5" />Reports</TabsTrigger>
        </TabsList>
        <TabsContent value="summary" className="mt-4"><SummaryView /></TabsContent>
        <TabsContent value="backlog" className="mt-4"><BacklogView /></TabsContent>
        <TabsContent value="board" className="mt-4"><BoardView /></TabsContent>
        <TabsContent value="list" className="mt-4"><ListView /></TabsContent>
        <TabsContent value="reports" className="mt-4"><ReportsView /></TabsContent>
      </Tabs>

      <DartButton context="sprint" />
    </div>
  )
}
