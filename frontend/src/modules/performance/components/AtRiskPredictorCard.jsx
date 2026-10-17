import PropTypes from 'prop-types'
import { ShieldCheck, AlertTriangle, AlertOctagon, Sparkles } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'

/**
 * AtRiskPredictorCard: Machine Learning Free-Rider & At-Risk Prediction Card
 *
 * Displays early-warning failure probability, risk classification badge,
 * and SHAP-style Explainable AI (XAI) feature attribution deltas.
 */
export default function AtRiskPredictorCard({
  probability = 0.12,
  tier = 'Low',
  primaryFactor = 'Consistent cadence across all sprint cycles',
  features = [
    { name: 'Commit Rhythm (Cadence)', impact: -18, status: 'positive' },
    { name: 'PR Review Latency', impact: -12, status: 'positive' },
    { name: 'Daily Scrum Punctuality', impact: -10, status: 'positive' },
    { name: 'Task Inactivity Drift', impact: 6, status: 'negative' },
  ],
}) {
  const probPercent = Math.round(probability * 100)

  // Risk styling
  let badgeColor = 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
  let Icon = ShieldCheck
  let statusText = 'Low Risk — On Track'

  if (probPercent >= 60 || tier === 'Critical' || tier === 'High') {
    badgeColor = 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20'
    Icon = AlertOctagon
    statusText = 'Critical Risk — Immediate Intervention'
  } else if (probPercent >= 25 || tier === 'Moderate' || tier === 'Warning') {
    badgeColor = 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20'
    Icon = AlertTriangle
    statusText = 'Moderate Warning — Free-Rider Suspect'
  }

  return (
    <div className="rounded-xl border border-border bg-card p-4 sm:p-5 shadow-xs space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">
              ML At-Risk Predictor
            </h3>
            <p className="text-[11px] text-muted-foreground">
              Gradient Boosted Free-Rider Classifier
            </p>
          </div>
        </div>

        <Badge variant="outline" className={`text-xs px-2.5 py-1 font-semibold ${badgeColor}`}>
          <Icon className="h-3.5 w-3.5 mr-1" />
          {statusText}
        </Badge>
      </div>

      {/* Probability Gauge Bar */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Predicted Risk Probability:</span>
          <span className="font-mono font-bold text-foreground">{probPercent}%</span>
        </div>
        <Progress
          value={probPercent}
          className={`h-2.5 ${
            probPercent >= 60
              ? '[&>div]:bg-rose-500'
              : probPercent >= 25
              ? '[&>div]:bg-amber-500'
              : '[&>div]:bg-emerald-500'
          }`}
        />
      </div>

      {/* Primary Attribution */}
      <div className="p-2.5 rounded-lg bg-muted/40 border border-border/60 text-xs">
        <span className="text-muted-foreground font-medium">Model Diagnosis: </span>
        <span className="text-foreground font-medium">{primaryFactor}</span>
      </div>

      {/* Explainable AI (XAI) Attribution Breakdown */}
      <div className="space-y-2 pt-1">
        <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
          Top Explainability Drivers (SHAP Attribution):
        </span>
        <div className="space-y-1.5">
          {features.map((feat) => {
            const isProtective = feat.impact < 0
            return (
              <div
                key={feat.name}
                className="flex items-center justify-between text-xs py-1 border-b border-border/30 last:border-b-0"
              >
                <span className="text-muted-foreground truncate mr-2">
                  {feat.name}
                </span>
                <span
                  className={`font-mono text-xs font-semibold shrink-0 ${
                    isProtective
                      ? 'text-emerald-500'
                      : 'text-rose-500'
                  }`}
                >
                  {isProtective ? `${feat.impact}% (Protective)` : `+${feat.impact}% (Risk)`}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

AtRiskPredictorCard.propTypes = {
  probability: PropTypes.number,
  tier: PropTypes.string,
  primaryFactor: PropTypes.string,
  features: PropTypes.arrayOf(
    PropTypes.shape({
      name: PropTypes.string,
      impact: PropTypes.number,
      status: PropTypes.string,
    }),
  ),
}
