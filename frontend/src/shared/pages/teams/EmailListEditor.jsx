import { useState } from 'react'
import PropTypes from 'prop-types'
import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import FormField from '../../components/FormField.jsx'
import Badge from '../../components/Badge.jsx'
import { parseEmails } from '../../utils/emails.js'

/**
 * Collects email addresses: paste or type several (separated by lines, commas or spaces), press
 * Add, and they become a list that can be trimmed. With `leader`, one student can be marked as
 * the team leader.
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

  const add = () => {
    const parsed = parseEmails(draft)
    setInvalid(parsed.invalid)
    onChange([...emails, ...parsed.valid.filter((email) => !emails.includes(email))])
    setDraft(parsed.invalid.join('\n'))
  }

  const onKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      add()
    }
  }

  return (
    <div className="grid gap-3">
      <FormField
        label={label}
        hint={hint}
        optional={optional}
        error={invalid.length ? `Not an email address: ${invalid.join(', ')}` : undefined}
      >
        {(props) => (
          <div className="flex items-start gap-2">
            <Textarea
              {...props}
              rows={2}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={onKeyDown}
              placeholder="name@example.com"
              className="min-h-0 resize-none"
            />
            <Button type="button" variant="outline" onClick={add} disabled={!draft.trim()}>
              Add
            </Button>
          </div>
        )}
      </FormField>

      {emails.length > 0 && (
        <ul className="divide-y divide-border rounded-lg border border-border text-sm">
          {emails.map((email) => (
            <li key={email} className="flex items-center justify-between gap-2 px-3 py-1.5">
              <span className="truncate">{email}</span>
              <span className="flex shrink-0 items-center gap-1">
                {onLeaderChange &&
                  (email === leader ? (
                    <Badge tone="primary">Leader</Badge>
                  ) : (
                    <Button
                      type="button"
                      variant="ghost"
                      size="xs"
                      onClick={() => onLeaderChange(email)}
                    >
                      Make leader
                    </Button>
                  ))}
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-xs"
                  aria-label={`Remove ${email}`}
                  onClick={() => onChange(emails.filter((other) => other !== email))}
                >
                  <X aria-hidden="true" />
                </Button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
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
