import PropTypes from 'prop-types'
import { Check, GraduationCap, Presentation } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Checkbox } from '@/components/ui/checkbox'
import { cn } from '@/lib/utils'
import FormField from '../../components/FormField.jsx'

const ACCOUNT_TYPES = [
  {
    value: 'student',
    label: 'Student',
    description: 'Join a team and work on its project.',
    icon: GraduationCap,
  },
  {
    value: 'lecturer',
    label: 'Lecturer',
    description: 'Create teams and follow their progress.',
    icon: Presentation,
  },
]

export function AccountTypeStep({ value, onChange }) {
  return (
    <div role="radiogroup" aria-label="Account type" className="grid gap-3">
      {ACCOUNT_TYPES.map(({ value: option, label, description, icon: Icon }) => {
        const selected = value === option
        return (
          <button
            key={option}
            type="button"
            role="radio"
            aria-checked={selected}
            onClick={() => onChange(option)}
            className={cn(
              'flex cursor-pointer items-center gap-4 rounded-xl border bg-card p-4 text-left shadow-xs outline-none transition-all',
              'focus-visible:ring-2 focus-visible:ring-ring',
              selected
                ? 'border-primary bg-primary/5 ring-1 ring-primary'
                : 'border-border hover:border-primary/40 hover:bg-muted/40',
            )}
          >
            <span
              className={cn(
                'flex h-12 w-12 shrink-0 items-center justify-center rounded-lg transition-colors',
                selected ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground',
              )}
            >
              <Icon className="h-6 w-6" aria-hidden="true" />
            </span>
            <span className="flex-1">
              <span className="block font-semibold text-foreground">{label}</span>
              <span className="mt-0.5 block text-sm text-muted-foreground">{description}</span>
            </span>
            <span
              className={cn(
                'flex h-5 w-5 shrink-0 items-center justify-center rounded-full border transition-colors',
                selected ? 'border-primary bg-primary text-primary-foreground' : 'border-input',
              )}
              aria-hidden="true"
            >
              {selected && <Check className="h-3 w-3" />}
            </span>
          </button>
        )
      })}
    </div>
  )
}

AccountTypeStep.propTypes = {
  value: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
}

export function DetailsStep({ accountType, values, errors, onChange }) {
  const field = (name) => ({
    value: values[name],
    onChange: (event) => onChange(name, event.target.value),
  })

  return (
    <div className="grid gap-4">
      <FormField label="Full name" error={errors.displayName}>
        {(props) => <Input {...props} {...field('displayName')} autoComplete="name" autoFocus />}
      </FormField>
      <FormField label="Institution" optional hint="Your university or school.">
        {(props) => <Input {...props} {...field('institution')} autoComplete="organization" />}
      </FormField>

      {accountType === 'student' ? (
        <>
          <FormField
            label="GitHub username"
            error={errors.githubUsername}
            hint="Used to match commits to you."
          >
            {(props) => (
              <Input {...props} {...field('githubUsername')} autoCapitalize="none" spellCheck={false} />
            )}
          </FormField>
          <FormField label="Student number" optional error={errors.studentNumber}>
            {(props) => <Input {...props} {...field('studentNumber')} />}
          </FormField>
        </>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Department" optional>
            {(props) => <Input {...props} {...field('department')} />}
          </FormField>
          <FormField label="Title" optional>
            {(props) => <Input {...props} {...field('title')} placeholder="Senior Lecturer" />}
          </FormField>
        </div>
      )}
    </div>
  )
}

DetailsStep.propTypes = {
  accountType: PropTypes.string.isRequired,
  values: PropTypes.object.isRequired,
  errors: PropTypes.object.isRequired,
  onChange: PropTypes.func.isRequired,
}

const USES = [
  ['What', 'Commits, tasks and messages in your team projects.'],
  ['Who sees it', 'Your team and its lecturers.'],
  ['Why', 'To give feedback and to support assessment.'],
]

export function ReviewStep({ accountType, values, accepted, onAcceptedChange, error }) {
  const rows = [
    ['Account type', accountType === 'student' ? 'Student' : 'Lecturer'],
    ['Name', values.displayName],
    ['Institution', values.institution],
    ...(accountType === 'student'
      ? [
          ['GitHub', values.githubUsername],
          ['Student number', values.studentNumber],
        ]
      : [
          ['Department', values.department],
          ['Title', values.title],
        ]),
  ].filter(([, value]) => value)

  return (
    <div className="grid gap-5">
      <dl className="divide-y divide-border rounded-lg border border-border text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-4 px-3 py-2">
            <dt className="text-muted-foreground">{label}</dt>
            <dd className="text-right font-medium text-foreground">{value}</dd>
          </div>
        ))}
      </dl>

      <div>
        <h3 className="text-sm font-medium text-foreground">How SELVIA uses your information</h3>
        <dl className="mt-2 grid gap-1 text-sm">
          {USES.map(([term, text]) => (
            <div key={term} className="flex gap-2">
              <dt className="w-20 shrink-0 text-muted-foreground">{term}</dt>
              <dd className="text-foreground">{text}</dd>
            </div>
          ))}
        </dl>
      </div>

      <label className="flex cursor-pointer items-start gap-2.5 text-sm">
        <Checkbox
          checked={accepted}
          onCheckedChange={(checked) => onAcceptedChange(checked === true)}
          className="mt-0.5"
        />
        <span>I understand and agree to this.</span>
      </label>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}

ReviewStep.propTypes = {
  accountType: PropTypes.string.isRequired,
  values: PropTypes.object.isRequired,
  accepted: PropTypes.bool.isRequired,
  onAcceptedChange: PropTypes.func.isRequired,
  error: PropTypes.string,
}
