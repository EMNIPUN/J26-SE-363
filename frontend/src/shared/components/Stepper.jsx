import PropTypes from 'prop-types'
import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'

/** Numbered steps for multi-step forms. `current` is the index of the step being filled in. */
export default function Stepper({ steps, current }) {
  return (
    <ol className="flex items-center gap-2" aria-label="Progress">
      {steps.map((label, index) => {
        const done = index < current
        const active = index === current
        return (
          <li
            key={label}
            className="flex flex-1 items-center gap-2 last:flex-none"
            aria-current={active ? 'step' : undefined}
          >
            <span
              className={cn(
                'flex h-6 w-6 shrink-0 items-center justify-center rounded-full border text-xs font-semibold',
                done && 'border-primary bg-primary text-primary-foreground',
                active && 'border-primary text-primary',
                !done && !active && 'border-border text-muted-foreground',
              )}
            >
              {done ? <Check className="h-3.5 w-3.5" aria-hidden="true" /> : index + 1}
            </span>
            <span
              className={cn(
                'text-sm',
                active ? 'font-medium text-foreground' : 'hidden text-muted-foreground sm:inline',
              )}
            >
              {label}
            </span>
            {index < steps.length - 1 && (
              <span className={cn('h-px flex-1', done ? 'bg-primary' : 'bg-border')} aria-hidden="true" />
            )}
          </li>
        )
      })}
    </ol>
  )
}

Stepper.propTypes = {
  steps: PropTypes.arrayOf(PropTypes.string).isRequired,
  current: PropTypes.number.isRequired,
}
