import { useState } from 'react'
import { ListTodo, LayoutGrid, BarChart3, GripVertical } from 'lucide-react'
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
import { usePlanningData } from '../../context/usePlanningData.js'
import { KANBAN_COLUMNS, BURNDOWN_SEED } from '../../data/mockData.js'

const STATUS_TONE = { Todo: 'neutral', 'In Progress': 'primary', Done: 'success' }

function memberFor(teamMembers, id) {
  return teamMembers.find((m) => m.id === id) || null
}

function KanbanCard({ task, member, onAssign, teamMembers, onDragStart }) {
  return (
    <div
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData('text/plain', task.id)
        onDragStart?.(task.id)
      }}
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
      <div className="flex items-center justify-between gap-2">
        {task.requirementId && (
          <span className="text-xs text-muted-foreground">{task.requirementId}</span>
        )}
        <Select value={task.assigneeId || 'unassigned'} onValueChange={(v) => onAssign(task.id, v === 'unassigned' ? null : v)}>
          <SelectTrigger className="w-[130px] h-7 ml-auto">
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
              <SelectItem key={m.id} value={m.id}>
                {m.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}

function BoardView() {
  const { kanbanTasks, teamMembers, moveKanbanTask, assignKanbanTask } = usePlanningData()
  const [dragOverCol, setDragOverCol] = useState(null)

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {KANBAN_COLUMNS.map((col) => {
        const tasks = kanbanTasks.filter((t) => t.status === col.key)
        const points = tasks.reduce((sum, t) => sum + t.points, 0)
        return (
          <div
            key={col.key}
            onDragOver={(e) => {
              e.preventDefault()
              setDragOverCol(col.key)
            }}
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
                <KanbanCard
                  key={task.id}
                  task={task}
                  member={memberFor(teamMembers, task.assigneeId)}
                  teamMembers={teamMembers}
                  onAssign={assignKanbanTask}
                />
              ))}
              {tasks.length === 0 && (
                <div className="text-xs text-muted-foreground text-center py-8 border-2 border-dashed border-border rounded-lg">
                  Drop tasks here
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
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
                      {teamMembers.map((m) => (
                        <SelectItem key={m.id} value={m.id}>
                          {m.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </TableCell>
                <TableCell>
                  <Select value={task.status} onValueChange={(v) => moveKanbanTask(task.id, v)}>
                    <SelectTrigger className="w-[130px]">
                      <SelectValue>
                        <Badge tone={STATUS_TONE[task.status]}>{task.status}</Badge>
                      </SelectValue>
                    </SelectTrigger>
                    <SelectContent>
                      {KANBAN_COLUMNS.map((c) => (
                        <SelectItem key={c.key} value={c.key}>
                          {c.label}
                        </SelectItem>
                      ))}
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

function SummaryView() {
  const { kanbanTasks } = usePlanningData()
  const totalPoints = kanbanTasks.reduce((s, t) => s + t.points, 0)
  const donePoints = kanbanTasks.filter((t) => t.status === 'Done').reduce((s, t) => s + t.points, 0)
  const inProgressPoints = kanbanTasks.filter((t) => t.status === 'In Progress').reduce((s, t) => s + t.points, 0)
  const todoPoints = kanbanTasks.filter((t) => t.status === 'Todo').reduce((s, t) => s + t.points, 0)

  const statusDistribution = KANBAN_COLUMNS.map((c) => ({
    status: c.label,
    points: kanbanTasks.filter((t) => t.status === c.key).reduce((s, t) => s + t.points, 0),
  }))

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={BarChart3} label="Total Story Points" value={totalPoints} tone="primary" />
        <StatCard icon={BarChart3} label="Completed" value={`${donePoints} SP`} tone="success" />
        <StatCard icon={BarChart3} label="In Progress" value={`${inProgressPoints} SP`} tone="primary" />
        <StatCard icon={BarChart3} label="To Do" value={`${todoPoints} SP`} tone="warning" />
      </div>

      <Card>
        <h3 className="text-base font-semibold text-foreground mb-4">Sprint burndown</h3>
        <div style={{ width: '100%', height: 240 }}>
          <ResponsiveContainer>
            <LineChart data={BURNDOWN_SEED}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="day" tick={{ fill: 'var(--muted-foreground)', fontSize: 11 }} />
              <YAxis tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }} unit=" SP" />
              <RechartsTooltip
                contentStyle={{ backgroundColor: 'var(--popover)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="ideal" name="Ideal" stroke="var(--chart-2)" strokeDasharray="4 4" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="actual" name="Actual remaining" stroke="var(--chart-1)" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card>
        <h3 className="text-base font-semibold text-foreground mb-4">Points by status</h3>
        <div style={{ width: '100%', height: 200 }}>
          <ResponsiveContainer>
            <BarChart data={statusDistribution}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="status" tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }} />
              <YAxis tick={{ fill: 'var(--muted-foreground)', fontSize: 12 }} />
              <RechartsTooltip
                contentStyle={{ backgroundColor: 'var(--popover)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 12 }}
              />
              <Bar dataKey="points" name="Story points" fill="var(--chart-1)" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  )
}

export default function SprintManagement() {
  const { projectInfo } = usePlanningData()
  const [tab, setTab] = useState('board')

  return (
    <div className="space-y-6">
      <PageHeader
        title="Sprint Management"
        breadcrumb={['Planning', 'Student', 'Sprint Management']}
        description={`${projectInfo.sprintName} of ${projectInfo.totalSprints} — drag tasks across the board, assign teammates, and track burndown.`}
      />

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="board">
            <LayoutGrid className="h-3.5 w-3.5" />
            Board
          </TabsTrigger>
          <TabsTrigger value="list">
            <ListTodo className="h-3.5 w-3.5" />
            Task List
          </TabsTrigger>
          <TabsTrigger value="summary">
            <BarChart3 className="h-3.5 w-3.5" />
            Summary
          </TabsTrigger>
        </TabsList>
        <TabsContent value="board" className="mt-4">
          <BoardView />
        </TabsContent>
        <TabsContent value="list" className="mt-4">
          <ListView />
        </TabsContent>
        <TabsContent value="summary" className="mt-4">
          <SummaryView />
        </TabsContent>
      </Tabs>
    </div>
  )
}
