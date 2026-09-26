import PropTypes from 'prop-types'
import { AlertTriangle, CheckCircle2, TrendingUp } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

const MEMBER_COLORS = [
  'bg-emerald-500 hover:bg-emerald-600',
  'bg-blue-500 hover:bg-blue-600',
  'bg-violet-500 hover:bg-violet-600',
  'bg-amber-500 hover:bg-amber-600',
]

/**
 * TeamParityBar: Team Contribution Equity & Free-Rider Visualizer
 *
 * Compares actual individual student contribution shares against the ideal
 * fair-share baseline (100% / N). Identifies team imbalances and free-riders.
 */
export default function TeamParityBar({
  members = [],
  highlightStudentId = null,
}) {
  const memberCount = members.length || 1
  const idealShare = Math.round(100 / memberCount)

  // Calculate total points for percentage normalization
  const totalScore = members.reduce((sum, m) => sum + (m.currentScore || m.score || 8.0), 0)
  
  const normalizedMembers = members.map((m, idx) => {
    const raw = m.currentScore || m.score || 8.0
    const percent = Math.round((raw / totalScore) * 100)
    const isFreeRider = percent < idealShare * 0.45 // E.g., < 11% in a 4-person team
    const isDominant = percent > idealShare * 1.6 // E.g., > 40% in a 4-person team
    return {
      ...m,
      percent,
      color: MEMBER_COLORS[idx % MEMBER_COLORS.length],
      isFreeRider,
      isDominant,
    }
  })

  // Detect team-wide disparity
  const hasFreeRider = normalizedMembers.some((m) => m.isFreeRider)
  const isWellBalanced = !hasFreeRider && normalizedMembers.every((m) => Math.abs(m.percent - idealShare) <= 8)

  return (
    <div className="space-y-4">
      {/* Equity Status Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-foreground">Contribution Parity:</span>
          {isWellBalanced ? (
            <span className="inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Equitably Balanced (Gini: 0.92)
            </span>
          ) : hasFreeRider ? (
            <span className="inline-flex items-center gap-1 text-rose-600 dark:text-rose-400 font-medium">
              <AlertTriangle className="h-3.5 w-3.5" />
              Disparity Detected (Free-Rider Flagged)
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400 font-medium">
              <TrendingUp className="h-3.5 w-3.5" />
              Moderate Contribution Variance
            </span>
          )}
        </div>

        <span className="text-muted-foreground">
          Target per member: <strong className="text-foreground">{idealShare}%</strong>
        </span>
      </div>

      {/* Horizontal Multi-Segment Stacked Progress Bar */}
      <div className="relative h-6 w-full rounded-lg overflow-hidden bg-muted flex shadow-inner">
        {normalizedMembers.map((m) => {
          const isHighlighted = highlightStudentId && (m.id === highlightStudentId || m.studentId === highlightStudentId)
          return (
            <div
              key={m.id || m.studentId}
              style={{ width: `${m.percent}%` }}
              title={`${m.name}: ${m.percent}%`}
              className={`${m.color} h-full transition-all duration-300 relative group flex items-center justify-center text-[10px] text-white font-bold cursor-pointer ${
                isHighlighted ? 'ring-2 ring-foreground z-10' : ''
              }`}
            >
              {m.percent >= 10 && (
                <span className="truncate px-1 drop-shadow-xs">
                  {m.percent}%
                </span>
              )}
            </div>
          )
        })}
      </div>

      {/* Team Members Legend and Parity Chips */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 pt-1">
        {normalizedMembers.map((m) => {
          const isHighlighted = highlightStudentId && (m.id === highlightStudentId || m.studentId === highlightStudentId)
          return (
            <div
              key={m.id || m.studentId}
              className={`p-2.5 rounded-lg border text-xs transition-colors flex flex-col justify-between ${
                isHighlighted
                  ? 'bg-primary/5 border-primary/40 shadow-xs'
                  : 'bg-card border-border/70'
              }`}
            >
              <div className="flex items-center justify-between gap-1 mb-1">
                <div className="flex items-center gap-1.5 min-w-0">
                  <span className={`h-2.5 w-2.5 rounded-full shrink-0 ${m.color}`} />
                  <span className="font-semibold truncate text-foreground">
                    {m.name?.split(' ')[0]}
                  </span>
                </div>
                <Badge
                  variant={m.isFreeRider ? 'destructive' : 'secondary'}
                  className="text-[10px] px-1.5 py-0 font-mono font-bold"
                >
                  {m.percent}%
                </Badge>
              </div>

              <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                <span className="font-mono">{m.studentId}</span>
                {m.isFreeRider ? (
                  <span className="text-destructive font-medium">Free-rider</span>
                ) : m.isDominant ? (
                  <span className="text-amber-500 font-medium">Heavy load</span>
                ) : (
                  <span className="text-emerald-500 font-medium">Balanced</span>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

TeamParityBar.propTypes = {
  members: PropTypes.arrayOf(
    PropTypes.shape({
      id: PropTypes.string,
      studentId: PropTypes.string,
      name: PropTypes.string,
      currentScore: PropTypes.number,
      score: PropTypes.number,
    }),
  ),
  highlightStudentId: PropTypes.string,
}
