import { CircleAlert, CircleCheck, GitCommitHorizontal } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import Badge from '@/shared/components/Badge.jsx'
import { MockBadge } from './common.jsx'
import {
  CATEGORIES,
  STAGE_LABEL,
  STAGE_ORDER,
  categoryState,
  checkoutLabel,
  coverageTone,
  formatWhen,
  llmFacts,
  problemRuns,
  scanTypeLabel,
  shortSha,
  stageTone,
  toolStatusLabel,
  toolTone,
  triggerLabel,
} from '../lib/format.js'

function Fact({ label, children }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs font-medium text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 break-words text-sm text-foreground">{children}</dd>
    </div>
  )
}

// Where the run came from, what ran it, and with which versions and settings.
export function ProvenanceCard({ overview }) {
  const m = overview.manifest ?? {}
  const checkout = m.checkout ?? null
  const sha = shortSha(m.commit_sha)
  return (
    <Card data-slot="provenance" className="gap-4 p-5">
      <div>
        <h2 className="text-sm font-semibold">Source and provenance</h2>
        <p className="text-xs text-muted-foreground">Where this run came from and exactly how it was produced.</p>
      </div>
      <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Fact label="Repository">{m.repo ?? 'Not recorded'}</Fact>
        <Fact label="Commit">
          {sha ? (
            <span className="inline-flex items-center gap-1 font-mono">
              <GitCommitHorizontal className="h-3.5 w-3.5" />
              {sha}
            </span>
          ) : (
            'Not recorded (the scan was not tied to one commit)'
          )}
        </Fact>
        <Fact label="Trigger">{triggerLabel(m.trigger)}</Fact>
        <Fact label="Scan type">{scanTypeLabel(m.scan_type)}</Fact>
        <Fact label="Started">{formatWhen(m.started_at)}</Fact>
        <Fact label="Finished">{formatWhen(m.finished_at)}</Fact>
        <Fact label="How the code was made available">{checkoutLabel(checkout)}</Fact>
        <Fact label="Read-only">{checkout ? (checkout.read_only ? 'Yes: the tools only read the code' : 'No') : 'Not recorded'}</Fact>
        <Fact label="Student code executed">{checkout ? (checkout.code_executed ? 'Yes' : 'No: nothing from the repository was run') : 'Not recorded'}</Fact>
        {overview.team_repo_url && <Fact label="Team repository (team page)">{overview.team_repo_url}</Fact>}
      </dl>

      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Tools and versions</h3>
        <div className="flex flex-wrap gap-2">
          {(overview.scan.tool_runs ?? []).map((r) => (
            <Badge key={r.tool} tone="neutral">
              {r.tool} {r.tool_version ?? 'version not recorded'}
            </Badge>
          ))}
          {!(overview.scan.tool_runs ?? []).length && <span className="text-xs text-muted-foreground">No tool ran.</span>}
        </div>
      </div>

      <div>
        <h3 className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Model and settings
          {overview.llm?.tutor_is_mock && <MockBadge>Tutor is a mock</MockBadge>}
        </h3>
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {llmFacts(overview.llm).map(([label, value]) => (
            <Fact key={label} label={label}>
              {String(value)}
            </Fact>
          ))}
        </dl>
      </div>
    </Card>
  )
}

