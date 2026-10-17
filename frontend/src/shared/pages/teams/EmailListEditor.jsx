import { useState } from 'react'
import PropTypes from 'prop-types'
import { Crown, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import FormField from '../../components/FormField.jsx'
import { parseEmails } from '../../utils/emails.js'

const SEPARATORS = [' ', ',', ';', 'Enter']

/**
 * Collects email addresses as chips. Type or paste addresses: a space, comma, semicolon or Enter
 * turns what was typed into a chip, Backspace on an empty field removes the last one. Something
 * that is not an address stays in the field with a message. With `onLeaderChange`, one chip can
 * be marked as the team leader.
 */
export default function EmailListEditor({
  label,
  hint,
  emails,
  onChange,
  leader,
  onLeaderChange,
  optional = false,
}) {
  const [draft, setDraft] = useState('')
  const [invalid, setInvalid] = useState([])

  // Turns the addresses in `text` into chips and keeps the rest in the field.
  const commit = (text) => {
    const parsed = parseEmails(text)
    setInvalid(parsed.invalid)
    setDraft(parsed.invalid.join(' '))
    const fresh = parsed.valid.filter((email) => !emails.includes(email))
    if (fresh.length) onChange([...emails, ...fresh])
  }

  const onKeyDown = (event) => {
    if (SEPARATORS.includes(event.key) && draft.trim()) {
      event.preventDefault()
      commit(draft)
    } else if (event.key === 'Enter') {
      event.preventDefault() // an empty Enter must not submit the whole form
    } else if (event.key === 'Backspace' && !draft && emails.length) {
      onChange(emails.slice(0, -1))
    }
  }

  const onPaste = (event) => {
    event.preventDefault()
    commit(`${draft} ${event.clipboardData.getData('text')}`)
  }

  const remove = (email) => onChange(emails.filter((other) => other !== email))

  return (
    <FormField
      label={label}
      hint={hint}
      optional={optional}
      error={invalid.length ? `Not an email address: ${invalid.join(', ')}` : undefined}
    >
      {(props) => (
        <div
          className={cn(
            'flex min-h-10 flex-wrap items-center gap-1.5 rounded-md border border-input bg-transparent px-2 py-1.5 shadow-xs transition-[color,box-shadow]',
            'focus-within:border-ring focus-within:ring-[3px] focus-within:ring-ring/50',
            invalid.length > 0 && 'border-destructive',
          )}
        >
          {emails.map((email) => {
            const isLeader = email === leader
            return (
              <span
                key={email}
                className={cn(
                  'group flex max-w-full items-center gap-1 rounded-md border py-0.5 pl-2 pr-1 text-sm',
                  isLeader
                    ? 'border-primary/30 bg-primary/10 text-primary'
                    : 'border-border bg-muted text-foreground',
                )}
              >
                <span className="truncate">{email}</span>
                {onLeaderChange &&
                  (isLeader ? (
                    <Crown
                      className="h-3.5 w-3.5"
                      aria-label="Team leader"
                      role="img"
                    />
                  ) : (
                    <button
                      type="button"
                      onClick={() => onLeaderChange(email)}
                      aria-label={`Make ${email} the leader`}
                      title="Make leader"
                      className="flex h-5 w-5 cursor-pointer items-center justify-center rounded text-muted-foreground opacity-0 outline-none hover:bg-background hover:text-foreground focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-ring group-hover:opacity-100"
                    >
                      <Crown className="h-3.5 w-3.5" aria-hidden="true" />
                    </button>
                  ))}
                <button
                  type="button"
                  onClick={() => remove(email)}
                  aria-label={`Remove ${email}`}
                  className="flex h-5 w-5 cursor-pointer items-center justify-center rounded text-muted-foreground outline-none hover:bg-background hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <X className="h-3.5 w-3.5" aria-hidden="true" />
                </button>
              </span>
            )
          })}
          <input
            {...props}
            type="text"
            inputMode="email"
            autoCapitalize="none"
            spellCheck={false}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onKeyDown}
            onPaste={onPaste}
            onBlur={() => draft.trim() && commit(draft)}
            placeholder={emails.length ? '' : 'name@example.com'}
            className="min-w-40 flex-1 bg-transparent py-0.5 text-sm outline-none placeholder:text-muted-foreground"
          />
        </div>
      )}
    </FormField>
  )
}

EmailListEditor.propTypes = {
  label: PropTypes.string.isRequired,
  hint: PropTypes.string,
  emails: PropTypes.arrayOf(PropTypes.string).isRequired,
  onChange: PropTypes.func.isRequired,
  leader: PropTypes.string,
  onLeaderChange: PropTypes.func,
  optional: PropTypes.bool,
}
