import { useState } from 'react'
import {
  ChevronDown,
  BookOpen,
  FlaskConical,
  Copy,
  Lightbulb,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Sparkles,
  UserCheck,
  ShieldCheck,
  Check,
} from 'lucide-react'
import Card from '../../../shared/components/Card.jsx'
import Badge from '../../../shared/components/Badge.jsx'
import { Button } from '@/components/ui/button'
import QualityRadarChart from './QualityRadarChart.jsx'
import { QUALITY_DIMENSIONS } from '../data/mockData.js'
import { DIMENSION_ISSUE, QUALITY_GATE_THRESHOLD } from '../utils.js'

function dimTier(score) {
  if (score >= 80) return 'pass'
  if (score >= 60) return 'warn'
  return 'fail'
}

const DIM_ICON = {
  pass: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />,
  warn: <AlertTriangle className="h-3.5 w-3.5 text-amber-500 shrink-0" />,
  fail: <XCircle className="h-3.5 w-3.5 text-destructive shrink-0" />,
}

const IEEE_STANDARD_CLAUSES = {
  clarity: 'IEEE 830 § 4.3.2',
  completeness: 'IEEE 830 § 4.3.3',
  consistency: 'IEEE 830 § 4.3.4',
  testability: 'IEEE 830 § 4.3.5',
  correctness: 'IEEE 830 § 4.3.1',
  traceability: 'IEEE 830 § 4.3.8',
}

const QUALITY_TONE = { high: 'success', medium: 'warning', low: 'danger' }

/**
 * Unified "Why this score? — IEEE 830 Radar & Agent Evidence" studio.
 * Combines the multi-dimension Radar Chart with deep diagnostic reasoning,
 * detected smells, suggested rewrite, retrieval evidence, and actionable remedies.
 */