// COMPLETE or INCOMPLETE with the reasons: a run with a failed or skipped check is never presented as a clean result.
export function IncompleteBanner({ run, scan }) {
  const problems = problemRuns(scan?.tool_runs)
  if (run.complete) {
    return (
      <div role="status" data-slot="complete-banner" className="flex items-start gap-2 rounded-lg border border-emerald-300 bg-emerald-50 px-3 py-2 text-sm text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200">
        <CircleCheck className="mt-0.5 h-4 w-4 shrink-0" />
        <span>
          <span className="font-semibold">COMPLETE. </span>All stages ran. Read the limitations before relying on the result.
        </span>
      </div>
    )
  }
  return (
    <div role="alert" data-slot="incomplete-banner" className="rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-foreground">
      <p className="flex items-center gap-2 font-semibold text-destructive">
        <CircleAlert className="h-4 w-4 shrink-0" />
        INCOMPLETE RUN. This is not a clean result.
      </p>
      <ul className="mt-1 list-disc space-y-0.5 pl-6 text-xs">
        {run.incomplete_reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
        {problems.map((r) => (
          <li key={`tool-${r.tool}`}>
            {r.tool} {toolStatusLabel(r.status)}
            {r.reason ? `: ${r.reason}` : ''}
          </li>
        ))}
      </ul>
    </div>
  )
}

export function StageStrip({ stages }) {
  const byName = Object.fromEntries(stages.map((s) => [s.stage, s]))
  return (
    <Card data-slot="stages" className="gap-3 p-5">
      <h2 className="text-sm font-semibold">Stages</h2>
      <ol className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {STAGE_ORDER.map((name) => {
          const s = byName[name]
          return (
            <li key={name} data-stage={name} data-status={s?.status ?? 'not recorded'} className="rounded-lg border border-border p-2.5">
              <p className="text-xs font-medium">{STAGE_LABEL[name]}</p>
              <Badge tone={s ? stageTone(s.status) : 'neutral'} className="mt-1">
                {s?.status ?? 'not recorded'}
              </Badge>
              {s?.detail && <p className="mt-1.5 line-clamp-3 text-[11px] leading-snug text-muted-foreground">{s.detail}</p>}
            </li>
          )
        })}
      </ol>
    </Card>
  )
}

export function ToolRunsTable({ toolRuns }) {
  return (
    <Card data-slot="tool-runs" className="gap-3 p-5">
      <div>
        <h2 className="text-sm font-semibold">Tool runs</h2>
        <p className="text-xs text-muted-foreground">A tool that failed, timed out or was not installed did not check anything: its absence of findings means nothing.</p>
      </div>
      {toolRuns.length ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Tool</TableHead>
              <TableHead>Result</TableHead>
              <TableHead>Version</TableHead>
              <TableHead className="text-right">Seconds</TableHead>
              <TableHead className="text-right">Findings</TableHead>
              <TableHead>Reason</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {toolRuns.map((r) => (
              <TableRow key={r.tool} data-tool={r.tool} data-status={r.status}>
                <TableCell className="font-medium">{r.tool}</TableCell>
                <TableCell>
                  <Badge tone={toolTone(r.status)}>{toolStatusLabel(r.status)}</Badge>
                </TableCell>
                <TableCell className="font-mono text-xs">{r.tool_version ?? 'n/a'}</TableCell>
                <TableCell className="text-right">{r.duration_s ?? 'n/a'}</TableCell>
                <TableCell className="text-right">{['succeeded'].includes(r.status) ? r.findings_count : 'n/a'}</TableCell>
                <TableCell className="max-w-xs text-xs text-muted-foreground">{r.reason || ''}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <p className="text-sm text-muted-foreground">No tool ran in this run.</p>
      )}
    </Card>
  )
}

export function CoverageGrid({ coverage, counts }) {
  return (
    <Card data-slot="coverage" className="gap-3 p-5">
      <div>
        <h2 className="text-sm font-semibold">Coverage by vulnerability type</h2>
        <p className="text-xs text-muted-foreground">How much of each category the tools could check, and what the counts mean given that.</p>
      </div>
      <ul className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
        {CATEGORIES.map(({ id, label }) => {
          const cov = coverage?.[id]
          const row = counts?.[id] ?? {}
          const state = categoryState(cov, row)
          return (
            <li key={id} data-category={id} data-coverage={cov?.level ?? 'NONE'} className="flex flex-col gap-2 rounded-lg border border-border p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold">
                  {id} <span className="font-normal text-muted-foreground">{label}</span>
                </p>
                <Badge tone={coverageTone(cov?.level)}>{cov?.level ?? 'NONE'}</Badge>
              </div>
              <p className="text-[11px] leading-snug text-muted-foreground">{cov?.note ?? 'No coverage information for this category.'}</p>
              <p className={`text-xs font-medium ${state.tone === 'danger' ? 'text-destructive' : state.tone === 'warning' ? 'text-amber-700 dark:text-amber-400' : ''}`}>{state.text}</p>
              <p className="text-[11px] text-muted-foreground">
                {row.confirmed ?? 0} confirmed · {row.dismissed ?? 0} dismissed · {(row.uncertain ?? 0) + (row['not interpreted'] ?? 0)} uncertain or not interpreted
              </p>
            </li>
          )
        })}
      </ul>
    </Card>
  )
}
