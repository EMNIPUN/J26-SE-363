import { useState, useMemo } from 'react'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
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
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useCreateBatch } from '@/shared/hooks/useCohorts'
import { Search, Check, Plus, ChevronsUpDown, Sparkles, AlertCircle } from 'lucide-react'
import { toast } from 'sonner'

export default function BatchCombobox({ value, onChange, batches = [] }) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')

  // Confirmation popup state
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [newBatchForm, setNewBatchForm] = useState({
    id: '',
    name: '',
    code: '',
    year: new Date().getFullYear(),
    semester: 1,
    status: 'active',
  })

  const createBatchMutation = useCreateBatch()

  // Selected batch object
  const selectedBatch = useMemo(() => {
    return batches.find((b) => b.id === value) || null
  }, [batches, value])

  // Filter batches by typed search
  const filteredBatches = useMemo(() => {
    const q = search.toLowerCase().trim()
    if (!q) return batches
    return batches.filter(
      (b) =>
        b.name?.toLowerCase().includes(q) ||
        b.code?.toLowerCase().includes(q) ||
        b.id?.toLowerCase().includes(q)
    )
  }, [batches, search])

  // Check if search matches an existing batch exactly
  const hasExactMatch = useMemo(() => {
    const q = search.toLowerCase().trim()
    if (!q) return true
    return batches.some(
      (b) =>
        b.name?.toLowerCase() === q ||
        b.code?.toLowerCase() === q ||
        b.id?.toLowerCase() === q
    )
  }, [batches, search])

  // Helper to convert spaces and words to dash-separated format
  const toDashedSlug = (text) => {
    return text
      .toLowerCase()
      .replace(/[_\s]+/g, '-')
      .replace(/[^a-z0-9-]/g, '')
      .replace(/-+/g, '-')
  }

  // Handle clicking "+ Create <search> [New]"
  const handleInitiateCreate = () => {
    const query = search.trim()
    if (!query) return

    // Smart-extract year and semester if present in query (e.g. "2027 Y4S2" or "Y4 S1 2027")
    const yearMatch = query.match(/\b(20\d{2})\b/)
    const semesterMatch = query.match(/[sS]([12])/)

    const yearVal = yearMatch ? Number(yearMatch[1]) : new Date().getFullYear() + 1
    const semVal = semesterMatch ? Number(semesterMatch[1]) : 1

    const rawSlug = toDashedSlug(query).replace(/^-+|-+$/g, '')
    const autoSlug = rawSlug.startsWith('batch-') ? rawSlug : `batch-${rawSlug}`
    const autoCode = `Y4.S${semVal}.${yearVal}`

    setNewBatchForm({
      id: autoSlug,
      name: query,
      code: autoCode,
      year: yearVal,
      semester: semVal,
      status: 'active',
    })

    setOpen(false)
    setConfirmOpen(true)
  }

  // Confirm creation
  const handleConfirmCreate = async (e) => {
    e.preventDefault()
    if (!newBatchForm.id || !newBatchForm.name || !newBatchForm.code) {
      toast.error('All required batch fields must be specified.')
      return
    }

    try {
      const payload = {
        ...newBatchForm,
        year: Number(newBatchForm.year),
        semester: Number(newBatchForm.semester),
      }
      const created = await createBatchMutation.mutateAsync(payload)
      setConfirmOpen(false)
      setSearch('')
      onChange(created.id)
    } catch {
      // toast is already handled by useCreateBatch
    }
  }

  const handleSelectExisting = (batchId) => {
    onChange(batchId)
    setOpen(false)
    setSearch('')
  }

  return (
    <>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            role="combobox"
            aria-expanded={open}
            className="flex h-9 w-full items-center justify-between rounded-lg border border-border bg-card px-3 text-xs text-foreground transition-colors hover:bg-muted/60 focus:outline-none focus:ring-1 focus:ring-primary cursor-pointer"
          >
            <span className="truncate font-medium">
              {selectedBatch
                ? `${selectedBatch.name || selectedBatch.code} (${selectedBatch.status})`
                : value
                ? value
                : 'Select or search cohort batch...'}
            </span>
            <ChevronsUpDown className="h-3.5 w-3.5 shrink-0 opacity-50 ml-2" />
          </button>
        </PopoverTrigger>

        <PopoverContent align="start" className="w-[min(92vw,460px)] p-0 shadow-xl border-border">
          {/* SEARCH INPUT */}
          <div className="p-2 border-b border-border bg-muted/30">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search batches or type to create new..."
                className="h-8 pl-8 text-xs bg-background"
                autoFocus
              />
            </div>
          </div>

          {/* SUGGESTION ITEM FOR NEW BATCH */}
          {!hasExactMatch && search.trim().length > 0 && (
            <div className="p-1 border-b border-border bg-primary/5">
              <button
                type="button"
                onClick={handleInitiateCreate}
                className="w-full text-left p-2 rounded-md text-xs hover:bg-primary/10 transition-colors flex items-center justify-between gap-2 cursor-pointer text-primary font-medium"
              >
                <div className="flex items-center gap-2 truncate">
                  <Plus className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">
                    Create &quot;<strong className="text-foreground">{search.trim()}</strong>&quot;
                    <span className="text-[10px] text-muted-foreground ml-1.5 font-mono">
                      ({toDashedSlug(search.trim()).startsWith('batch-') ? toDashedSlug(search.trim()) : `batch-${toDashedSlug(search.trim())}`})
                    </span>
                  </span>
                </div>
                <Badge variant="outline" className="bg-primary/10 text-primary border-primary/30 text-[10px] uppercase font-bold shrink-0">
                  New
                </Badge>
              </button>
            </div>
          )}

          {/* BATCH LIST */}
          <div className="max-h-56 overflow-y-auto p-1 space-y-0.5 column-scroll-contain">
            {filteredBatches.length === 0 && hasExactMatch ? (
              <div className="py-6 text-center text-xs text-muted-foreground">
                No matching batches found.
              </div>
            ) : (
              filteredBatches.map((b) => {
                const isSelected = b.id === value
                return (
                  <button
                    key={b.id}
                    type="button"
                    onClick={() => handleSelectExisting(b.id)}
                    className={`w-full text-left px-2.5 py-2 rounded-md text-xs transition-colors flex items-center justify-between gap-2 cursor-pointer ${
                      isSelected
                        ? 'bg-muted text-foreground font-semibold'
                        : 'hover:bg-accent text-foreground'
                    }`}
                  >
                    <div className="truncate min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-foreground truncate">{b.name || b.code}</span>
                        <span className="font-mono text-[10px] text-muted-foreground">{b.code}</span>
                      </div>
                      <span className="text-[10px] font-mono text-muted-foreground block truncate">
                        ID: {b.id} • Year {b.year} Sem {b.semester}
                      </span>
                    </div>

                    {isSelected && <Check className="h-4 w-4 text-primary shrink-0" />}
                  </button>
                )
              })
            )}
          </div>
        </PopoverContent>
      </Popover>

      {/* CONFIRMATION POPUP FOR CREATING NEW BATCH */}
      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent className="sm:max-w-md p-6">
          <form onSubmit={handleConfirmCreate} className="space-y-4">
            <DialogHeader>
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-primary/10 text-primary">
                  <Sparkles className="h-5 w-5" />
                </div>
                <div>
                  <DialogTitle className="text-base font-bold">Confirm New Academic Batch</DialogTitle>
                  <DialogDescription className="text-xs">
                    Do you want to create and register this new academic cohort?
                  </DialogDescription>
                </div>
              </div>
            </DialogHeader>

            <div className="space-y-3 pt-2 text-xs">
              <div>
                <label className="block font-medium text-foreground mb-1">Batch Title *</label>
                <Input
                  value={newBatchForm.name}
                  onChange={(e) => {
                    const val = e.target.value
                    const rawSlug = toDashedSlug(val).replace(/^-+|-+$/g, '')
                    const autoSlug = rawSlug ? (rawSlug.startsWith('batch-') ? rawSlug : `batch-${rawSlug}`) : ''
                    setNewBatchForm((prev) => ({
                      ...prev,
                      name: val,
                      id: autoSlug,
                    }))
                  }}
                  placeholder="e.g. 2027 — Year 4 Semester 1"
                  className="h-8 text-xs"
                  required
                />
              </div>

              <div>
                <label className="block font-medium text-foreground mb-1">Batch Identifier Slug (Auto-dashed) *</label>
                <Input
                  value={newBatchForm.id}
                  onChange={(e) => {
                    const dashed = toDashedSlug(e.target.value)
                    setNewBatchForm((prev) => ({ ...prev, id: dashed }))
                  }}
                  placeholder="e.g. batch-2027-y4-s1"
                  className="h-8 text-xs font-mono"
                  required
                />
                <p className="text-[10px] text-muted-foreground mt-0.5">
                  Spaces and symbols are automatically converted to hyphens.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-foreground mb-1">Academic Code *</label>
                  <Input
                    value={newBatchForm.code}
                    onChange={(e) => setNewBatchForm({ ...newBatchForm, code: e.target.value })}
                    placeholder="e.g. Y4.S1.2027"
                    className="h-8 text-xs font-mono"
                    required
                  />
                </div>
                <div>
                  <label className="block font-medium text-foreground mb-1">Year</label>
                  <Input
                    type="number"
                    value={newBatchForm.year}
                    onChange={(e) => setNewBatchForm({ ...newBatchForm, year: Number(e.target.value) })}
                    className="h-8 text-xs"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block font-medium text-foreground mb-1">Semester</label>
                <Select
                  value={String(newBatchForm.semester)}
                  onValueChange={(val) => setNewBatchForm({ ...newBatchForm, semester: Number(val) })}
                >
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue placeholder="Semester" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1" className="text-xs">Semester 1</SelectItem>
                    <SelectItem value="2" className="text-xs">Semester 2</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <DialogFooter className="pt-3 border-t border-border flex items-center justify-end gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setConfirmOpen(false)}
              >
                No, Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={createBatchMutation.isPending}
              >
                {createBatchMutation.isPending ? 'Creating...' : 'Yes, Create Batch'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </>
  )
}
