import { Link } from 'react-router-dom'
import { Check, ExternalLink, EyeOff, GitCommitHorizontal } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import Badge from '@/shared/components/Badge.jsx'
import { MockBadge } from './common.jsx'
import {
  CATEGORIES,
  LINK_STATUS_NOTE,
  SECRET_LINE_NOTE,
  linkTone,
  probeSummary,
  referenceLabel,
  riskTotal,
  shortSha,
  statusTone,
  whereLabel,
} from '../lib/format.js'

const STATUS_ORDER = ['confirmed', 'dismissed', 'uncertain', 'not interpreted']

// Counts by status of one type: the numbers the tab and the page header show.
export function StatusCounts({ row }) {
  return (
    <div data-slot="status-counts" className="flex flex-wrap gap-2">
      {STATUS_ORDER.filter((s) => s !== 'not interpreted' || row?.[s]).map((status) => (
        <Badge key={status} tone={statusTone(status)} data-status={status}>
          {row?.[status] ?? 0} {status}
        </Badge>
      ))}
    </div>
  )
}

export function FindingRow({ finding: f, to }) {
  return (
    <li data-group={f.group_id} data-status={f.status} className="rounded-lg border border-border bg-card p-3">
      <Link to={to} className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-4">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-foreground">{f.title}</p>
          <p className="truncate text-xs text-muted-foreground">
            <span className="font-mono">{whereLabel(f)}</span> · {f.tool} · {f.rule_id}
            {f.cwe ? ` · ${f.cwe}` : ''}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {f.mine && <Badge tone="primary">mine</Badge>}
          <Badge tone={statusTone(f.status)}>{f.status}</Badge>
          {f.risk_score != null ? (
            <Badge tone="neutral" title="Risk score and rank">
              risk {f.risk_score} · #{f.risk_rank}
            </Badge>
          ) : (
            <Badge tone="warning" title="Not ranked: the risk stage did not run or the finding was dismissed">
              not ranked
            </Badge>
          )}
        </div>
      </Link>
    </li>
  )
}

export function FindingHeader({ finding: f, action }) {
  return (
    <div data-slot="finding-header" className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h2 className="text-lg font-semibold">{f.message ?? f.rule_id}</h2>
        <p className="text-xs text-muted-foreground">
          {f.category} {CATEGORIES.find((c) => c.id === f.category)?.label} · <span className="font-mono">{whereLabel(f)}</span> · {f.tool} · {f.rule_id}
          {f.cwe ? ` · ${f.cwe}` : ''}
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {f.mine && <Badge tone="primary">mine</Badge>}
        <Badge tone={statusTone(f.status)}>{f.status}</Badge>
        {action}
      </div>
    </div>
  )
}

function Section({ title, hint, children, ...props }) {
  return (
    <Card className="gap-3 p-5" {...props}>
      <div>
        <h2 className="text-sm font-semibold">{title}</h2>
        {hint && <p className="text-xs text-muted-foreground">{hint}</p>}
      </div>
      {children}
    </Card>
  )
}

// The code around the finding, already masked by the run. A secret's own line is never shown, so a secret finding says so instead of an empty box.
export function MaskedCode({ finding: f }) {
  if (f.category === 'V4' || f.snippet_note) {
    return (
      <div data-slot="code-hidden" className="flex items-center gap-2 rounded-lg border border-dashed border-border bg-muted/40 p-3 text-xs text-muted-foreground">
        <EyeOff className="h-4 w-4 shrink-0" />
        <span className="font-medium text-foreground">{f.snippet_note ?? SECRET_LINE_NOTE}</span>
        <span>The value is masked everywhere in this tool.</span>
      </div>
    )
  }
  if (!f.snippet) {
    return <p data-slot="code-none" className="text-xs text-muted-foreground">No code snippet for this finding (a dependency, a history entry, or a line the copy no longer has).</p>
  }
  return (
    <pre data-slot="code" className="overflow-x-auto rounded-lg border border-border bg-muted/40 p-3 font-mono text-xs leading-relaxed">
      {f.snippet}
    </pre>
  )
}

