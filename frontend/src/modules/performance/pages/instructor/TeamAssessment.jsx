import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, AlertTriangle, ArrowRight, Flag, Play, RefreshCw, Settings2, TrendingUp, Users, Workflow } from 'lucide-react'
import { Button } from '@/components/ui/button'
import PageHeader from '@/shared/components/PageHeader.jsx'
import { useTeam } from '@/shared/hooks/useTeams.js'
import { useConfirm } from '@/shared/utils/useConfirm.js'
import { showToast } from '@/shared/utils/toast.jsx'
import { assessmentApi, assessmentKeys } from '../../assessment/assessmentApi.js'
import { when } from '../../assessment/format.js'
import { RunPill } from '../../assessment/visuals.jsx'
import { Skel, StatRowSkeleton, TableSkeleton } from '../../assessment/Reveal.jsx'
import SprintSelect from '../../assessment/SprintSelect.jsx'
import ResultsTab from './team/ResultsTab.jsx'
import DevelopmentTab from './team/DevelopmentTab.jsx'
import { ReviewsTab, RunsTab } from './team/OtherTabs.jsx'
import SetupTab from './team/SetupTab.jsx'

const TABS = [
  { id: 'results', label: 'Results', icon: Users },
  { id: 'development', label: 'Development', icon: TrendingUp },
  { id: 'runs', label: 'Runs', icon: Workflow },
  { id: 'reviews', label: 'Reviews', icon: Flag },
  { id: 'setup', label: 'Setup', icon: Settings2 },
]
const ACTIVE = ['queued', 'running', 'waiting_human']
const TAB_HELP = {
  results: 'Individual contribution of every student, with the evidence behind each mark.',
  development: 'How each student\'s predicted mark moved while the sprint ran.',
  runs: 'Every assessment run, with its pipeline and report.',
  reviews: 'What the agent could not settle and left to a person.',
  setup: 'Whether everything the agent needs is in place, and who is connected.',
}

