import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { assessmentApi } from './assessmentApi.js'

const EMAIL = /<([^>]+)>/

/** The run is waiting: authors that match no student wrote a large part of the code. The lecturer maps them (or continues without). */
export default function IdentityMapForm({ runId, review, onDone, students = [] }) {
  const authors = Object.entries(review?.evidence?.unmapped_authors || {})
  const roster = review?.evidence?.roster || []
  const [choice, setChoice] = useState({})
  const [busy, setBusy] = useState(false)

  const teamRef = review?.team_ref
  const setupQuery = useQuery({
    queryKey: ['team-setup-for-id-map', teamRef],
    queryFn: () => assessmentApi.setup(teamRef),
    enabled: Boolean(teamRef) && (!students || students.length === 0),
    staleTime: 60000,
  })

  const memberList = students?.length ? students : setupQuery.data?.members || []
  const studentMap = new Map(memberList.map((s) => [String(s.id), s]))

  const getLabel = (id) => {
    const s = studentMap.get(String(id))
    if (!s) return id
    const name = s.name || s.student_number || id
    const num = s.student_number ? ` (${s.student_number})` : ''
    return `${name}${num}`
  }

  const send = async (withoutMapping) => {
    const mapping = withoutMapping ? [] : authors.filter(([a]) => choice[a]).map(([a]) => ({ student_id: choice[a], email: EMAIL.exec(a)?.[1], name: a.split(' <')[0] }))
    if (!withoutMapping && !mapping.length) return toast.error('Choose a student for at least one author')
    setBusy(true)
    try {
      await assessmentApi.identityMap(runId, { mapping, continue_without_mapping: withoutMapping })
      toast.success('Continuing the run')
      onDone?.()
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="rounded-xl border border-amber-300 bg-amber-50 p-4 dark:bg-amber-950/30 space-y-3">
      <div>
        <p className="font-semibold text-sm">The run is waiting for you</p>
        <p className="text-xs text-muted-foreground">{review?.reason}. Say who these authors are so their work is counted.</p>
      </div>
      <ul className="space-y-2">
        {authors.map(([author, u]) => (
          <li key={author} className="flex flex-wrap items-center gap-3 text-sm">
            <span className="font-mono text-xs">{author}</span>
            <span className="text-xs text-muted-foreground">{u.commits} commits, {u.lines} lines</span>
            <select className="ml-auto rounded-md border bg-background px-2 py-1 text-sm font-sans" value={choice[author] || ''} onChange={(e) => setChoice({ ...choice, [author]: e.target.value })}>
              <option value="">Not a student of this team</option>
              {roster.map((id) => (
                <option key={id} value={id}>
                  {getLabel(id)}
                </option>
              ))}
            </select>
          </li>
        ))}
      </ul>
      <div className="flex gap-2">
        <Button size="sm" disabled={busy} onClick={() => send(false)}>Map and continue</Button>
        <Button size="sm" variant="outline" disabled={busy} onClick={() => send(true)}>Continue without mapping</Button>
      </div>
    </div>
  )
}
