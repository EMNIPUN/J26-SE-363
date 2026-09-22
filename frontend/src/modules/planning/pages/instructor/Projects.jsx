import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus } from 'lucide-react'
import PageHeader from '../../../../shared/components/PageHeader.jsx'
import Card from '../../../../shared/components/Card.jsx'
import Badge from '../../../../shared/components/Badge.jsx'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { GROUPS as INITIAL_GROUPS } from '../../data/mockData.js'
import { showToast } from '@/shared/utils/toast.jsx'

const STATUS_TONE = {
  'On Track': 'success',
  'Needs Attention': 'warning',
  'At Risk': 'danger',
}

export default function InstructorProjects() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState(INITIAL_GROUPS)
  const [batchFilter, setBatchFilter] = useState('all')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [form, setForm] = useState({ name: '', project: '', batch: 'Y4.1' })

  const batches = ['all', ...new Set(projects.map((p) => p.batch))]
  const filtered = batchFilter === 'all' ? projects : projects.filter((p) => p.batch === batchFilter)

  function createProject() {
    if (!form.name.trim() || !form.project.trim()) return
    const id = `g${Math.floor(Math.random() * 900 + 100)}`
    setProjects((prev) => [
      {
        id,
        name: form.name,
        project: form.project,
        batch: form.batch,
        members: 4,
        qualityGate: 0,
        risk: 'Low',
        openArbitrations: 0,
        status: 'On Track',
        requirementIds: [],
      },
      ...prev,
    ])
    setDialogOpen(false)
    setForm({ name: '', project: '', batch: 'Y4.1' })
    showToast.success('Project created', { description: `${form.project} has been added.` })
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Projects"
        breadcrumb={['Planning', 'Instructor', 'Projects']}
        description="Every project you supervise, with a link into each project's requirement set."
        actions={
          <>
            <Select value={batchFilter} onValueChange={setBatchFilter}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Batch" />
              </SelectTrigger>
              <SelectContent>
                {batches.map((b) => (
                  <SelectItem key={b} value={b}>
                    {b === 'all' ? 'All batches' : b}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button size="sm" onClick={() => setDialogOpen(true)} className="active:scale-[0.98]">
              <Plus className="h-3.5 w-3.5" />
              Create project
            </Button>
          </>
        }
      />

      <Card className="p-0 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Project</TableHead>
              <TableHead>Group</TableHead>
              <TableHead className="w-[90px]">Batch</TableHead>
              <TableHead className="w-[110px]">Quality gate</TableHead>
              <TableHead className="w-[140px]">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.map((p) => (
              <TableRow
                key={p.id}
                className="cursor-pointer"
                onClick={() => navigate(`/planning/instructor/groups/${p.id}`)}
              >
                <TableCell className="font-medium max-w-xs truncate">{p.project}</TableCell>
                <TableCell className="text-muted-foreground">{p.name}</TableCell>
                <TableCell>{p.batch}</TableCell>
                <TableCell>{p.qualityGate ? `${p.qualityGate}%` : '—'}</TableCell>
                <TableCell>
                  <Badge tone={STATUS_TONE[p.status]}>{p.status}</Badge>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create new project</DialogTitle>
            <DialogDescription>Register a new supervised group and project (demo only — not persisted).</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Group name</label>
              <Input value={form.name} onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))} placeholder="Group 24" />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Project title</label>
              <Input
                value={form.project}
                onChange={(e) => setForm((f) => ({ ...f, project: e.target.value }))}
                placeholder="e.g. SkillForge — Peer Learning Platform"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Batch</label>
              <Select value={form.batch} onValueChange={(v) => setForm((f) => ({ ...f, batch: v }))}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Y4.1">Y4.1</SelectItem>
                  <SelectItem value="Y4.2">Y4.2</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={createProject}>Create project</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
