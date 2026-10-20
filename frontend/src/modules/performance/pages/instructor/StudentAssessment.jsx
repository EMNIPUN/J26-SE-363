import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import EmptyState from '@/shared/components/EmptyState.jsx'
import { useConfirm } from '@/shared/utils/useConfirm.js'
import { showToast } from '@/shared/utils/toast.jsx'
import { assessmentApi, assessmentKeys } from '../../assessment/assessmentApi.js'
import { markText } from '../../assessment/format.js'
import ResultView from '../../assessment/ResultView.jsx'
import { Avatar } from '../../assessment/visuals.jsx'

function MarkDialog({ open, onClose, result, onSave }) {
  const [mark, setMark] = useState(result?.override?.mark ?? '')
  const [reason, setReason] = useState(result?.override?.reason ?? '')
  const ok = mark !== '' && Number(mark) >= 0 && Number(mark) <= 100 && reason.trim().length >= 10
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Set your own mark</DialogTitle>
          <DialogDescription>The agent predicted {markText(result?.mark)}. Your mark is shown to the student instead, and the prediction stays on record next to it.</DialogDescription>
        </DialogHeader>
        <div className="grid gap-3">
          <label className="grid gap-1 text-sm">Mark (0 to 100)<Input type="number" min="0" max="100" value={mark} onChange={(e) => setMark(e.target.value)} /></label>
          <label className="grid gap-1 text-sm">Why<textarea className="min-h-24 rounded-md border bg-background p-2 text-sm" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="At least 10 characters. This is kept with the mark." /></label>
        </div>
        <DialogFooter>
          {result?.override?.mark != null && <Button variant="ghost" className="mr-auto" onClick={() => onSave(null, '')}>Use the prediction again</Button>}
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button disabled={!ok} onClick={() => onSave(Number(mark), reason)}>Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

/** One student for the lecturer: the mark and why, the evidence behind each factor, what the agent checked, and the lecturer's own mark. */
export default function StudentAssessment() {
  const { teamId, studentId } = useParams()
  const [params] = useSearchParams()
  const sprint = params.get('sprint') || ''
  const qc = useQueryClient()
  const confirm = useConfirm()
  const [dialog, setDialog] = useState(false)
  const results = useQuery({ queryKey: assessmentKeys.results(teamId, sprint), queryFn: () => assessmentApi.results(teamId, sprint), enabled: Boolean(sprint) })
  const result = results.data?.find((r) => r.student_id === studentId)
  const traj = useQuery({ queryKey: assessmentKeys.trajectory(teamId, sprint, studentId), queryFn: () => assessmentApi.trajectory(teamId, sprint, studentId), enabled: Boolean(result) })
  const quiz = useQuery({ queryKey: assessmentKeys.quiz(teamId, sprint, studentId), queryFn: () => assessmentApi.quiz(teamId, sprint, studentId), enabled: Boolean(result) })
  const runs = useQuery({ queryKey: assessmentKeys.runs(teamId, sprint), queryFn: () => assessmentApi.runs(teamId, sprint), enabled: Boolean(sprint) })
  const weights = runs.data?.find((r) => r.summary?.method)?.summary.method.weights
  const latest = runs.data?.[0]
  const back = `/teams/${teamId}/performance/assessment?sprint=${encodeURIComponent(sprint)}`

  const save = async (mark, reason) => {
    try {
      await assessmentApi.setMark(teamId, sprint, studentId, { mark, reason })
      showToast.success(mark == null ? 'The prediction is used again' : 'Your mark is saved')
      setDialog(false)
      qc.invalidateQueries({ queryKey: ['assessment', teamId] })
    } catch (e) {
      showToast.error(e.message)
    }
  }
  const evaluateAgain = async () => {
    const ok = await confirm({ title: `Evaluate ${result.student?.name} again?`, description: 'The whole team is assessed again from the repository as it is now (the agent works on a team at a time). Earlier results stay available.', confirmText: 'Evaluate again' })
    if (!ok) return
    try {
      await assessmentApi.rerun(latest.id)
      showToast.success('Started again')
      qc.invalidateQueries({ queryKey: ['assessment', teamId] })
    } catch (e) {
      showToast.error(e.message)
    }
  }

  if (results.isPending) return <Skeleton className="h-96 w-full" aria-busy="true" />
  if (!result) return <EmptyState title="No result for this student" description="There is no result for this student in this sprint yet." actionLabel="Back to the team" onAction={() => window.history.back()} />

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" asChild aria-label="Back to the team"><Link to={back}><ArrowLeft className="h-4 w-4" /></Link></Button>
          <Avatar name={result.student?.name} size={48} />
          <div>
            <h1 className="text-xl font-semibold tracking-tight text-foreground">{result.student?.name}</h1>
            <p className="text-sm text-muted-foreground">Sprint {sprint}</p>
          </div>
        </div>
        {latest && !['queued', 'running', 'waiting_human'].includes(latest.status) && <Button variant="outline" onClick={evaluateAgain}><RefreshCw className="h-4 w-4" />Re-evaluate</Button>}
      </div>
      <ResultView result={result} weights={weights} mode="lecturer" trajectory={traj.data} quiz={quiz.data} onSetMark={() => setDialog(true)} />
      {dialog && <MarkDialog open onClose={() => setDialog(false)} result={result} onSave={save} />}
    </div>
  )
}
