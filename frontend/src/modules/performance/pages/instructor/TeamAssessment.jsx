import { useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Activity, AlertTriangle, ArrowRight, Flag, Play, RefreshCw, Settings2, Trash2, TrendingUp, Users, Workflow } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import PageHeader from '@/shared/components/PageHeader.jsx'
import { useTeam } from '@/shared/hooks/useTeams.js'
import { useConfirm } from '@/shared/utils/useConfirm.js'
import { showToast } from '@/shared/utils/toast.jsx'
import { assessmentApi, assessmentKeys } from '../../assessment/assessmentApi.js'
import { when } from '../../assessment/format.js'
import { Avatar, RunPill } from '../../assessment/visuals.jsx'
import { Skel, StatRowSkeleton, TableSkeleton } from '../../assessment/Reveal.jsx'
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
  const qc = useQueryClient()
  const confirm = useConfirm()
  const team = useTeam(teamId)
  const meta = useQuery({ queryKey: assessmentKeys.meta, queryFn: assessmentApi.meta, staleTime: Infinity })
  const code = team.data?.code || teamId
  const tab = TABS.some((t) => t.id === tabParam) ? tabParam : 'results'

  const overview = useQuery({
    queryKey: assessmentKeys.overview(teamId, ''),
    queryFn: () => assessmentApi.overview(teamId),
    staleTime: 30000,
    retry: false,
    refetchInterval: (query) => {
      const activeRun = query.state.data?.run_state?.active_run
      return activeRun ? 4000 : false
    },
  })

  const sprints = useMemo(() => overview.data?.sprints ?? [], [overview.data?.sprints])
  const sprint = overview.data?.sprint || sprints[sprints.length - 1]?.id || ''

  const runs = useQuery({
    queryKey: assessmentKeys.runs(teamId, ""),
    queryFn: () => assessmentApi.runs(teamId),
    enabled: Boolean(sprint),
    staleTime: 15000,
    refetchInterval: (query) => {
      const data = query.state.data
      const runList = data?.runs || (Array.isArray(data) ? data : [])
      const hasActive = runList.some((r) => ACTIVE.includes(r.status))
      return hasActive ? 3000 : false
    },
  })

  const development = useQuery({
    queryKey: assessmentKeys.development(teamId, sprint),
    queryFn: () => assessmentApi.development(teamId, sprint),
    enabled: Boolean(sprint) && tab === 'development',
    staleTime: 30000,
    refetchInterval: false,
  })

  const setup = useQuery({
    queryKey: assessmentKeys.setup(teamId),
    queryFn: () => assessmentApi.setup(teamId),
    staleTime: 60000,
    refetchInterval: false,
  })

  const [busy, setBusy] = useState(false)
  const base = `/teams/${teamId}/performance`

  const openTab = (id) => navigate(`${base}/team/${id}`)

  const runPayload = runs.data?.runs ? runs.data : { runs: runs.data || [], analysis: null }
  const runRows = runPayload.runs
  const latest = overview.data?.run_state?.latest_run || runRows[0]
  const active = overview.data?.run_state?.active_run || runRows.find((r) => ACTIVE.includes(r.status))
  const ready = overview.data?.run_state?.ready !== false
  // The sprints a final assessment will cover: those with no finished or active final run, oldest first (the server decides the same way).
  const pendingSprints = sprints.filter((x) => !runRows.some((r) => r.sprint_id === x.id && r.mode === 'final' && ['succeeded', 'queued', 'running', 'waiting_human'].includes(r.status)))
  const refresh = () => qc.invalidateQueries({ queryKey: ['assessment', teamId] })

  const teamStudents = useMemo(() => {
    const list = []
    const seen = new Set()

    // 1. From overview roster (provided by backend platform agent_roster or team config)
    if (overview.data?.roster?.length) {
      for (const r of overview.data.roster) {
        const sid = r.student_id || r.user_id || r.id
        if (sid && !seen.has(String(sid))) {
          seen.add(String(sid))
          const name = (r.names && r.names[0]) || r.name || (r.logins && r.logins[0]) || String(sid)
          list.push({
            id: String(sid),
            name,
            picture: r.picture || null,
          })
        }
      }
    }

    // 2. From team members (from teamService getTeam)
    if (team.data?.members?.length) {
      for (const m of team.data.members) {
        const sid = m.user_id || m.student_id || m.id
        const role = String(m.role || '').toLowerCase()
        if (sid && !seen.has(String(sid)) && role !== 'lecturer') {
          seen.add(String(sid))
          list.push({
            id: String(sid),
            name: m.name || m.github_username || String(sid),
            picture: m.picture || null,
          })
        }
      }
    }

    // 3. From setup members
    if (setup.data?.members?.length) {
      for (const m of setup.data.members) {
        const sid = m.user_id || m.student_id || m.id
        const role = String(m.role || '').toLowerCase()
        if (sid && !seen.has(String(sid)) && role !== 'lecturer') {
          seen.add(String(sid))
          list.push({
            id: String(sid),
            name: m.name || m.login || String(sid),
            picture: m.picture || null,
          })
        }
      }
    }

    // 4. From overview rows (if previous run results exist)
    if (overview.data?.rows?.length) {
      for (const r of overview.data.rows) {
        const sid = r.student_id || r.id
        if (sid && !seen.has(String(sid))) {
          seen.add(String(sid))
          list.push({
            id: String(sid),
            name: r.student?.name || r.name || String(sid),
            picture: r.student?.picture || r.picture || null,
          })
        }
      }
    }

    return list
  }, [overview.data, team.data, setup.data])

  const [selectDialogOpen, setSelectDialogOpen] = useState(false)
  const [selectedStudents, setSelectedStudents] = useState([])

  const openStudentSelect = () => {
    setSelectedStudents(teamStudents.map((s) => s.id))
    setSelectDialogOpen(true)
  }

  const toggleStudent = (id) => {
    setSelectedStudents((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]
    )
  }

  const toggleSelectAll = () => {
    if (selectedStudents.length === teamStudents.length) {
      setSelectedStudents([])
    } else {
      setSelectedStudents(teamStudents.map((s) => s.id))
    }
  }

  const start = async (mode, students) => {
    setBusy(true)
    try {
      const r = await assessmentApi.startRun(teamId, sprint, mode, students)
      if (mode === 'final') {
        const count = students?.length ?? teamStudents.length
        showToast.info('Agent began evaluation', {
          description: (
            <div className="mt-1 space-y-1">
              <p className="text-xs text-muted-foreground">
                Evaluating {count} student{count !== 1 ? 's' : ''} for sprint {r.sprint_id || sprint}.
              </p>
              {r.also_queued?.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  {r.also_queued.length} other sprint{r.also_queued.length !== 1 ? 's' : ''} ({r.also_queued.map((q) => q.sprint_id).join(', ')}) {r.also_queued.length !== 1 ? 'have' : 'has'} no evaluation yet and will follow.
                </p>
              )}
              <button
                type="button"
                onClick={() => navigate(`${base}/runs/${r.run_id}`)}
                className="inline-flex items-center gap-1 font-medium text-xs text-primary hover:underline cursor-pointer"
              >
                To see the logs, click here &rarr;
              </button>
            </div>
          ),
          action: {
            label: 'See live logs',
            onClick: () => navigate(`${base}/runs/${r.run_id}`),
          },
          duration: 12000,
        })
      } else {
        showToast.success('Snapshot started')
      }
      refresh()
      return r
    } catch (e) {
      showToast.error(e.message)
    } finally {
      setBusy(false)
    }
  }

  const handleConfirmStartAssessment = async () => {
    setSelectDialogOpen(false)
    await start('final', selectedStudents)
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

  const handleClearData = async () => {
    const ok = await confirm({
      title: `Clear evaluation data?`,
      description: `This will permanently delete all assessment runs, factor scores, quizzes, snapshots, and reviews for every sprint of this team. You can start a fresh evaluation afterwards.`,
      confirmText: 'Clear data',
      destructive: true,
    })
    if (!ok) return
    setBusy(true)
    try {
      await assessmentApi.clearEvaluation(teamId)
      showToast.success('Evaluation data cleared')
      refresh()
      qc.invalidateQueries({ queryKey: ['assessment', teamId] })
    } catch (e) {
      showToast.error(e.message)
    } finally {
      setBusy(false)
    }
  }

  const report = async (id) => {
    const text = await assessmentApi.runReport(id)
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
            <Button variant="outline" disabled={busy || !ready || !sprint || Boolean(active)} onClick={() => start('snapshot')} title="Where the team is right now. Marks are provisional."><Activity className="h-4 w-4" />Snapshot</Button>
            <Button disabled={busy || !ready || !sprint || Boolean(active)} onClick={openStudentSelect} title="Select students and start the assessment of every sprint that has not been evaluated yet."><Play className="h-4 w-4" />Start assessment</Button>
            {latest && !active && <Button variant="ghost" disabled={busy} onClick={() => rerun(latest)}><RefreshCw className="h-4 w-4" />Re-evaluate</Button>}
            <Button variant="ghost" className="text-destructive hover:bg-destructive/10 hover:text-destructive" disabled={busy || Boolean(active)} onClick={handleClearData} title="Clear the evaluation data of every sprint"><Trash2 className="h-4 w-4" />Clear data</Button>
          </>
        }
      />


      <Dialog open={selectDialogOpen} onOpenChange={setSelectDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Start Assessment</DialogTitle>
            <DialogDescription>
              Which student(s) would you like to evaluate? {pendingSprints.length ? <>It starts with <span className="font-semibold text-foreground">{pendingSprints[0].id}</span>{pendingSprints.length > 1 ? <> and goes on to {pendingSprints.slice(1).map((x) => x.id).join(', ')}</> : null}, one after another.</> : <>Every sprint has been evaluated; this evaluates {sprint} again.</>}
            </DialogDescription>
          </DialogHeader>

          <div className="py-2">
            <div className="flex items-center justify-between border-b pb-2 mb-3 px-1">
              <span className="text-xs font-medium text-muted-foreground">
                {selectedStudents.length} of {teamStudents.length} selected
              </span>
              <button
                type="button"
                onClick={toggleSelectAll}
                className="text-xs font-medium text-primary hover:underline cursor-pointer"
              >
                {selectedStudents.length === teamStudents.length ? 'Deselect all' : 'Select all'}
              </button>
            </div>

            <div className="max-h-64 overflow-y-auto space-y-1.5 pr-1">
              {teamStudents.map((s) => {
                const isChecked = selectedStudents.includes(s.id)
                return (
                  <label
                    key={s.id}
                    className="flex items-center gap-3 rounded-lg border p-2.5 transition-colors hover:bg-accent/50 cursor-pointer select-none"
                  >
                    <Checkbox
                      checked={isChecked}
                      onCheckedChange={() => toggleStudent(s.id)}
                    />
                    <Avatar name={s.name} picture={s.picture} size={32} />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-foreground">{s.name}</p>
                      <p className="truncate text-xs text-muted-foreground">{s.id}</p>
                    </div>
                  </label>
                )
              })}
              {teamStudents.length === 0 && (
                <p className="py-4 text-center text-xs text-muted-foreground">
                  No students found in the team roster.
                </p>
              )}
            </div>
          </div>

          <DialogFooter className="gap-2 sm:gap-0">
            <Button variant="ghost" onClick={() => setSelectDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              disabled={busy || selectedStudents.length === 0}
              onClick={handleConfirmStartAssessment}
            >
              <Play className="h-4 w-4" />
              Evaluate ({selectedStudents.length})
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {!sprints.length && (
        <div className="rounded-xl border border-dashed p-5 text-sm">
          <p className="font-medium">No sprint to assess yet</p>
          <p className="mt-1 text-muted-foreground">The agent reads one sprint at a time. Sprints come from the team's Scrum board and appear here once the board has them. Setup shows what is still missing.</p>
          <Button size="sm" className="mt-3" onClick={() => openTab('setup')}>Open Setup</Button>
        </div>
      )}
      {sprints.length > 0 && !ready && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm dark:border-amber-900 dark:bg-amber-950/30">
          <div className="flex gap-3"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" aria-hidden="true" /><div><p className="font-medium text-amber-900 dark:text-amber-200">This team cannot be assessed yet</p>          <ul className="mt-1 list-disc pl-4 text-amber-800 dark:text-amber-300">{(overview.data?.run_state?.blockers || []).map((b) => <li key={b}>{b}</li>)}</ul></div></div>
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
        {tab === 'results' && <ResultsTab overview={overview.data ? { ...overview.data, meta: meta.data } : overview.data} loading={overview.isPending && Boolean(sprint)} base={base} />}
        {tab === 'development' && <DevelopmentTab team={teamId} development={development.data} loading={development.isPending && Boolean(sprint)} sprintInfo={sprints.find((s) => s.id === sprint)} base={base} canRun={!busy && ready && Boolean(sprint) && !active} onSnapshot={() => start('snapshot')} />}
        {tab === 'runs' && <RunsTab runs={runRows} analysis={runPayload.analysis} loading={runs.isPending && Boolean(sprint)} base={base} onRerun={rerun} onReport={report} busy={busy} />}
        {tab === 'reviews' && <ReviewsTab team={code} students={teamStudents} />}
        {tab === 'setup' && <SetupTab setup={setup.data} loading={setup.isPending} base={base} membersPath={`/teams/${teamId}/members`} />}
      </div>
    </div>
  )
}
