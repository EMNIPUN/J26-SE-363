import { useState } from 'react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { assessmentApi } from './assessmentApi.js'
import { parseRoster, rosterToText } from './rosterText.js'

const emptySprint = () => ({ id: '', start: '', end: '' })

/** Start or change tracking of a team: repository, board, sprint dates and the roster that maps commit authors to students. */
export default function TrackingForm({ initial, onSaved }) {
  const cfg = initial?.config || {}
  const [team, setTeam] = useState(initial?.team_ref || '')
  const [repo, setRepo] = useState(initial?.repo_url || '')
  const [board, setBoard] = useState(initial?.board_ref || '')
  const [roster, setRoster] = useState(rosterToText(cfg.roster))
  const [sprints, setSprints] = useState(cfg.sprints?.length ? cfg.sprints : [emptySprint()])
  const [release, setRelease] = useState(cfg.release_to_students ?? true)
  const [busy, setBusy] = useState(false)
  const parsed = parseRoster(roster)

  const save = async (e) => {
    e.preventDefault()
    if (parsed.problems.length) return toast.error(parsed.problems[0])
    setBusy(true)
    try {
      const body = { repo_url: repo.trim(), board_ref: board.trim() || null, roster: parsed.students, release_to_students: release, sprints: sprints.filter((s) => s.id && s.start && s.end) }
      await assessmentApi.saveTracking(team.trim(), body)
      toast.success('Tracking saved')
      onSaved?.(team.trim())
    } finally {
      setBusy(false)
    }
  }
  const setSprint = (i, k, v) => setSprints(sprints.map((s, j) => (j === i ? { ...s, [k]: v } : s)))

  return (
    <form onSubmit={save} className="space-y-4 rounded-xl border bg-card p-5">
      <div className="grid gap-3 md:grid-cols-3">
        <label className="text-sm space-y-1">Team reference<Input required disabled={Boolean(initial)} value={team} onChange={(e) => setTeam(e.target.value)} placeholder="T9" /></label>
        <label className="text-sm space-y-1 md:col-span-2">GitHub repository<Input required type="url" value={repo} onChange={(e) => setRepo(e.target.value)} placeholder="https://github.com/owner/project" /></label>
        <label className="text-sm space-y-1">Scrum board team id<Input value={board} onChange={(e) => setBoard(e.target.value)} placeholder="same as the team reference" /></label>
      </div>
      <div className="space-y-2">
        <p className="text-sm font-medium">Sprints</p>
        {sprints.map((s, i) => (
          <div key={i} className="grid gap-2 grid-cols-3">
            <Input aria-label="Sprint id" placeholder="Sprint id (as on the board)" value={s.id} onChange={(e) => setSprint(i, 'id', e.target.value)} />
            <Input aria-label="Start" type="date" value={s.start} onChange={(e) => setSprint(i, 'start', e.target.value)} />
            <Input aria-label="End" type="date" value={s.end} onChange={(e) => setSprint(i, 'end', e.target.value)} />
          </div>
        ))}
        <Button type="button" size="sm" variant="outline" onClick={() => setSprints([...sprints, emptySprint()])}>Add a sprint</Button>
      </div>
      <label className="text-sm space-y-1 block">
        Roster, one student per line: <span className="font-mono text-xs">student id, GitHub login, commit e-mails, name</span>
        <Textarea rows={6} className="font-mono text-xs" value={roster} onChange={(e) => setRoster(e.target.value)} placeholder="STU-001, amy-gh, amy@uni.lk amy@gmail.com, Amy Perera" />
      </label>
      {parsed.problems.length > 0 && <ul className="text-xs text-destructive">{parsed.problems.map((p) => <li key={p}>{p}</li>)}</ul>}
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={release} onChange={(e) => setRelease(e.target.checked)} /> Students can see their own predicted marks and feedback</label>
      <Button type="submit" disabled={busy}>Save tracking</Button>
    </form>
  )
}
