import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { assessmentApi } from './assessmentApi.js'

function Item({ review, onChanged }) {
  const [mark, setMark] = useState('')
  const [reason, setReason] = useState('')
  const [open, setOpen] = useState(false)
  const act = async (decision) => {
    const body = decision === 'override' ? { decision, mark: Number(mark), reason } : { decision, reason }
    await assessmentApi.decide(review.id, body)
    toast.success(decision === 'override' ? 'Mark set' : decision === 'rerun' ? 'Run started again' : 'Accepted')
    onChanged()
  }
  return (
    <li className="rounded-xl border bg-card p-4 space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm"><span className="font-semibold">{review.student_id || 'Team'}</span> · sprint {review.sprint_id} · {review.kind.replace('_', ' ')}</p>
        <Link className="text-xs text-primary underline" to={`../runs/${review.run_id}`}>Open the run</Link>
      </div>
      <p className="text-sm">{review.reason}</p>
      {review.kind === 'identity_mapping' ? (
        <p className="text-xs text-muted-foreground">Answer this on the run page (the run is waiting for it).</p>
      ) : open ? (
        <div className="flex flex-wrap gap-2 items-center">
          <Input className="w-24" type="number" min="0" max="100" placeholder="Mark" value={mark} onChange={(e) => setMark(e.target.value)} />
          <Input className="flex-1 min-w-48" placeholder="Why (at least 10 characters)" value={reason} onChange={(e) => setReason(e.target.value)} />
          <Button size="sm" disabled={!mark || reason.trim().length < 10} onClick={() => act('override')}>Set mark</Button>
          <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>Cancel</Button>
        </div>
      ) : (
        <div className="flex gap-2">
          <Button size="sm" onClick={() => act('accept')}>Accept the prediction</Button>
          <Button size="sm" variant="outline" onClick={() => setOpen(true)}>Override</Button>
          <Button size="sm" variant="outline" onClick={() => act('rerun')}>Run again</Button>
        </div>
      )}
    </li>
  )
}

export default function ReviewQueue({ team }) {
  const client = useQueryClient()
  const q = useQuery({ queryKey: ['perf-reviews', 'open'], queryFn: () => assessmentApi.reviews('open') })
  const list = (q.data || []).filter((r) => !team || r.team_ref === team)
  if (!list.length) return <p className="text-sm text-muted-foreground">Nothing to review.</p>
  return <ul className="space-y-3">{list.map((r) => <Item key={r.id} review={r} onChanged={() => { client.invalidateQueries({ queryKey: ['perf-reviews'] }); client.invalidateQueries({ queryKey: ['perf-results'] }) }} />)}</ul>
}
