import { useMemo, useState } from 'react'
import PropTypes from 'prop-types'
import { toast } from 'sonner'
import { ArrowRight, GitCommitHorizontal, UserCheck, UserX } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { assessmentApi } from './assessmentApi.js'
import { Avatar } from './visuals.jsx'

const NONE = '__none__'
const tokens = (text) => new Set(String(text || '').toLowerCase().split(/[^a-z0-9]+/).filter((t) => t.length > 2))

/** The student whose name shares at least two words with the author's git name (or whose login is in the e-mail), when exactly one does. */
function suggest(author, students) {
  const mine = tokens(author.name)
  const hits = students.filter((s) => {
    const theirs = tokens(s.name)
    return [...mine].filter((t) => theirs.has(t)).length >= 2 || (s.login && author.email.toLowerCase().includes(s.login.toLowerCase()))
  })
  return hits.length === 1 ? hits[0].id : null
}

/** "Name <email>" as git records it, split into the two parts. */
function parseAuthor(author) {
  const m = /^(.*?)\s*<([^>]+)>\s*$/.exec(author)
  return m ? { name: m[1] || m[2], email: m[2] } : { name: author, email: '' }
}

/**
 * The run has found commit authors that match no student, and asks who they are. Shown in a popup: every author is a card (who, how much they wrote, a bar for their share of the new code)
 * with a menu to pick the student they are. Authors left as "not in this team" are listed in the report and their work is not counted for anyone.
 */
export default function IdentityDecision({ open, onOpenChange, review, names = {}, onDone }) {
  const [choice, setChoice] = useState({})
  const [busy, setBusy] = useState(false)
  const field = (review?.form?.fields || []).find((f) => f.type === 'author_map')
  const evidence = review?.evidence?.unmapped_authors || {}
  const authors = useMemo(() => (field?.authors || Object.keys(evidence).map((author) => ({ author }))).map((a) => {
    const stats = evidence[a.author] || {}
    return { ...a, ...parseAuthor(a.author), commits: a.commits || stats.commits || 0, lines: a.lines || stats.lines || 0 }
  }), [field, evidence])
  const students = (field?.students || (review?.evidence?.roster || []).map((id) => ({ id }))).map((s) => ({ id: s.id, name: names[s.id] || (s.name && s.name !== s.id ? s.name : '') || 'Team member' }))
  const suggested = useMemo(() => Object.fromEntries(authors.map((a) => [a.author, suggest(a, students)])), [authors, students])  // eslint-disable-line react-hooks/exhaustive-deps
  const total = authors.reduce((n, a) => n + a.lines, 0) || 1
  const picked = (a) => choice[a.author] ?? suggested[a.author] ?? NONE
  const mapped = authors.filter((a) => picked(a) !== NONE)
  const decisionField = (review?.form?.fields || []).find((f) => f.id === 'decision')

  const send = async (withoutMapping) => {
    setBusy(true)
    try {
      const answers = { decision: withoutMapping ? 'continue' : 'map', mapping: withoutMapping ? [] : mapped.map((a) => ({ author: a.author, student_id: picked(a) })) }
      if (review.form && decisionField) await assessmentApi.answer(review.id, answers)
      else await assessmentApi.identityMap(review.run_id, { mapping: answers.mapping.map((m) => ({ student_id: m.student_id, email: parseAuthor(m.author).email, name: parseAuthor(m.author).name })), continue_without_mapping: withoutMapping })
      toast.success(withoutMapping ? 'Continuing without mapping' : `${mapped.length} author${mapped.length === 1 ? '' : 's'} mapped, continuing`)
      onOpenChange(false)
      onDone?.()
    } catch (e) {
      toast.error(e?.message || 'The decision could not be sent')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[88vh] gap-0 overflow-hidden p-0 sm:max-w-2xl">
        <DialogHeader className="border-b bg-amber-50 px-6 py-5 text-left dark:bg-amber-950/30">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-500/15 text-amber-600"><UserCheck className="h-5 w-5" aria-hidden="true" /></span>
            <div className="min-w-0 space-y-1">
              <DialogTitle className="text-lg">Who wrote this code?</DialogTitle>
              <DialogDescription className="text-sm leading-relaxed">
                {review?.reason ? `${review.reason}. ` : ''}The agent cannot tell which student these {authors.length} commit author{authors.length === 1 ? ' is' : 's are'}. Choose the student for each one so their work is counted. If none is chosen, nobody is credited with that work, so a student whose commits are all unmapped will show no activity in this sprint.
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <ul className="max-h-[52vh] space-y-3 overflow-y-auto px-6 py-5">
          {authors.map((a) => {
            const value = picked(a)
            return (
              <li key={a.author} className="rounded-xl border bg-card p-4 shadow-sm">
                <div className="flex flex-wrap items-center gap-3">
                  <Avatar name={a.name} size={40} />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold text-foreground">{a.name}{suggested[a.author] && choice[a.author] === undefined && <span className="ml-2 rounded-full bg-emerald-100 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-700">looks like a team member</span>}</p>
                    {a.email && <p className="truncate text-xs text-muted-foreground">{a.email}</p>}
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <GitCommitHorizontal className="h-3.5 w-3.5" aria-hidden="true" />{a.commits} commit{a.commits === 1 ? '' : 's'} · {a.lines.toLocaleString()} lines
                  </div>
                </div>
                <div className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-muted" title={`${Math.round((a.lines / total) * 100)}% of the new code`}>
                  <div className="h-full rounded-full bg-amber-500" style={{ width: `${Math.max(3, (a.lines / total) * 100)}%` }} />
                </div>
                <div className="mt-3 flex items-center gap-2">
                  <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <Select value={value} onValueChange={(v) => setChoice((c) => ({ ...c, [a.author]: v }))}>
                    <SelectTrigger className="h-9 flex-1" aria-label={`Student for ${a.name}`}><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value={NONE}><span className="inline-flex items-center gap-2 text-muted-foreground"><UserX className="h-4 w-4" aria-hidden="true" />Not in this team</span></SelectItem>
                      {students.map((s) => <SelectItem key={s.id} value={s.id}>{s.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </li>
            )
          })}
        </ul>

        <DialogFooter className="flex-col gap-2 border-t bg-muted/30 px-6 py-4 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-muted-foreground">{mapped.length} of {authors.length} mapped. Later sprints will not ask again about authors you leave as not in this team.</p>
          <div className="flex gap-2">
            <Button variant="outline" disabled={busy} onClick={() => send(true)}>Continue without mapping</Button>
            <Button disabled={busy || mapped.length === 0} onClick={() => send(false)}>Map {mapped.length || ''} and continue</Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
IdentityDecision.propTypes = { open: PropTypes.bool, onOpenChange: PropTypes.func, review: PropTypes.object, names: PropTypes.object, onDone: PropTypes.func }
