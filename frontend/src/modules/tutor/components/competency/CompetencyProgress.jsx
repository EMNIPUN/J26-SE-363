const toPercent = (value) => `${Math.min(100, Math.max(0, value))}%`

export default function CompetencyProgress({ name, score, className }) {
  return (
    <div className={className}>
      <div className="mb-1.5 flex items-baseline justify-between gap-2 text-sm">
        <span className="truncate text-foreground">{name}</span>
        <span className="shrink-0 text-xs font-semibold tabular-nums text-foreground">{score}%</span>
      </div>
      <div
        role="progressbar"
        aria-label={`${name} competency`}
        aria-valuenow={score}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-1.5 overflow-hidden rounded-full bg-muted"
      >
        <div
          className="h-full rounded-full bg-primary transition-[width] duration-500 ease-out"
          style={{ width: toPercent(score) }}
        />
      </div>
    </div>
  )
}
