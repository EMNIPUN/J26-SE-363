import { useState } from 'react'
import { ShieldAlert, ShieldCheck } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import Badge from '@/shared/components/Badge.jsx'
import {
  INDICATOR_NOTE,
  auditFacts,
  describeRejected,
  indicatorRows,
  optionsLabel,
  pageOf,
  rejectedCount,
  scrutinyMeaning,
  scrutinyTone,
} from '../lib/agents.js'

function Fact({ label, children, ...props }) {
  return (
    <div {...props}>
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium">{children}</dd>
    </div>
  )
}

// One agent's decisions: what it could choose, what it chose and why. A choice the code refused (outside the allowed list) is highlighted.
export function DecisionTrail({ agent, onlyRejected }) {
  const rejected = rejectedCount(agent.entries)
  const rows = onlyRejected ? agent.entries.filter((e) => e.rejected) : agent.entries
  return (
    <Card data-slot="trail" data-agent={agent.key} className="gap-3 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold">{agent.title}</h3>
          <p className="text-xs text-muted-foreground">Goal: {agent.goal}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge tone="neutral">{agent.entries.length} decision{agent.entries.length === 1 ? '' : 's'}</Badge>
          <Badge tone={rejected ? 'danger' : 'success'} data-slot="rejected-count">
            {rejected} rejected choice{rejected === 1 ? '' : 's'}
          </Badge>
        </div>
      </div>
      {rows.length ? (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Step</TableHead>
              <TableHead>For</TableHead>
              <TableHead>Policy</TableHead>
              <TableHead>It could choose</TableHead>
              <TableHead>It chose</TableHead>
              <TableHead>Why</TableHead>
              <TableHead>Outcome</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((e, index) => (
              <TableRow
                key={`${e.step}-${index}`}
                data-step={e.step}
                data-rejected={e.rejected ? 'true' : 'false'}
                className={e.rejected ? 'border-l-4 border-l-destructive bg-destructive/10' : undefined}
              >
                <TableCell>{e.step}</TableCell>
                <TableCell className="font-mono text-xs">{e.subject ?? '-'}</TableCell>
                <TableCell className="text-xs">{e.policy}</TableCell>
                <TableCell className="max-w-48 whitespace-normal text-xs">{optionsLabel(e.options)}</TableCell>
                <TableCell className="whitespace-normal font-mono text-xs">{e.chosen}</TableCell>
                <TableCell className="max-w-72 whitespace-normal text-xs">
                  {e.rejected && (
                    <p data-slot="rejected-note" className="mb-1 font-semibold text-destructive">
                      REJECTED CHOICE. {describeRejected(e.rejected)}
                    </p>
                  )}
                  {e.reason}
                </TableCell>
                <TableCell className="max-w-64 whitespace-normal text-xs text-muted-foreground">{e.outcome ?? '-'}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <p className="text-sm text-muted-foreground">
          {onlyRejected ? 'No choice of this agent was rejected.' : 'This agent made no decision in this run (the stage did not run).'}
        </p>
      )}
    </Card>
  )
}

// The state of the governance gate at the end of the run, and what the repository's own text tried to say to the model.
export function GovernancePanel({ governance }) {
  if (!governance) {
    return (
      <Card data-slot="governance" className="gap-2 p-5">
        <h2 className="text-sm font-semibold">Governance</h2>
        <p className="text-sm text-muted-foreground">No governance record in this run.</p>
      </Card>
    )
  }
  const s = governance.scrutiny ?? {}
  const rows = indicatorRows(governance.injection_indicators)
  const Icon = s.level === 'normal' ? ShieldCheck : ShieldAlert
  return (
    <Card data-slot="governance" className="gap-4 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold">Governance</h2>
          <p className="text-xs text-muted-foreground">Deterministic checks around the LLM stages. They never change a verdict and never drop a finding.</p>
        </div>
        <Badge tone={scrutinyTone(s.level)} data-slot="scrutiny-level">
          <Icon className="h-3 w-3" /> scrutiny {s.level ?? 'not recorded'}
        </Badge>
      </div>
      <p className="text-sm" data-slot="scrutiny-meaning">{scrutinyMeaning(s)}</p>
      <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Fact label="Mode">{governance.mode}</Fact>
        <Fact label="Scrutiny score" data-fact="score">{s.score ?? 'n/a'} (elevated at {s.elevated_at}, high at {s.high_at})</Fact>
        <Fact label="Second checks" data-fact="second-checks">{s.second_checks ?? 0} (blocked {s.second_check_blocks ?? 0})</Fact>
        <Fact label="Escalated for human review" data-fact="escalation">{s.escalated ? `Yes: ${s.escalation_reason}` : 'No'}</Fact>
        <Fact label="Calls checked">{governance.calls_checked}</Fact>
        <Fact label="Calls blocked">{governance.calls_blocked}</Fact>
        <Fact label="Sent in warn-only mode">{governance.violations_allowed_in_warn_only}</Fact>
        <Fact label="Values removed from the report">{governance.report_items_removed}</Fact>
      </dl>

      <div data-slot="indicators">
        <h3 className="mb-1 flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Prompt-injection indicators in the repository
          <Badge tone="warning">{INDICATOR_NOTE}</Badge>
        </h3>
        {rows.length ? (
          <>
            <p className="mb-2 text-xs text-muted-foreground">
              Text in the README or a commit message that looks like an instruction to the model. A match is a heuristic <b>{INDICATOR_NOTE}</b>: it was logged and nothing was blocked or changed.
            </p>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Where</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Pattern</TableHead>
                  <TableHead className="text-right">Times</TableHead>
                  <TableHead>Reading</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r) => (
                  <TableRow key={`${r.source}-${r.pattern}`} data-pattern={r.pattern}>
                    <TableCell>{r.kind}</TableCell>
                    <TableCell className="font-mono text-xs">{r.source}</TableCell>
                    <TableCell className="font-mono text-xs">{r.pattern}</TableCell>
                    <TableCell className="text-right">{r.count}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">{INDICATOR_NOTE}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </>
        ) : (
          <p className="text-sm text-muted-foreground">
            No indicator was found in the {governance.repo_sources_scanned ?? 0} README and commit-message sources that were scanned. This is a heuristic check: it is {INDICATOR_NOTE} that the repository is clean.
          </p>
        )}
      </div>

      {s.history?.length ? (
        <div data-slot="scrutiny-history">
          <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">How the level changed</h3>
          <ol className="list-decimal space-y-0.5 pl-5 text-xs">
            {s.history.map((h, i) => (
              <li key={i}>
                {h.event.replace(/_/g, ' ')}
                {h.points ? `: +${h.points} points` : ''}
                {h.from ? `: ${h.from} → ${h.to}` : ''} (score {h.score})
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </Card>
  )
}

// audit.jsonl as a table. It holds fingerprints (hashes), ids, counts and decisions, never the text of a prompt: that is what makes it safe to show.
export function AuditTable({ lines, total }) {
  const [page, setPage] = useState(0)
  const view = pageOf(lines, page)
  return (
    <Card data-slot="audit" className="gap-3 p-5">
      <div>
        <h2 className="text-sm font-semibold">Audit log (hashes only)</h2>
        <p className="text-xs text-muted-foreground">
          Every governed step of the run, as recorded. Prompts appear only as a short fingerprint (hash), never as text. Visible to lecturers and administrators only.
        </p>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>#</TableHead>
            <TableHead>Event</TableHead>
            <TableHead>Facts</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {view.rows.map((line) => (
            <TableRow key={line.seq} data-seq={line.seq} data-event={line.event}>
              <TableCell>{line.seq}</TableCell>
              <TableCell className="font-mono text-xs">{line.event}</TableCell>
              <TableCell className="whitespace-normal text-xs">
                {auditFacts(line).map((f) => (
                  <span key={f.name} className="mr-2 inline-block">
                    <span className="text-muted-foreground">{f.name}=</span>
                    <span className={f.hash ? 'font-mono' : undefined} data-hash={f.hash ? 'true' : undefined}>{f.value}</span>
                  </span>
                ))}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>
          Lines {view.page * 25 + 1}-{view.page * 25 + view.rows.length} of {total ?? view.total}
        </span>
        <span className="flex gap-2">
          <button type="button" className="rounded border border-border px-2 py-1 disabled:opacity-40" disabled={view.page === 0} onClick={() => setPage(view.page - 1)}>
            Previous
          </button>
          <button type="button" className="rounded border border-border px-2 py-1 disabled:opacity-40" disabled={view.page >= view.pages - 1} onClick={() => setPage(view.page + 1)}>
            Next
          </button>
        </span>
      </div>
    </Card>
  )
}
