import { ClipboardCopy } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { reviewRequestText } from '../lib/format.js'

// Nothing is sent or stored: the request is copied so the student can paste it to their lecturer (the pages are read-only).
export default function RequestReviewButton({ team, run, finding }) {
  async function copy() {
    const text = reviewRequestText({ team, run, finding })
    try {
      await navigator.clipboard.writeText(text)
      toast.success('Review request copied. Paste it into a message to your lecturer.')
    } catch {
      toast.error(`Could not copy. Select and copy this instead:\n${text}`)
    }
  }
  return (
    <Button size="sm" variant="outline" onClick={copy} data-slot="request-review">
      <ClipboardCopy className="h-4 w-4" /> Request review
    </Button>
  )
}