export function ScannerVsVerdict({ finding: f, model }) {
  return (
    <Section title="Scanner evidence and the LLM's verdict" hint="Left: what the scanner reported. Right: what the model made of it. The model can be wrong; 'dismissed' is an argument, not proof." data-slot="scanner-vs-verdict">
      <div className="grid gap-4 md:grid-cols-2">
        <div data-slot="scanner" className="space-y-2 rounded-lg border border-border p-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Scanner</h3>
          <dl className="space-y-1 text-sm">
            <div><dt className="inline text-muted-foreground">Tool and rule: </dt><dd className="inline font-mono text-xs">{f.tool} · {f.rule_id}</dd></div>
            <div><dt className="inline text-muted-foreground">CWE: </dt><dd className="inline">{f.cwe ?? 'none given'}</dd></div>
            <div><dt className="inline text-muted-foreground">Tool severity: </dt><dd className="inline">{f.severity_tool ?? 'none given'}</dd></div>
            <div><dt className="inline text-muted-foreground">Where: </dt><dd className="inline font-mono text-xs">{whereLabel(f)}</dd></div>
            {f.findings_in_group > 1 && <div><dt className="inline text-muted-foreground">Reported by: </dt><dd className="inline">{f.findings_in_group} scanner results merged into this finding</dd></div>}
          </dl>
          <p className="text-sm">{f.message}</p>
          <MaskedCode finding={f} />
        </div>
        <div data-slot="verdict" className="space-y-2 rounded-lg border border-border p-3">
          <h3 className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            LLM verdict {model && <span className="font-mono normal-case">({model})</span>}
          </h3>
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={statusTone(f.status)}>{f.status}</Badge>
            <span className="text-sm">confidence {f.confidence ?? 'n/a'}</span>
          </div>
          {f.original_status && (
            <p className="rounded-md border border-amber-300 bg-amber-50 p-2 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
              The model first said <b>{f.original_status}</b>; the checks around it changed that to <b>{f.status}</b>: {f.downgrade_reason}
            </p>
          )}
          <p className="text-sm">{f.rationale || 'No rationale: the LLM did not analyse this finding.'}</p>
          <p className="text-xs text-muted-foreground">
            Evidence cited: {f.evidence_ids?.length ? f.evidence_ids.map((id) => <span key={id} className="mr-1 rounded bg-muted px-1 font-mono">{id}</span>) : 'none'}
          </p>
        </div>
      </div>
    </Section>
  )
}

export function RiskBreakdown({ risk }) {
  if (!risk) {
    return (
      <Section title="Risk score" data-slot="risk">
        <p className="text-sm text-muted-foreground">Not ranked: the risk stage did not run for this finding, or it was dismissed.</p>
      </Section>
    )
  }
  const total = riskTotal(risk.breakdown)
  return (
    <Section title="Risk score" hint="A rule-based ranking with weights chosen by the developers. It is not a measured probability." data-slot="risk">
      <p className="text-sm">
        Score <b>{risk.score}</b> · rank <b>#{risk.rank}</b>
      </p>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Factor</TableHead>
            <TableHead>Why</TableHead>
            <TableHead className="text-right">Weight</TableHead>
            <TableHead className="text-right">Value</TableHead>
            <TableHead className="text-right">Adds</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {risk.breakdown.map((b) => (
            <TableRow key={b.factor} data-factor={b.factor}>
              <TableCell className="font-medium">{b.factor}</TableCell>
              <TableCell className="text-xs text-muted-foreground">{b.detail}</TableCell>
              <TableCell className="text-right">{b.weight}</TableCell>
              <TableCell className="text-right">{b.value}</TableCell>
              <TableCell className="text-right">{b.contribution}</TableCell>
            </TableRow>
          ))}
          <TableRow data-slot="risk-total">
            <TableCell colSpan={4} className="text-right font-semibold">Total</TableCell>
            <TableCell className="text-right font-semibold">
              {total}
              {total === risk.score && <Check className="ml-1 inline h-3.5 w-3.5 text-emerald-600" aria-label="matches the score" />}
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Section>
  )
}

