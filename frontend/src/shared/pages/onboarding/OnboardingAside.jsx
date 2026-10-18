import PropTypes from 'prop-types'
import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'
import SelviaLogo from '../../components/SelviaLogo.jsx'

/**
 * The brand panel beside the onboarding form (wide screens only). It is dark in both themes, like
 * the sign-in page, so the two feel like one flow. The steps are the same ones the form shows.
 */
export default function OnboardingAside({ steps, current }) {
  return (
    <aside className="relative hidden flex-col justify-between overflow-hidden bg-[oklch(0.2_0.06_275)] p-10 text-white lg:flex">
      <div
        aria-hidden="true"
        className="absolute inset-0 bg-[radial-gradient(60rem_40rem_at_0%_0%,oklch(0.5_0.2_280/55%),transparent_60%),radial-gradient(40rem_30rem_at_100%_100%,oklch(0.45_0.18_250/45%),transparent_60%)]"
      />
      <div
        aria-hidden="true"
        className="absolute inset-0 bg-[linear-gradient(oklch(1_0_0/6%)_1px,transparent_1px),linear-gradient(90deg,oklch(1_0_0/6%)_1px,transparent_1px)] bg-size-[3rem_3rem] mask-[linear-gradient(to_bottom,black,transparent_85%)]"
      />

      <SelviaLogo size={32} showText showTagline={false} className="relative" textColorClassName="text-white" />

      <div className="relative">
        <h2 className="mb-8 max-w-sm text-3xl font-semibold leading-tight tracking-tight">
          Set up your account
        </h2>
        <ol className="grid gap-0">
          {steps.map(({ label, hint }, index) => {
            const done = index < current
            const active = index === current
            return (
              <li key={label} className="flex gap-4" aria-current={active ? 'step' : undefined}>
                <div className="flex flex-col items-center">
                  <span
                    className={cn(
                      'flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-sm font-semibold transition-colors',
                      done && 'border-transparent bg-white text-[oklch(0.2_0.06_275)]',
                      active && 'border-white bg-white/15 text-white',
                      !done && !active && 'border-white/25 text-white/50',
                    )}
                  >
                    {done ? <Check className="h-4 w-4" aria-hidden="true" /> : index + 1}
                  </span>
                  {index < steps.length - 1 && (
                    <span
                      className={cn('my-1 w-px flex-1', done ? 'bg-white/60' : 'bg-white/20')}
                      aria-hidden="true"
                    />
                  )}
                </div>
                <div className="pb-8">
                  <p className={cn('text-sm font-medium', active || done ? 'text-white' : 'text-white/55')}>
                    {label}
                  </p>
                  <p className="text-sm text-white/55">{hint}</p>
                </div>
              </li>
            )
          })}
        </ol>
      </div>

      <span aria-hidden="true" />
    </aside>
  )
}

OnboardingAside.propTypes = {
  steps: PropTypes.arrayOf(
    PropTypes.shape({ label: PropTypes.string.isRequired, hint: PropTypes.string.isRequired }),
  ).isRequired,
  current: PropTypes.number.isRequired,
}