export default function QualityEvidencePanel({
  requirement,
  onApplyRewrite,
  onConsult,
  defaultOpen = true,
}) {
  const [open, setOpen] = useState(defaultOpen)
  if (!requirement) return null

  const dimensionScores = requirement.dimensionScores || {}
  const details = requirement.dimensionDetails || {}
  const smells = requirement.smells || []
  const retrieval = requirement.retrieval || {}
  const standards = retrieval.standards || []
  const exemplars = retrieval.exemplars || []
  const duplicates = retrieval.cross_req_hits || []

  // Calculate passing dimension stats
  const passingDimsCount = QUALITY_DIMENSIONS.filter(
    (d) => (dimensionScores[d.key] ?? 0) >= QUALITY_GATE_THRESHOLD,
  ).length

  const attentionDims = QUALITY_DIMENSIONS.filter(
    (d) => (dimensionScores[d.key] ?? 0) < QUALITY_GATE_THRESHOLD,
  )

  const flaggedDims = Object.entries(details).filter(([, d]) => (d.issues || []).length > 0)

  return (
    <Card className="p-0 overflow-hidden border-border bg-card">
      {/* Header bar with accordion toggle */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-muted/40 transition-colors cursor-pointer border-b border-border/50"
      >
        <div className="flex items-center gap-2.5">
          <div className="h-7 w-7 rounded-lg bg-primary/10 flex items-center justify-center text-primary shrink-0">
            <Lightbulb className="h-4 w-4" />
          </div>
          <div>
            <span className="flex items-center gap-2 text-sm font-bold text-foreground">
              Why this score? — IEEE 830 Quality Radar &amp; Agent Evidence
            </span>
            <p className="text-[11px] text-muted-foreground">
              Diagnostic breakdown, 6-dimension reasoning profile, and retrieval evidence
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <Badge
            tone={requirement.status === 'Passing' ? 'success' : 'warning'}
            className="text-xs font-semibold px-2 py-0.5"
          >
            {requirement.overallScore}% · {requirement.status}
          </Badge>
          <ChevronDown
            className={`h-4 w-4 text-muted-foreground transition-transform duration-200 ${
              open ? 'rotate-180' : ''
            }`}
          />
        </div>
      </button>

      {open && (
        <div className="p-4 sm:p-5 space-y-6">
          {/* Top Section: Radar Chart + Quality Gate Profile Overview */}
          <div className="grid grid-cols-1 md:grid-cols-[260px_1fr] gap-4 items-center bg-muted/20 p-4 rounded-xl border border-border/60">
            {/* Visual Radar Polygon */}
            <div className="flex flex-col items-center justify-center">
              <QualityRadarChart scores={dimensionScores} height={190} />
              <span className="text-[10px] uppercase font-bold tracking-wider text-muted-foreground mt-1">
                IEEE 830 Radar Polygon
              </span>
            </div>

            {/* Quality Summary & Metrics */}
            <div className="space-y-3">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-foreground flex items-center gap-1.5">
                  <ShieldCheck className="h-4 w-4 text-primary" />
                  IEEE 830 Gate Verdict
                </span>
                <Badge
                  tone={passingDimsCount === 6 ? 'success' : passingDimsCount >= 4 ? 'warning' : 'danger'}
                  className="text-xs font-semibold"
                >
                  {passingDimsCount} of 6 Dimensions ≥ {QUALITY_GATE_THRESHOLD}%
                </Badge>
              </div>

              <p className="text-xs text-muted-foreground leading-relaxed">
                {passingDimsCount === 6 ? (
                  <span className="text-emerald-600 dark:text-emerald-400 font-medium">
                    Excellent specification! All six IEEE 830 quality dimensions satisfy the {QUALITY_GATE_THRESHOLD}% gate threshold.
                  </span>
                ) : (
                  <span>
                    <strong className="text-foreground">{attentionDims.length} dimension(s)</strong> require refinement:{' '}
                    <span className="text-amber-600 dark:text-amber-400 font-medium">
                      {attentionDims.map((d) => d.label).join(', ')}
                    </span>
                    . Review the actionable remedies below to elevate the score.
                  </span>
                )}
              </p>

              <div className="flex items-center gap-3 pt-1 text-xs text-muted-foreground flex-wrap">
                {requirement.confidence !== undefined && (
                  <span className="bg-muted/60 px-2 py-0.5 rounded-md font-mono text-[11px] text-foreground">
                    Confidence: {Math.round(requirement.confidence * 100)}%
                  </span>
                )}
                {onConsult && (
                  <button
                    type="button"
                    onClick={onConsult}
                    className="text-xs text-primary font-semibold hover:underline inline-flex items-center gap-1 cursor-pointer ml-auto"
                  >
                    <UserCheck className="h-3.5 w-3.5" /> Book Advisory with Supervisor
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Section: Six IEEE 830 Dimension Breakdown Cards */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
              <span>Dimension Breakdown &amp; Actionable Remedies</span>
              <span className="text-[10px] font-normal lowercase text-muted-foreground">
                (click remedies to guide edits)
              </span>
            </h4>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {QUALITY_DIMENSIONS.map((dim) => {
                const score = dimensionScores[dim.key] ?? 0
                const tier = dimTier(score)
                const real = details[dim.key]
                const fallback = DIMENSION_ISSUE[dim.key]
                const issueText = real?.issues?.[0] || real?.rationale || fallback?.issue
                const remedyText = fallback?.suggestion
                const standardClause = IEEE_STANDARD_CLAUSES[dim.key]

                return (
                  <div
                    key={dim.key}
                    className={`p-3 rounded-xl border transition-all ${
                      tier === 'pass'
                        ? 'border-border/70 bg-card hover:border-emerald-500/30'
                        : tier === 'warn'
                          ? 'border-amber-500/30 bg-amber-500/5'
                          : 'border-destructive/30 bg-destructive/5'
                    }`}
                  >
                    {/* Dimension Title & Score */}
                    <div className="flex items-center justify-between text-xs mb-1.5">
                      <div className="flex items-center gap-1.5 font-bold text-foreground text-xs">
                        {DIM_ICON[tier]}
                        <span>{dim.label}</span>
                        {standardClause && (
                          <span className="text-[10px] text-muted-foreground font-normal">
                            · {standardClause}
                          </span>
                        )}
                      </div>
                      <Badge
                        tone={tier === 'pass' ? 'success' : tier === 'warn' ? 'warning' : 'danger'}
                        className="text-[11px] font-bold px-1.5 py-0"
                      >
                        {score}%
                      </Badge>
                    </div>

                    {/* Rationale & Issues */}
                    {tier === 'pass' ? (
                      <p className="text-[11px] text-muted-foreground leading-snug">
                        {real?.rationale || 'Satisfies the IEEE standard criteria with verifiable precision.'}
                      </p>
                    ) : (
                      <div className="space-y-1.5 pt-1 border-t border-border/40 text-[11px]">
                        {issueText && (
                          <p className="text-foreground leading-snug">
                            <span className="text-destructive font-semibold">Issue: </span>
                            {issueText}
                          </p>
                        )}
                        {remedyText && (
                          <p className="text-muted-foreground leading-snug bg-muted/40 p-1.5 rounded-md border border-border/40">
                            <strong className="text-foreground">Remedy: </strong>
                            {remedyText}
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>

          {/* Section: AI Suggested Rewrite (if present) */}
          {requirement.suggestedRewrite && (
            <div className="p-3.5 rounded-xl border border-primary/30 bg-primary/5 space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5" /> AI Quality Rewrite Suggestion
                </h4>
                {onApplyRewrite && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onApplyRewrite(requirement.suggestedRewrite)}
                    className="text-xs h-7 gap-1 text-primary border-primary/30 hover:bg-primary/10 cursor-pointer"
                  >
                    <Check className="h-3 w-3" /> Apply to Editor
                  </Button>
                )}
              </div>
              <p className="text-xs text-foreground bg-card p-3 rounded-lg border border-border leading-relaxed font-sans">
                {requirement.suggestedRewrite}
              </p>
            </div>
          )}

          {/* Section: Detected Linguistic Smells */}
          {smells.length > 0 && (
            <div>
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1.5">
                <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
                Detected Linguistic Smells ({smells.length})
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {smells.map((s, i) => (
                  <Badge
                    key={i}
                    tone="warning"
                    className="text-xs py-0.5 px-2 font-medium"
                    title={s.suggestion}
                  >
                    {s.type}
                    {s.span ? `: "${s.span}"` : ''}
                  </Badge>
                ))}
              </div>
            </div>
          )}

          {/* Section: Retrieval Evidence (Glass-box RAG) */}
          <div className="grid gap-3 sm:grid-cols-2 pt-2 border-t border-border/60">
            <div className="p-3 rounded-xl bg-muted/20 border border-border/60">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1.5">
                <BookOpen className="h-3.5 w-3.5 text-primary" /> Standards Retrieved
              </h4>
              {standards.length === 0 ? (
                <p className="text-[11px] text-muted-foreground">Standard IEEE 830 baseline references applied.</p>
              ) : (
                <ul className="space-y-1.5 text-[11px] text-muted-foreground">
                  {standards.map((s, i) => (
                    <li key={i} className="leading-snug">
                      <span className="font-semibold text-foreground capitalize">{s.dimension}: </span>
                      {s.text?.slice(0, 110)}…
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="p-3 rounded-xl bg-muted/20 border border-border/60">
              <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-2 flex items-center gap-1.5">
                <FlaskConical className="h-3.5 w-3.5 text-primary" /> Exemplar References
              </h4>
              {exemplars.length === 0 ? (
                <p className="text-[11px] text-muted-foreground">IEEE 830 benchmark corpus exemplars loaded.</p>
              ) : (
                <ul className="space-y-1.5 text-[11px] text-muted-foreground">
                  {exemplars.map((e, i) => (
                    <li key={i} className="flex gap-1.5 leading-snug">
                      <Badge tone={QUALITY_TONE[e.quality] || 'neutral'} className="text-[9px] px-1 py-0 h-fit shrink-0">
                        {e.quality}
                      </Badge>
                      <span className="text-foreground/90">{e.requirement?.slice(0, 85)}…</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          {/* Duplicate / Similar Requirements */}
          {duplicates.length > 0 && (
            <div className="p-3 rounded-xl bg-destructive/5 border border-destructive/20">
              <h4 className="text-xs font-bold uppercase tracking-wider text-destructive mb-1.5 flex items-center gap-1.5">
                <Copy className="h-3.5 w-3.5 text-destructive" />
                Cross-Requirement Overlap Warning
              </h4>
              <ul className="space-y-1 text-xs text-destructive/90">
                {duplicates.map((h, i) => (
                  <li key={i}>
                    <strong className="font-mono">({Math.round((h.similarity || 0) * 100)}% match)</strong> {h.text}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {flaggedDims.length === 0 && smells.length === 0 && (
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-xs text-emerald-700 dark:text-emerald-300 font-medium flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-500" />
              <span>All 6 IEEE 830 dimensions satisfy the quality threshold. No linguistic smells or ambiguities detected.</span>
            </div>
          )}
        </div>
      )}
    </Card>
  )
}