function LinkGroup({ label, items }) {
  return (
    <div data-slot={`links-${label}`}>
      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</h3>
      {items.length ? (
        <ul className="space-y-2">
          {items.map((l) => (
            <li key={`${l.kind}-${l.id}`} className="rounded-lg border border-border p-2.5 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs font-semibold">{l.id}</span>
                <Badge tone={linkTone(l.status)} title={LINK_STATUS_NOTE[l.status]}>{l.status}</Badge>
                <span>{l.title}</span>
              </div>
              <ul className="mt-1 list-disc pl-5 text-xs text-muted-foreground">
                {(l.evidence ?? []).map((e) => <li key={e}>{e}</li>)}
              </ul>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-muted-foreground">No {label.toLowerCase()} linked.</p>
      )}
    </div>
  )
}

export function TraceLinks({ finding: f }) {
  const c = f.introducing_commit
  const stories = (f.links ?? []).filter((l) => l.kind === 'story')
  const tasks = (f.links ?? []).filter((l) => l.kind === 'task')
  return (
    <Section title="Story, task and introducing commit" hint="Where this code came from. 'Verified' links are supported by a simple rule; 'candidate' links are only proposals." data-slot="trace">
      <div className="grid gap-4 md:grid-cols-2">
        <LinkGroup label="Stories" items={stories} />
        <LinkGroup label="Tasks" items={tasks} />
      </div>
      <div data-slot="commit" className="rounded-lg border border-border p-2.5 text-sm">
        {c ? (
          <>
            <p className="flex flex-wrap items-center gap-2">
              <GitCommitHorizontal className="h-4 w-4" />
              <span className="font-mono text-xs font-semibold">{shortSha(c.sha)}</span>
              {c.contributor && <Badge tone="neutral" title="A pseudonym: names and e-mail addresses are never shown">{c.contributor}</Badge>}
              <span>{c.subject}</span>
            </p>
            <p className="mt-1 text-xs text-muted-foreground">{c.how_found}. It shows where the code came from, not who is at fault.</p>
          </>
        ) : (
          <p className="text-xs text-muted-foreground">No introducing commit was found for this finding.</p>
        )}
      </div>
    </Section>
  )
}

export function FixGuidance({ finding: f }) {
  const g = f.fix_guidance
  return (
    <Section title="How to fix it" hint="Standard guidance for this type of issue, then the model's note for this code." data-slot="fix">
      {g ? (
        <>
          <p className="text-sm font-medium">{g.title}</p>
          <ol className="list-decimal space-y-1 pl-5 text-sm">
            {g.steps.map((step) => <li key={step}>{step}</li>)}
          </ol>
          {g.example ? (
            <div data-slot="safe-example">
              <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Safe example ({g.example.language})</p>
              <pre className="overflow-x-auto rounded-lg border border-emerald-300 bg-emerald-50/60 p-3 font-mono text-xs dark:border-emerald-800 dark:bg-emerald-950/30">{g.example.code}</pre>
            </div>
          ) : null}
          {g.references?.length ? (
            <p data-slot="references" className="flex flex-wrap items-center gap-3 text-xs">
              Read more:
              {g.references.map((url) => (
                <a key={url} href={url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-primary underline-offset-2 hover:underline">
                  {referenceLabel(url)} <ExternalLink className="h-3 w-3" />
                </a>
              ))}
            </p>
          ) : null}
        </>
      ) : (
        <p className="text-sm text-muted-foreground">No standard guidance applies.</p>
      )}
      <div data-slot="tailored-note" className="rounded-lg border border-border bg-muted/40 p-3 text-sm">
        <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Tailored note for this code</p>
        {f.recommendation ? f.recommendation : <span className="text-muted-foreground">Tailored note not generated in this run</span>}
      </div>
    </Section>
  )
}

export function ProbeCard({ probe, threshold }) {
  return (
    <Section title="Probe question" hint="A question the Tutor would ask about this finding. The Tutor is a mock: nobody answered and nothing was graded." data-slot="probe">
      <p className="flex flex-wrap items-center gap-2 text-sm">
        <MockBadge /> {probeSummary(probe)}
      </p>
      {probe ? (
        <>
          <p className="rounded-lg border border-border bg-muted/40 p-3 text-sm">{probe.question}</p>
          {probe.attempt_log?.length ? (
            <ul className="space-y-1 text-xs text-muted-foreground">
              {probe.attempt_log.map((a) => (
                <li key={a.attempt}>
                  Attempt {a.attempt} (hint level {a.hint_level}): simulated score <b>{a.score}</b> against the threshold {threshold ?? probe.threshold} → {a.result}
                </li>
              ))}
            </ul>
          ) : null}
          {probe.escalation_reason && <p className="text-xs">Escalated to the lecturer: {probe.escalation_reason}</p>}
        </>
      ) : null}
    </Section>
  )
}
