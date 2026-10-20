import { useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { createPortal } from 'react-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { ArrowLeft, Check, Loader2, RefreshCw, ShieldAlert, ShieldCheck, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import SelviaLogo from '../components/SelviaLogo.jsx'
import { showToast } from '../utils/toast.jsx'
import GithubIcon from './GithubIcon.jsx'
import { gateCopy, reasonText, STEPS, stepStates } from './gateCopy.js'
import { githubKeys, githubService } from './githubService.js'

const TONE = {
  action: { ring: 'from-indigo-500 to-violet-500', soft: 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950/50 dark:text-indigo-300', Icon: ShieldCheck },
  wait: { ring: 'from-sky-400 to-cyan-400', soft: 'bg-sky-50 text-sky-700 dark:bg-sky-950/50 dark:text-sky-300', Icon: ShieldCheck },
  reject: { ring: 'from-rose-500 to-orange-400', soft: 'bg-rose-50 text-rose-700 dark:bg-rose-950/50 dark:text-rose-300', Icon: ShieldAlert },
}

// Drawn on the page body, not where the gate sits in the tree: inside the dashboard shell a transformed or clipped ancestor would shrink or hide a fixed full-screen page.
function Backdrop({ children }) {
  return createPortal(
    <div className="fixed inset-0 z-[100] overflow-y-auto bg-background">
      <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
        <div className="absolute -left-24 -top-24 h-96 w-96 rounded-full bg-indigo-400/25 blur-3xl" />
        <div className="absolute -right-24 top-1/3 h-96 w-96 rounded-full bg-violet-400/20 blur-3xl" />
        <div className="absolute -bottom-32 left-1/3 h-96 w-96 rounded-full bg-sky-400/20 blur-3xl" />
        <div className="absolute inset-0 opacity-[0.35] [background-image:radial-gradient(var(--border)_1px,transparent_1px)] [background-size:22px_22px]" />
      </div>
      <div className="relative mx-auto flex min-h-full w-full max-w-4xl flex-col px-4 py-8 sm:px-6">{children}</div>
    </div>,
    document.body,
  )
}
Backdrop.propTypes = { children: PropTypes.node }

function Header({ team }) {
  return (
    <header className="mb-8 flex items-center justify-between gap-3">
      <SelviaLogo />
      {team && <span className="rounded-full border bg-card/80 px-3 py-1 text-xs font-medium text-muted-foreground backdrop-blur">{team}</span>}
    </header>
  )
}
Header.propTypes = { team: PropTypes.string }

function Checking({ team }) {
  return (
    <Backdrop>
      <Header team={team} />
      <div className="flex flex-1 flex-col items-center justify-center gap-5 pb-24 text-center" role="status" aria-live="polite">
        <div className="relative">
          <span className="absolute inset-0 animate-ping rounded-3xl bg-indigo-400/30" />
          <span className="relative flex h-20 w-20 items-center justify-center rounded-3xl bg-foreground text-background shadow-xl"><GithubIcon className="h-10 w-10" /></span>
        </div>
        <div>
          <p className="text-lg font-semibold text-foreground">Checking your access</p>
          <p className="mt-1 text-sm text-muted-foreground">Asking GitHub whether your account can work in this team&apos;s repository.</p>
        </div>
      </div>
    </Backdrop>
  )
}
Checking.propTypes = { team: PropTypes.string }

function Rail({ gate }) {
  const states = stepStates(gate)
  return (
    <ol className="relative grid gap-0">
      {STEPS.map((s, i) => {
        const st = states[i]
        return (
          <li key={s.id} className="relative flex gap-3 pb-7 last:pb-0">
            {i < STEPS.length - 1 && <span className={`absolute left-[15px] top-8 h-[calc(100%-2rem)] w-0.5 ${st === 'done' ? 'bg-emerald-400' : 'bg-border'}`} aria-hidden="true" />}
            <span className={`relative z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border-2 text-xs font-semibold transition-colors ${
              st === 'done' ? 'border-emerald-500 bg-emerald-500 text-white' : st === 'failed' ? 'border-rose-500 bg-rose-500 text-white' : st === 'current' ? 'border-indigo-500 bg-background text-indigo-600 shadow-[0_0_0_4px_rgba(99,102,241,0.18)]' : 'border-border bg-background text-muted-foreground'}`}>
              {st === 'done' ? <Check className="h-4 w-4" aria-hidden="true" /> : st === 'failed' ? <X className="h-4 w-4" aria-hidden="true" /> : i + 1}
            </span>
            <span className="min-w-0 pt-0.5">
              <span className={`block text-sm font-medium ${st === 'waiting' ? 'text-muted-foreground' : 'text-foreground'}`}>{s.label}</span>
              <span className="block text-xs text-muted-foreground">{s.who}</span>
            </span>
          </li>
        )
      })}
    </ol>
  )
}
Rail.propTypes = { gate: PropTypes.object }

function RepoPicker({ teamId, gate, onDone }) {
  const [pick, setPick] = useState('')
  const repos = useQuery({ queryKey: githubKeys.repos(teamId), queryFn: () => githubService.repos(teamId), enabled: gate.installed })
  const install = useMutation({ mutationFn: () => githubService.install(teamId), onSuccess: (r) => window.location.assign(r.url), onError: (e) => showToast.error(e.message) })
  const choose = useMutation({ mutationFn: () => githubService.chooseRepo(teamId, pick), onSuccess: onDone, onError: (e) => showToast.error(e.message) })
  if (!gate.installed) {
    return (
      <div className="space-y-3">
        <p className="text-sm text-muted-foreground">GitHub will ask which repository the app may read. Choose only your team&apos;s repository.</p>
        <Button size="lg" onClick={() => install.mutate()} disabled={install.isPending}>{install.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <GithubIcon className="h-4 w-4" />}Install on GitHub</Button>
      </div>
    )
  }
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">The app is installed{gate.installed_by ? ` on @${gate.installed_by}` : ''}. Now choose the repository your team works in.</p>
      {repos.isPending ? <p className="text-sm text-muted-foreground">Looking for repositories...</p> : !repos.data?.length ? (
        <p className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900 dark:bg-amber-950/30 dark:text-amber-200">The app can see no repository. Add one in the app&apos;s settings on GitHub, then check again.</p>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          <select className="h-10 min-w-60 rounded-md border bg-background px-3 text-sm" value={pick} onChange={(e) => setPick(e.target.value)} aria-label="Repository">
            <option value="">Select a repository</option>
            {repos.data.map((r) => <option key={r.id} value={r.full_name}>{r.full_name}{r.private ? ' (private)' : ''}</option>)}
          </select>
          <Button size="lg" disabled={!pick || choose.isPending} onClick={() => choose.mutate()}>Use this repository</Button>
        </div>
      )}
    </div>
  )
}
RepoPicker.propTypes = { teamId: PropTypes.string, gate: PropTypes.object, onDone: PropTypes.func }

/**
 * The page in front of a team. A student reaches the team's dashboard only after three things are true, checked live against GitHub every time the page loads:
 * the leader has linked the repository, the student has signed in with a GitHub account, and that account is a collaborator with write access.
 * Anything else shows this page and says exactly what to do. Lecturers and administrators do not pass through it.
 */
export default function TeamAccessGate({ teamId, children }) {
  const qc = useQueryClient()
  const [params, setParams] = useSearchParams()
  const gate = useQuery({
    queryKey: githubKeys.gate(teamId), queryFn: () => githubService.gate(teamId),
    staleTime: 0, gcTime: 0, refetchOnMount: 'always', refetchOnWindowFocus: true, refetchInterval: 5 * 60 * 1000, retry: 1,
  })
  const connect = useMutation({ mutationFn: (choose) => githubService.connect(teamId, `/teams/${teamId}`, choose), onSuccess: (r) => window.location.assign(r.url), onError: (e) => showToast.error(e.message) })
  const recheck = () => qc.invalidateQueries({ queryKey: githubKeys.gate(teamId) })

  useEffect(() => {
    const g = params.get('github')
    if (!g) return
    if (g === 'installed') showToast.success('GitHub App installed. Now choose the repository.')
    else if (g === 'connected') showToast.success('Your GitHub account is connected.')
    else showToast.error(reasonText(params.get('reason')))
    const next = new URLSearchParams(params)
    ;['github', 'reason'].forEach((k) => next.delete(k))
    setParams(next, { replace: true })
    qc.invalidateQueries({ queryKey: ['github'] })
  }, [params, setParams, qc])

  if (gate.isPending) return <Checking team={teamId} />
  if (gate.isError) {
    return (
      <Backdrop>
        <Header team={teamId} />
        <div className="flex flex-1 flex-col items-center justify-center gap-4 pb-24 text-center">
          <ShieldAlert className="h-10 w-10 text-rose-500" aria-hidden="true" />
          <p className="text-lg font-semibold">The access check did not finish</p>
          <p className="max-w-md text-sm text-muted-foreground">{gate.error?.message || 'Something went wrong while checking.'}</p>
          <Button onClick={recheck}><RefreshCw className="h-4 w-4" />Try again</Button>
        </div>
      </Backdrop>
    )
  }
  const g = gate.data
  if (g.state === 'ok') return children

  const copy = gateCopy(g, g.team_name)
  const tone = TONE[copy.tone] || TONE.wait
  const busy = gate.isFetching
  return (
    <Backdrop>
      <Header team={g.team_name || teamId} />
      <div className="flex flex-1 items-center pb-16">
        <div className="grid w-full overflow-hidden rounded-3xl border bg-card/85 shadow-2xl backdrop-blur md:grid-cols-[260px_1fr]">
          <aside className="border-b bg-muted/40 p-6 md:border-b-0 md:border-r">
            <p className="mb-5 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Before you enter</p>
            <Rail gate={g} />
          </aside>
          <section className="flex flex-col gap-6 p-6 sm:p-9">
            <div className="flex items-start gap-4">
              <span className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br ${tone.ring} text-white shadow-lg`}>
                {copy.tone === 'reject' ? <tone.Icon className="h-7 w-7" aria-hidden="true" /> : <GithubIcon className="h-7 w-7" />}
              </span>
              <div className="min-w-0">
                <h1 className="text-xl font-semibold leading-snug tracking-tight text-foreground sm:text-2xl">{copy.title}</h1>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{copy.body}</p>
              </div>
            </div>

            {copy.primary === 'repo' && <RepoPicker teamId={teamId} gate={g} onDone={recheck} />}
            {copy.primary === 'connect' && (
              <div className="space-y-3">
                <Button size="lg" className="w-fit" onClick={() => connect.mutate(false)} disabled={connect.isPending}>{connect.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <GithubIcon className="h-4 w-4" />}Continue with GitHub</Button>
                <p className="text-xs text-muted-foreground">GitHub opens, you approve, and you come straight back here.</p>
              </div>
            )}
            {(copy.primary === 'recheck' || copy.secondary) && (
              <div className="flex flex-wrap items-center gap-3">
                {copy.primary === 'recheck' && <Button size="lg" onClick={recheck} disabled={busy}><RefreshCw className={`h-4 w-4 ${busy ? 'animate-spin' : ''}`} />Check again</Button>}
                {copy.secondary === 'switch' && <Button size="lg" variant="outline" onClick={() => connect.mutate(true)} disabled={connect.isPending}><GithubIcon className="h-4 w-4" />Use a different GitHub account</Button>}
              </div>
            )}
            {g.repo && <p className={`w-fit rounded-lg px-3 py-1.5 font-mono text-xs ${tone.soft}`}>{g.repo}</p>}
            <div className="mt-auto flex flex-wrap items-center justify-between gap-3 border-t pt-4 text-xs text-muted-foreground">
              <span>This check runs again every time you open the team, so access that is taken away on GitHub closes the door here too.</span>
              <Link to="/home" className="inline-flex items-center gap-1 font-medium text-foreground hover:underline"><ArrowLeft className="h-3.5 w-3.5" />My teams</Link>
            </div>
          </section>
        </div>
      </div>
    </Backdrop>
  )
}
TeamAccessGate.propTypes = { teamId: PropTypes.string.isRequired, children: PropTypes.node }
