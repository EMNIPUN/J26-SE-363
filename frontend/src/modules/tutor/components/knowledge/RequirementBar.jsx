import { cn } from '@/lib/utils'

const toPercent = (value) => `${Math.min(100, Math.max(0, value))}%`

// Fill = current competency; vertical marker = level required by the task.
export default function RequirementBar({ label, current, required, barClass = 'bg-primary', className }) {
  return (
    <div
      role="img"
      aria-label={`${label}: current ${current}%, required ${required}%`}
      className={cn('relative py-1.5', className)}
    >
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <div
          className={cn('h-full rounded-full transition-[width] duration-500 ease-out', barClass)}
          style={{ width: toPercent(current) }}
        />
      </div>
      <span
        aria-hidden="true"
        className="absolute top-0 h-5 w-0.5 -translate-x-1/2 rounded-full bg-foreground/70"
        style={{ left: toPercent(required) }}
      />
    </div>
  )
}