/** The lecturer's page for one team: results first, then how they developed, the runs behind them, what needs a decision, and the setup. */
export default function TeamAssessment() {
  const { teamId, tab: tabParam } = useParams()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const qc = useQueryClient()
  const confirm = useConfirm()
  const team = useTeam(teamId)
  const code = team.data?.code || teamId
  const tracking = useQuery({ queryKey: assessmentKeys.tracking(teamId), queryFn: () => assessmentApi.tracking(teamId), retry: false })
  const readiness = useQuery({ queryKey: assessmentKeys.readiness(teamId), queryFn: () => assessmentApi.readiness(teamId), refetchInterval: 20000 })
  const sprints = useMemo(() => tracking.data?.config?.sprints ?? [], [tracking.data])
  const [chosen, setChosen] = useState('')
  const sprint = chosen || params.get('sprint') || sprints[sprints.length - 1]?.id || ''
  const tab = TABS.some((t) => t.id === tabParam) ? tabParam : 'results'
  const runs = useQuery({ queryKey: assessmentKeys.runs(teamId, sprint), queryFn: () => assessmentApi.runs(teamId, sprint), enabled: Boolean(sprint), refetchInterval: 6000 })
  const results = useQuery({ queryKey: assessmentKeys.results(teamId, sprint), queryFn: () => assessmentApi.results(teamId, sprint), enabled: Boolean(sprint), refetchInterval: 15000 })
  const [busy, setBusy] = useState(false)
  const base = `/teams/${teamId}/performance`

  useEffect(() => { if (!params.get('sprint') && sprint) setParams((p) => { const n = new URLSearchParams(p); n.set('sprint', sprint); return n }, { replace: true }) }, [sprint, params, setParams])
  const go = (next) => setParams((p) => { const n = new URLSearchParams(p); Object.entries(next).forEach(([k, v]) => n.set(k, v)); return n })
  const openTab = (id) => navigate(`${base}/team/${id}${sprint ? `?sprint=${encodeURIComponent(sprint)}` : ''}`)

  const latest = runs.data?.[0]
  const active = runs.data?.find((r) => ACTIVE.includes(r.status))
  const ready = readiness.data?.ready !== false
  const refresh = () => qc.invalidateQueries({ queryKey: ['assessment', teamId] })

  const start = async (mode) => {
    setBusy(true)
    try {
      const r = await assessmentApi.startRun(teamId, sprint, mode)
      showToast.success(mode === 'final' ? 'Final assessment started' : 'Snapshot started')
      refresh()
      return r
    } catch (e) {
      showToast.error(e.message)
    } finally {
      setBusy(false)
    }
  }
  const rerun = async (run) => {
    const ok = await confirm({ title: 'Evaluate again?', description: `A new ${run.mode === 'final' ? 'final assessment' : 'snapshot'} of sprint ${run.sprint_id} starts from the repository as it is now. The earlier run and its results stay available.`, confirmText: 'Evaluate again' })
    if (!ok) return
    setBusy(true)
    try {
      await assessmentApi.rerun(run.id)
      showToast.success('Started again')
      refresh()
    } catch (e) {
      showToast.error(e.message)
    } finally {
      setBusy(false)
    }
  }
  const report = async (id) => {
    const text = await assessmentApi.report(id)
    const url = URL.createObjectURL(new Blob([text], { type: 'text/markdown' }))
    Object.assign(document.createElement('a'), { href: url, download: `assessment-${code}-${sprint}.md` }).click()
    URL.revokeObjectURL(url)
  }

  if (team.isPending) {
    return (
      <div className="space-y-6" aria-busy="true">
        <div className="flex flex-wrap items-end justify-between gap-4"><div className="space-y-2"><Skel className="h-8 w-56" /><Skel className="h-3 w-80 bg-muted/70" /></div><div className="flex gap-2"><Skel className="h-10 w-48 rounded-xl" /><Skel className="h-10 w-28" /><Skel className="h-10 w-40" /></div></div>
        <StatRowSkeleton />
        <TableSkeleton rows={4} columns={7} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Team · ${TABS.find((t) => t.id === tab).label}`}
        description={`${team.data?.name ?? code}. ${TAB_HELP[tab]}`}
        actions={
          <>
            {sprints.length > 0 && (
              <SprintSelect sprints={sprints} value={sprint} onChange={(id) => { setChosen(id); go({ sprint: id }) }} />
            )}
            <Button variant="outline" disabled={busy || !ready || !sprint || Boolean(active)} onClick={() => start('snapshot')} title="Where the team is right now. Marks are provisional."><Activity className="h-4 w-4" />Snapshot</Button>
            <Button disabled={busy || !ready || !sprint || Boolean(active)} onClick={() => start('final')} title="For a finished sprint. Also asks each student a question about their code."><Play className="h-4 w-4" />Final assessment</Button>
            {latest && !active && <Button variant="ghost" disabled={busy} onClick={() => rerun(latest)}><RefreshCw className="h-4 w-4" />Re-evaluate</Button>}
          </>
        }
      />

      {!sprints.length && (
        <div className="rounded-xl border border-dashed p-5 text-sm">
          <p className="font-medium">No sprint to assess yet</p>
          <p className="mt-1 text-muted-foreground">The agent reads one sprint at a time. Sprints come from the team's Scrum board and appear here once the board has them. Setup shows what is still missing.</p>
          <Button size="sm" className="mt-3" onClick={() => openTab('setup')}>Open Setup</Button>
        </div>
      )}
      {sprints.length > 0 && !ready && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-900 dark:bg-amber-950/30">
          <div className="flex gap-3"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" aria-hidden="true" /><div><p className="font-medium text-amber-900 dark:text-amber-200">This team cannot be assessed yet</p><ul className="mt-1 list-disc pl-4 text-amber-800 dark:text-amber-300">{readiness.data.blockers.map((b) => <li key={b}>{b}</li>)}</ul></div></div>
          <Button size="sm" variant="outline" asChild><Link to={`/teams/${teamId}/members`}>Link GitHub<ArrowRight className="h-4 w-4" /></Link></Button>
        </div>
      )}
      {active && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-primary/30 bg-primary/5 p-4">
          <div className="flex items-center gap-3 text-sm"><RunPill status={active.status} /><span>{active.mode === 'final' ? 'Final assessment' : 'Snapshot'} of sprint {active.sprint_id} started {when(active.created_at)}.</span></div>
          <Button size="sm" asChild><Link to={`${base}/runs/${active.id}`}>Watch it live<ArrowRight className="h-4 w-4" /></Link></Button>
        </div>
      )}

      <div>
        {tab === 'results' && <ResultsTab rows={results.data} loading={results.isPending && Boolean(sprint)} sprint={sprint} base={base} />}
        {tab === 'development' && <DevelopmentTab team={teamId} sprint={sprint} rows={results.data} sprintInfo={sprints.find((s) => s.id === sprint)} base={base} canRun={!busy && ready && Boolean(sprint) && !active} onSnapshot={() => start('snapshot')} />}
        {tab === 'runs' && <RunsTab runs={runs.data} loading={runs.isPending && Boolean(sprint)} base={base} onRerun={rerun} onReport={report} busy={busy} />}
        {tab === 'reviews' && <ReviewsTab team={code} />}
        {tab === 'setup' && <SetupTab loading={readiness.isPending || tracking.isPending} tracking={tracking.data} readiness={readiness.data} runs={runs.data} base={base} membersPath={`/teams/${teamId}/members`} />}
      </div>
    </div>
  )
}
