const RADIUS = 18
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

export default function ConfidenceIndicator({ value }) {
  const clamped = Math.min(100, Math.max(0, value))
  const offset = CIRCUMFERENCE * (1 - clamped / 100)

  return (
    <div className="flex items-center gap-3">
      <div className="relative h-12 w-12 shrink-0">
        <svg viewBox="0 0 44 44" className="h-12 w-12 -rotate-90" aria-hidden="true">
          <circle cx="22" cy="22" r={RADIUS} fill="none" strokeWidth="4" className="stroke-muted" />
          <circle
            cx="22"
            cy="22"
            r={RADIUS}
            fill="none"
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={offset}
            className="stroke-primary transition-[stroke-dashoffset] duration-500 ease-out"
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-xs font-semibold tabular-nums text-foreground">
          {clamped}%
        </span>
      </div>
      <div className="min-w-0">
        <p className="text-sm font-semibold text-foreground">Confidence</p>
        <p className="text-[11px] leading-snug text-muted-foreground">How certain the Tutor is about these estimates</p>
      </div>
    </div>
  )
}
