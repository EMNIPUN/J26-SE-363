import { cn } from '@/lib/utils'

export default function ProgressBar({ value, label, className, barClass = 'bg-primary' }) {
  const clamped = Math.min(100, Math.max(0, value ?? 0))

  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
      className={cn('h-1.5 w-full overflow-hidden rounded-full bg-muted', className)}
    >
      <div className={cn('h-full rounded-full transition-[width] duration-500 ease-out', barClass)} style={{ width: `${clamped}%` }} />
    </div>
  )
}
