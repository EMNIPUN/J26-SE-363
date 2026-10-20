import { useState } from 'react'
import PropTypes from 'prop-types'
import { useAvatarImage } from '@/shared/hooks/useAvatarImage.js'
import Badge from '@/shared/components/Badge.jsx'
import { band, factorState, initials, markBand, markText, rangeText, RESULT_STATUS, RUN_STATUS, score100, styleOf } from './format.js'

/** A round gauge for the mark (0 to 100), with the plausible range under it. */
export function ScoreRing({ mark, interval, size = 132, label = 'predicted mark' }) {
  const r = (size - 14) / 2
  const c = 2 * Math.PI * r
  const pct = mark == null ? 0 : Math.max(0, Math.min(100, mark)) / 100
  const color = styleOf(markBand(mark)).ring
  return (
    <div className="relative inline-flex flex-col items-center" style={{ width: size }}>
      <svg width={size} height={size} role="img" aria-label={mark == null ? 'No mark' : `Mark ${markText(mark)} out of 100`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="currentColor" strokeOpacity="0.12" strokeWidth="9" />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="9" strokeLinecap="round" strokeDasharray={`${c * pct} ${c}`} transform={`rotate(-90 ${size / 2} ${size / 2})`} style={{ transition: 'stroke-dasharray 0.6s ease' }} />
      </svg>
      <div className="absolute inset-x-0 top-0 flex flex-col items-center justify-center" style={{ height: size }}>
        <span className="text-3xl font-bold tabular-nums leading-none text-foreground">{markText(mark)}</span>
        <span className="mt-1 text-[11px] uppercase tracking-wide text-muted-foreground">out of 100</span>
      </div>
      <p className="mt-1 text-center text-xs text-muted-foreground">{interval ? `likely ${rangeText(interval)}` : label}</p>
    </div>
  )
}
ScoreRing.propTypes = { mark: PropTypes.number, interval: PropTypes.array, size: PropTypes.number, label: PropTypes.string }

/** A 0 to 1 bar with the plausible range drawn as a lighter stretch. Hatched while the sprint is still running. */
const SHORT = { unavailable: 'n/a', pending: 'pending', failed: 'failed', missing: '-' }

export function FactorBar({ result, height = 8, compact = false }) {
  const state = factorState(result)
  if (state.kind !== 'scored') {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground" title={state.label}>
        <span className="h-2 w-full rounded-full border border-dashed border-muted-foreground/30" />
        <span className="shrink-0">{compact ? SHORT[state.kind] : state.label}</span>
      </div>
    )
  }
  const s = result.score
  const st = styleOf(band(s))
  const [lo, hi] = result.interval || [s, s]
  return (
    <div className="flex items-center gap-3">
      <div className="relative w-full rounded-full bg-muted" style={{ height }} title={result.interval ? `likely between ${score100(lo)} and ${score100(hi)}` : undefined}>
        {result.interval && <div className={`absolute top-0 h-full rounded-full opacity-25 ${st.bar}`} style={{ left: `${lo * 100}%`, width: `${Math.max(1, (hi - lo) * 100)}%` }} />}
        <div className={`absolute left-0 top-0 h-full rounded-full ${st.bar}`} style={{ width: `${Math.max(2, s * 100)}%`, backgroundImage: result.provisional ? 'repeating-linear-gradient(45deg, rgba(255,255,255,.35) 0 4px, transparent 4px 8px)' : undefined }} />
      </div>
      <span className={`w-8 shrink-0 text-right text-sm font-semibold tabular-nums ${st.text}`}>{score100(s)}</span>
    </div>
  )
}
FactorBar.propTypes = { result: PropTypes.object, height: PropTypes.number, compact: PropTypes.bool }

export function StatusPill({ status }) {
  const s = RESULT_STATUS[status] || { label: status, tone: 'neutral' }
  return <Badge tone={s.tone} title={s.help}>{s.label}</Badge>
}
StatusPill.propTypes = { status: PropTypes.string }

export function RunPill({ status }) {
  const s = RUN_STATUS[status] || { label: status, tone: 'neutral' }
  return <Badge tone={s.tone}>{status === 'running' && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />}{s.label}</Badge>
}
RunPill.propTypes = { status: PropTypes.string }

function Photo({ src, size }) {
  const [broken, setBroken] = useState(false)
  if (broken) return null
  return <img src={src} alt="" referrerPolicy="no-referrer" onError={() => setBroken(true)} className="absolute inset-0 h-full w-full rounded-full object-cover" style={{ width: size, height: size }} />
}
Photo.propTypes = { src: PropTypes.string, size: PropTypes.number }

/** A person's profile photo; their coloured initials show while it loads, and when they have no photo or it cannot be shown. */
export function Avatar({ name, size = 36, picture = null }) {
  const fromApi = useAvatarImage(picture)
  const src = typeof picture === 'string' && picture.startsWith('/') ? fromApi : picture
  const hue = [...String(name || '?')].reduce((a, c) => a + c.charCodeAt(0), 0) % 360
  return (
    <span className="relative inline-flex shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white ring-1 ring-black/5" style={{ width: size, height: size, background: `hsl(${hue} 55% 48%)`, fontSize: Math.max(9, size * 0.36) }} aria-hidden="true">
      {initials(name)}
      {src && <Photo key={src} src={src} size={size} />}
    </span>
  )
}
Avatar.propTypes = { name: PropTypes.string, size: PropTypes.number, picture: PropTypes.string }

/** One thin stacked bar: how the mark is made up. Each part is weight x score. */
export function ContributionBar({ parts }) {
  if (!parts.length) return null
  const total = parts.reduce((a, p) => a + p.points, 0) || 1
  const colors = ['#6366f1', '#0ea5e9', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6']
  return (
    <div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-muted">
        {parts.map((p, i) => <div key={p.id} style={{ width: `${(p.points / 100) * 100}%`, background: colors[i % colors.length] }} title={`${p.label}: ${p.points.toFixed(1)} points`} />)}
      </div>
      <ul className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground @xl:grid-cols-3">
        {parts.map((p, i) => (
          <li key={p.id} className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ background: colors[i % colors.length] }} />
            <span className="truncate">{p.label}</span>
            <span className="ml-auto tabular-nums text-foreground">{p.points.toFixed(0)}</span>
          </li>
        ))}
      </ul>
      <p className="mt-1 text-[11px] text-muted-foreground">Points each factor adds ({Math.round(total)} before the pattern adjustment). Weights are shared out when a factor cannot be measured.</p>
    </div>
  )
}
ContributionBar.propTypes = { parts: PropTypes.array }

