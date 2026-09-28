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
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { toast } from 'sonner'
import { Sparkles, PlusCircle, CheckCircle2 } from 'lucide-react'
import { actions } from '../context/planningStore.js'

export default function NewRequirementModal({ open, onOpenChange, existingCount = 8 }) {
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [priority, setPriority] = useState('High')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!title.trim() || !description.trim()) return

    setIsSubmitting(true)
    const nextNum = 100 + existingCount + 1
    const newId = `REQ-${nextNum}`

    // Simulate AI scoring based on text completeness
    const wordCount = description.trim().split(/\s+/).length
    const scoreClarity = Math.min(95, Math.max(60, 70 + (wordCount > 10 ? 15 : 0)))
    const scoreCompleteness = Math.min(95, Math.max(55, 65 + (description.toLowerCase().includes('shall') ? 20 : 5)))
    const scoreConsistency = 85
    const scoreTestability = Math.min(96, Math.max(50, 70 + (description.toLowerCase().includes('within') || description.toLowerCase().includes('allow') ? 18 : 5)))
    const scoreFeasibility = 90
    const scoreScope = 88

    const overallScore = Math.round(
      (scoreClarity + scoreCompleteness + scoreConsistency + scoreTestability + scoreFeasibility + scoreScope) / 6,
    )
    const status = overallScore >= 70 ? 'Passing' : overallScore >= 50 ? 'Needs Review' : 'Failing'

    const newReq = {
      id: newId,
      title: title.trim(),
      description: description.trim(),
      priority,
      status,
      overallScore,
      dimensionScores: {
        clarity: scoreClarity,
        completeness: scoreCompleteness,
        consistency: scoreConsistency,
        testability: scoreTestability,
        feasibility: scoreFeasibility,
        scope: scoreScope,
      },
      suggestedRewrite: status !== 'Passing' ? 'Clarify acceptance threshold and avoid ambiguous terms.' : null,
      lastChecked: new Date().toISOString(),
    }

    setTimeout(() => {
      actions.addRequirement(newReq)
      setIsSubmitting(false)
      toast.success(`${newId} created & scored`, {
        description: `Quality Analysis Agent scored it at ${overallScore}% (${status}).`,
      })
      setTitle('')
      setDescription('')
      onOpenChange(false)
    }, 450)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1 rounded bg-primary/10 text-primary">
              <PlusCircle className="h-4 w-4" />
            </span>
            <DialogTitle className="text-lg font-bold">Add Functional Requirement</DialogTitle>
          </div>
          <DialogDescription className="text-xs">
            Submit a new requirement to the SRS quality pipeline. The automated gatekeeper will instantly evaluate clarity, testability, and feasibility.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-3.5 text-xs">
          <div>
            <label className="font-semibold text-foreground block mb-1">Requirement Title</label>
            <Input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Student can export personalized study roadmap as PDF"
              className="text-xs h-9"
              required
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="font-semibold text-foreground block mb-1">Priority Level</label>
              <Select value={priority} onValueChange={setPriority}>
                <SelectTrigger className="text-xs h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="High">High (Must Have)</SelectItem>
                  <SelectItem value="Medium">Medium (Should Have)</SelectItem>
                  <SelectItem value="Low">Low (Could Have)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="font-semibold text-foreground block mb-1">Specification Standard</label>
              <Input value="IEEE 830 / ISO 29148" disabled className="text-xs h-9 bg-muted/50 text-muted-foreground" />
            </div>
          </div>

          <div>
            <label className="font-semibold text-foreground block mb-1">
              Specification Description (<span className="font-mono text-primary font-normal">The system shall...</span>)
            </label>
            <Textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="The system shall allow authenticated students to download their complete milestone curriculum in structured format..."
              rows={4}
              className="text-xs leading-relaxed"
              required
            />
          </div>

          <div className="p-2.5 rounded-lg bg-primary/5 border border-primary/15 text-[11px] text-muted-foreground flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary shrink-0" />
            <span>
              The Quality Analysis Agent will automatically calculate a 6-dimension radar score upon submission.
            </span>
          </div>

          <DialogFooter className="pt-2 gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onOpenChange(false)}
              className="text-xs cursor-pointer"
            >
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={isSubmitting} className="text-xs cursor-pointer gap-1.5">
              <PlusCircle className="h-3.5 w-3.5" />
              {isSubmitting ? 'Evaluating...' : 'Submit & Score Requirement'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
