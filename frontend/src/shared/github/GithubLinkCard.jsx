import { useEffect, useState } from 'react'
import PropTypes from 'prop-types'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { CheckCircle2, ExternalLink, Lock, RefreshCw, Unlink } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import Badge from '@/shared/components/Badge.jsx'
import { showToast } from '../utils/toast.jsx'
import RepositoryForm from '../pages/teams/RepositoryForm.jsx'
import GithubIcon from './GithubIcon.jsx'
import { githubKeys, githubService, MEMBER_STATE } from './githubService.js'

const REASONS = {
  github_account_taken: 'That GitHub account is already linked to another person.',
  leader_must_link_first: 'The team leader has to link the repository first.',
}

function Step({ number, done, title, children }) {
  return (
    <li className="flex gap-3">
      <span className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${done ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300' : 'bg-muted text-muted-foreground'}`}>
        {done ? <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> : number}
      </span>
      <div className="min-w-0 flex-1 space-y-2">
        <p className="text-sm font-medium text-foreground">{title}</p>
        {children}
      </div>
    </li>
  )
}
Step.propTypes = { number: PropTypes.number, done: PropTypes.bool, title: PropTypes.string, children: PropTypes.node }

function Members({ members, canLink, onRefresh, refreshing }) {
  return (
    <div className="overflow-hidden rounded-lg border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-xs text-muted-foreground">
          <tr><th className="p-2 text-left font-medium">Member</th><th className="p-2 text-left font-medium">GitHub account</th><th className="p-2 text-left font-medium">Access to the repository</th></tr>
        </thead>
        <tbody>
          {members.map((m) => {
            const s = MEMBER_STATE[m.state] || MEMBER_STATE.not_connected
            return (
              <tr key={m.user_id} className="border-t">
                <td className="p-2">{m.name}{m.is_leader && <span className="ml-2 text-xs text-muted-foreground">leader</span>}</td>
                <td className="p-2 font-mono text-xs">{m.login ? `@${m.login}` : <span className="font-sans text-muted-foreground">-</span>}</td>
                <td className="p-2"><Badge tone={s.tone} title={s.help}>{s.label}</Badge></td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {canLink && (
        <div className="flex items-center justify-between border-t bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
          <span>Access is read from GitHub. Press refresh after adding a collaborator.</span>
          <Button size="sm" variant="ghost" onClick={onRefresh} disabled={refreshing}><RefreshCw className="h-3.5 w-3.5" /> Refresh access</Button>
        </div>
      )}
    </div>
  )
}
Members.propTypes = { members: PropTypes.array, canLink: PropTypes.bool, onRefresh: PropTypes.func, refreshing: PropTypes.bool }

/**
 * The team's GitHub link, as a short checklist.
 *  1. The leader (or a lecturer) installs the GitHub App on the repository.   2. They pick the repository.
 *  3. Every member connects their own GitHub account from here. GitHub says whose it is and what it may do.
 * Without the GitHub App set up on the server, the repository can still be typed in (unverified) as before.
 */
export default function GithubLinkCard({ team, repoUrl, canEditRepo }) {
  const qc = useQueryClient()
  const [params, setParams] = useSearchParams()
  const [pick, setPick] = useState('')
  const config = useQuery({ queryKey: githubKeys.config, queryFn: githubService.config })
  const state = useQuery({ queryKey: githubKeys.team(team), queryFn: () => githubService.team(team), enabled: Boolean(config.data?.configured) })
  const mine = state.data?.members?.[0]
  const linked = Boolean(state.data?.repo)
  const repos = useQuery({ queryKey: githubKeys.repos(team), queryFn: () => githubService.repos(team), enabled: Boolean(state.data?.can_link) && !linked })

  useEffect(() => {
    const g = params.get('github')
    if (!g) return
    if (g === 'installed') showToast.success('GitHub App installed. Now choose the repository.')
    else if (g === 'connected') showToast.success('Your GitHub account is connected.')
    else showToast.error(REASONS[params.get('reason')] || 'GitHub could not be linked. Try again.')
    qc.invalidateQueries({ queryKey: ['github'] })
    const next = new URLSearchParams(params)
    next.delete('github')
    next.delete('reason')
    setParams(next, { replace: true })
  }, [params, setParams, qc])

  const go = useMutation({ mutationFn: (fn) => fn(), onSuccess: (r) => { if (r?.url) window.location.assign(r.url) } })
  const done = useMutation({
    mutationFn: (fn) => fn(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['github'] }),
    onError: (e) => showToast.error(e.message || 'That did not work.'),
  })

  if (config.isPending) return <Card className="p-4 text-sm text-muted-foreground">Loading GitHub...</Card>
  if (!config.data?.configured) {
    return (
      <div className="grid gap-2">
        <RepositoryForm team={team} repoUrl={repoUrl} canEdit={canEditRepo} />
        <p className="text-xs text-muted-foreground">GitHub linking is not set up on this server, so the address is typed and not checked.</p>
      </div>
    )
  }
  if (state.isPending) return <Card className="p-4 text-sm text-muted-foreground">Loading GitHub...</Card>
  if (state.isError) return <Card className="p-4 text-sm text-destructive">{state.error.message}</Card>
  const s = state.data

  return (
    <Card className="p-5">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-foreground text-background"><GithubIcon className="h-5 w-5" /></span>
          <div>
            <p className="text-sm font-semibold text-foreground">GitHub</p>
            {linked ? (
              <a href={`https://github.com/${s.repo}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm text-primary hover:underline">{s.repo}<ExternalLink className="h-3 w-3" aria-hidden="true" /></a>
            ) : <p className="text-sm text-muted-foreground">No repository linked yet</p>}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {linked && <Badge tone="success"><Lock className="h-3 w-3" />Verified by GitHub</Badge>}
          {linked && s.can_link && <Button size="sm" variant="ghost" onClick={() => done.mutate(() => githubService.unlink(team))}><Unlink className="h-3.5 w-3.5" /> Unlink</Button>}
        </div>
      </div>

      <ol className="grid gap-4">
        <Step number={1} done={linked || Boolean(repos.data)} title="Install the GitHub App on the repository">
          {s.can_link ? (
            linked ? <p className="text-sm text-muted-foreground">Installed.</p> : (
              <>
                <p className="text-sm text-muted-foreground">GitHub asks you to choose which repository the app may read. Choose only the team's repository.</p>
                <Button size="sm" onClick={() => go.mutate(() => githubService.install(team, `/teams/${team}/members`))} disabled={go.isPending}>Install on GitHub</Button>
              </>
            )
          ) : <p className="text-sm text-muted-foreground">The team leader does this.</p>}
        </Step>
        <Step number={2} done={linked} title="Choose the team's repository">
          {s.can_link && !linked && (repos.data?.length ? (
            <div className="flex flex-wrap items-center gap-2">
              <select className="h-9 min-w-56 rounded-md border bg-background px-2 text-sm" value={pick} onChange={(e) => setPick(e.target.value)} aria-label="Repository">
                <option value="">Select a repository</option>
                {repos.data.map((r) => <option key={r.id} value={r.full_name}>{r.full_name}{r.private ? ' (private)' : ''}</option>)}
              </select>
              <Button size="sm" disabled={!pick || done.isPending} onClick={() => done.mutate(() => githubService.chooseRepo(team, pick))}>Use this repository</Button>
            </div>
          ) : <p className="text-sm text-muted-foreground">{repos.isPending ? 'Waiting for step 1.' : 'The app can see no repository yet.'}</p>)}
          {linked && <p className="text-sm text-muted-foreground">Linked. Members can now connect their accounts.</p>}
          {!s.can_link && !linked && <p className="text-sm text-muted-foreground">The team leader does this first.</p>}
        </Step>
        <Step number={3} done={s.members.length > 0 && s.members.every((m) => m.state === 'ready')} title="Each member connects their GitHub account">
          {!linked ? <p className="text-sm text-muted-foreground">Available after the repository is linked.</p> : (
            <>
              {mine && !s.can_link && (
                <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-muted/30 p-3">
                  <div className="text-sm">
                    {mine.login ? <>Connected as <span className="font-mono">@{mine.login}</span></> : 'You have not connected your GitHub account.'}
                    <p className="text-xs text-muted-foreground">{(MEMBER_STATE[mine.state] || MEMBER_STATE.not_connected).help}</p>
                  </div>
                  {mine.login ? (
                    <Button size="sm" variant="outline" onClick={() => done.mutate(() => githubService.disconnect())}>Disconnect</Button>
                  ) : (
                    <Button size="sm" onClick={() => go.mutate(() => githubService.connect(team, `/teams/${team}/members`))} disabled={go.isPending}><GithubIcon className="h-4 w-4" /> Connect GitHub</Button>
                  )}
                </div>
              )}
              <Members members={s.members} canLink={s.can_link} onRefresh={() => done.mutate(() => githubService.refresh(team))} refreshing={done.isPending} />
            </>
          )}
        </Step>
      </ol>
    </Card>
  )
}
GithubLinkCard.propTypes = { team: PropTypes.string.isRequired, repoUrl: PropTypes.string, canEditRepo: PropTypes.bool }
