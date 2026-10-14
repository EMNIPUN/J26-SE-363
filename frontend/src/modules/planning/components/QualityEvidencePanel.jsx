import { useState } from 'react'
import { ChevronDown, BookOpen, FlaskConical, Copy, Lightbulb, AlertTriangle } from 'lucide-react'
import Card from '../../../shared/components/Card.jsx'
import Badge from '../../../shared/components/Badge.jsx'

const QUALITY_TONE = { high: 'success', medium: 'warning', low: 'danger' }

/**
 * "Why this score?" — the glass-box view of what the Quality agent used for one
 * requirement: per-dimension rationale, detected smells, suggested rewrite, and
 * the retrieval evidence (IEEE 830/SMART criteria, exemplars, duplicate reqs).
 * Supports NFR-05 (all diagnostic rationales visible and inspectable).
 */
export default function QualityEvidencePanel({ requirement }) {
  const [open, setOpen] = useState(false)
  if (!requirement) return null

  const details = requirement.dimensionDetails || {}
  const smells = requirement.smells || []
  const retrieval = requirement.retrieval || {}
  const standards = retrieval.standards || []
  const exemplars = retrieval.exemplars || []
  const duplicates = retrieval.cross_req_hits || []

  const flaggedDims = Object.entries(details).filter(([, d]) => (d.issues || []).length > 0)

  return (
    <Card className="p-0 overflow-hidden border-border">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-muted/40 transition-colors cursor-pointer"
      >
        <span className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <Lightbulb className="h-4 w-4 text-primary" />
          Why this score? — what the agent used
        </span>
        <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-4 border-t border-border/60 pt-4">
          {/* Per-dimension rationale */}
          <section>
            <h4 className="text-xs font-bold uppercase tracking-wide text-muted-foreground mb-2">Dimension reasoning</h4>
            <div className="space-y-2">
              {Object.entries(details).map(([dim, d]) => (
                <div key={dim} className="text-xs">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold capitalize text-foreground">{dim}</span>
                    <Badge tone={d.score >= 80 ? 'success' : d.score >= 60 ? 'warning' : 'danger'} className="text-[10px] px-1.5 py-0">
                      {d.score}
                    </Badge>
                  </div>
                  {d.rationale && <p className="text-muted-foreground mt-0.5">{d.rationale}</p>}
                  {(d.issues || []).length > 0 && (
                    <ul className="mt-1 ml-3 list-disc text-destructive/90 space-y-0.5">
                      {d.issues.map((issue, i) => (
                        <li key={i}>{issue}</li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </div>
          </section>

          {/* Smells */}
          {smells.length > 0 && (
            <section>
              <h4 className="text-xs font-bold uppercase tracking-wide text-muted-foreground mb-2 flex items-center gap-1.5">
                <AlertTriangle className="h-3.5 w-3.5 text-amber-500" /> Detected smells
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {smells.map((s, i) => (
                  <Badge key={i} tone="warning" className="text-[10px]" title={s.suggestion}>
                    {s.type}{s.span ? `: "${s.span}"` : ''}
                  </Badge>
                ))}
              </div>
            </section>
          )}

          {/* Suggested rewrite */}
          {requirement.suggestedRewrite && (
            <section>
              <h4 className="text-xs font-bold uppercase tracking-wide text-muted-foreground mb-1">Suggested rewrite</h4>
              <p className="text-xs text-foreground bg-primary/5 border border-primary/20 rounded-md px-3 py-2">
                {requirement.suggestedRewrite}
              </p>
            </section>
          )}

          {/* Retrieval evidence */}
          <section className="grid gap-3 sm:grid-cols-2">
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wide text-muted-foreground mb-1.5 flex items-center gap-1.5">
                <BookOpen className="h-3.5 w-3.5 text-primary" /> Standards retrieved
              </h4>
              {standards.length === 0 ? (
                <p className="text-[11px] text-muted-foreground">None.</p>
              ) : (
                <ul className="space-y-1 text-[11px] text-muted-foreground">
                  {standards.map((s, i) => (
                    <li key={i}>
                      <span className="font-medium capitalize text-foreground">{s.dimension}</span>: {s.text?.slice(0, 120)}…
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wide text-muted-foreground mb-1.5 flex items-center gap-1.5">
                <FlaskConical className="h-3.5 w-3.5 text-primary" /> Example requirements
              </h4>
              {exemplars.length === 0 ? (
                <p className="text-[11px] text-muted-foreground">None.</p>
              ) : (
                <ul className="space-y-1 text-[11px] text-muted-foreground">
                  {exemplars.map((e, i) => (
                    <li key={i} className="flex gap-1.5">
                      <Badge tone={QUALITY_TONE[e.quality] || 'neutral'} className="text-[9px] px-1 py-0 h-fit shrink-0">
                        {e.quality}
                      </Badge>
                      <span>{e.requirement?.slice(0, 90)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          {/* Duplicate / similar requirements */}
          {duplicates.length > 0 && (
            <section>
              <h4 className="text-xs font-bold uppercase tracking-wide text-muted-foreground mb-1.5 flex items-center gap-1.5">
                <Copy className="h-3.5 w-3.5 text-destructive" /> Similar requirements (possible duplicate/overlap)
              </h4>
              <ul className="space-y-1 text-[11px] text-destructive/90">
                {duplicates.map((h, i) => (
                  <li key={i}>({Math.round((h.similarity || 0) * 100)}% similar) {h.text}</li>
                ))}
              </ul>
            </section>
          )}

          {flaggedDims.length === 0 && smells.length === 0 && (
            <p className="text-[11px] text-emerald-600">No issues flagged — this requirement is in good shape.</p>
          )}
        </div>
      )}
    </Card>
  )
}
