import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useCreateBatch } from '@/shared/hooks/useCohorts'

export default function CreateBatchDialog({ open, onOpenChange, onBatchCreated }) {
  const [form, setForm] = useState({
    id: '',
    name: '',
    code: '',
    year: new Date().getFullYear(),
    semester: 1,
    status: 'active',
  })

  const createBatchMutation = useCreateBatch()

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!form.id || !form.name || !form.code) return

    createBatchMutation.mutate(
      {
        ...form,
        year: Number(form.year),
        semester: Number(form.semester),
      },
      {
        onSuccess: (data) => {
          onOpenChange(false)
          if (onBatchCreated) onBatchCreated(data.id)
          setForm({
            id: '',
            name: '',
            code: '',
            year: new Date().getFullYear(),
            semester: 1,
            status: 'active',
          })
        },
      }
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>Create Academic Cohort / Batch</DialogTitle>
            <DialogDescription>
              Register a new academic cohort for student project supervision.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 text-xs">
            <div>
              <label className="block font-medium text-foreground mb-1">Batch Identifier Slug *</label>
              <Input
                placeholder="e.g. batch-2026-y4s1"
                value={form.id}
                onChange={(e) => setForm({ ...form, id: e.target.value })}
                required
              />
            </div>

            <div>
              <label className="block font-medium text-foreground mb-1">Display Title *</label>
              <Input
                placeholder="e.g. 2026 — Year 4 Semester 1"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
              />
            </div>

            <div>
              <label className="block font-medium text-foreground mb-1">Academic Code *</label>
              <Input
                placeholder="e.g. Y4.S1.2026"
                value={form.code}
                onChange={(e) => setForm({ ...form, code: e.target.value })}
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block font-medium text-foreground mb-1">Year</label>
                <Input
                  type="number"
                  value={form.year}
                  onChange={(e) => setForm({ ...form, year: Number(e.target.value) })}
                  required
                />
              </div>
              <div>
                <label className="block font-medium text-foreground mb-1">Semester</label>
                <Select
                  value={String(form.semester)}
                  onValueChange={(val) => setForm({ ...form, semester: Number(val) })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Semester" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">Semester 1</SelectItem>
                    <SelectItem value="2">Semester 2</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={createBatchMutation.isPending}
            >
              {createBatchMutation.isPending ? 'Creating...' : 'Create Batch'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
