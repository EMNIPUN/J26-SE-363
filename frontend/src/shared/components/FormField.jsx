import { useId } from 'react'
import PropTypes from 'prop-types'
import { cn } from '@/lib/utils'

/**
 * A label, one control, an optional hint and an error. Pass a function as `children` to receive
 * the generated `id` and the props that tie the control to its hint and error text.
 */
export default function FormField({ label, hint, error, optional = false, className, children }) {
  const id = useId()
  const describedBy = [hint && `${id}-hint`, error && `${id}-error`].filter(Boolean).join(' ')
  const controlProps = {
    id,
    'aria-invalid': error ? true : undefined,
    'aria-describedby': describedBy || undefined,
  }

  return (
    <div className={cn('grid gap-1.5', className)}>
      <label htmlFor={id} className="flex items-baseline gap-1.5 text-sm font-medium text-foreground">
        {label}
        {optional && <span className="text-xs font-normal text-muted-foreground">Optional</span>}
      </label>
      {typeof children === 'function' ? children(controlProps) : children}
      {hint && !error && (
        <p id={`${id}-hint`} className="text-xs text-muted-foreground">
          {hint}
        </p>
      )}
      {error && (
        <p id={`${id}-error`} role="alert" className="text-xs text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}

FormField.propTypes = {
  label: PropTypes.string.isRequired,
  hint: PropTypes.string,
  error: PropTypes.string,
  optional: PropTypes.bool,
  className: PropTypes.string,
  children: PropTypes.oneOfType([PropTypes.node, PropTypes.func]).isRequired,
}
