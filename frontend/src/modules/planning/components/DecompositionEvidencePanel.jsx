import { useState } from 'react'
import { ChevronDown, BookOpen, Lightbulb, AlertTriangle, CheckCircle2 } from 'lucide-react'
import Card from '../../../shared/components/Card.jsx'
import Badge from '../../../shared/components/Badge.jsx'

export default function DecompositionEvidencePanel({ evaluation }) {
  const [open, setOpen] = useState(true)
  if (!evaluation) return null

  const { investResults, gaps, covered, patternExamples, summary, coverage, score, verdict, confidence } = evaluation

  const investEntries = Object.entries(investResults || {})
  const failingStories = investEntries.filter(([, r]) => !r.overallPass)

  return (
    <Card className="p-0 overflow-hidden border-border bg-card">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-muted/40 transition-colors cursor-pointer"
      >
        <span className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <Lightbulb className="h-4 w-4 text-primary" />
          Agent Reasoning Evidence &amp; Retrieval Patterns
        </span>
        <div className="flex items-center gap-2">
          <Badge tone={verdict === 'Validated' ? 'success' : 'warning'} className="text-[10px] px-2 py-0.5">
            {score}% · {verdict}
          </Badge>
          <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${open ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {open && (
        <div className="px-5 pb-5 space-y-4 border-t border-border/60 pt-4">
          {/* Summary */}
          <section>
            <h4 className="text-xs font-bold uppercase tracking-wide text-muted-foreground mb-1">Summary</h4>
            <p className="text-xs text-foreground">{summary}</p>
            <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
              <span>Score: <strong className="text-foreground">{score}/100</strong></span>
              <span>Verdict: <Badge tone={verdict === 'Validated' ? 'success' : 'warning'} className="text-[10px] px-1.5 py-0">{verdict}</Badge></span>
              <span>Confidence: <strong className="text-foreground">{(confidence * 100).toFixed(0)}%</strong></span>
            </div>
          </section>

          {/* Coverage */}
          <section>
            <h4 className="text-xs font-bold uppercase tracking-wide text-muted-foreground mb-2">Coverage ({Math.round(coverage * 100)}%)</h4>
            {(covered || []).length > 0 && (
              <div className="mb-2">
                <p className="text-[11px] text-emerald-600 font-medium mb-1">Covered aspects</p>
                <ul className="space-y-0.5 text-[11px] text-muted-foreground">
                  {covered.map((a) => (
                    <li key={a.id} className="flex items-center gap-1.5">
                      <CheckCircle2 className="h-3 w-3 text-emerald-500 shrink-0" />
                      {a.label}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {(gaps || []).length > 0 && (
              <div>
                <p className="text-[11px] text-amber-600 font-medium mb-1">Gaps (uncovered)</p>
                <ul className="space-y-0.5 text-[11px] text-destructive/90">
                  {gaps.map((a) => (
                    <li key={a.id} className="flex items-center gap-1.5">
                      <AlertTriangle className="h-3 w-3 text-amber-500 shrink-0" />
                      {a.label}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>

          {/* Failing stories INVEST detail */}
          {failingStories.length > 0 && (
            <section>
              <h4 className="text-xs font-bold uppercase tracking-wide text-muted-foreground mb-2">
                Stories needing attention ({failingStories.length})
              </h4>
              <div className="space-y-2">
                {failingStories.map(([storyId, result]) => {
                  const failing = ['independent', 'negotiable', 'valuable', 'estimable', 'small', 'testable'].filter(
                    (c) => !result[c]?.pass,
                  )
                  return (
                    <div key={storyId} className="text-xs">
                      <span className="font-semibold text-foreground">{storyId}</span>
                      <span className="text-destructive/90 ml-1.5">
                        — fails: {failing.map((c) => c.charAt(0).toUpperCase() + c.slice(1)).join(', ')}
                      </span>
                      <ul className="mt-0.5 ml-3 list-disc text-muted-foreground space-y-0.5">
                        {failing.map((c) => (
                          <li key={c}>{result[c]?.note}</li>
                        ))}
                      </ul>
                    </div>
                  )
                })}
              </div>
            </section>
          )}

          {/* Pattern examples */}
          {patternExamples && patternExamples.length > 0 && (
            <section>
              <h4 className="text-xs font-bold uppercase tracking-wide text-muted-foreground mb-1.5 flex items-center gap-1.5">
                <BookOpen className="h-3.5 w-3.5 text-primary" /> Retrieved decomposition patterns
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {patternExamples.map((ex) => (
                  <div key={ex.id} className="p-2.5 rounded-lg border border-border bg-card">
                    <p className="text-xs font-semibold text-foreground mb-1">{ex.title}</p>
                    <ul className="text-[11px] text-muted-foreground list-disc list-inside space-y-0.5">
                      {(ex.stories || []).slice(0, 4).map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                    {ex.note && <p className="text-[10px] text-muted-foreground mt-1 italic">{ex.note}</p>}
                  </div>
                ))}
              </div>
            </section>
          )}

          {failingStories.length === 0 && (gaps || []).length === 0 && (
            <p className="text-[11px] text-emerald-600">No issues flagged — this decomposition is in good shape.</p>
          )}
        </div>
      )}
    </Card>
  )
}
