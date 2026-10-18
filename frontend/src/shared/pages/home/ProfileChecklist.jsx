import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { Check } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { profileChecklist } from '../../utils/teams.js'

/** What is still missing from the profile. Gone once everything is filled in. */
export default function ProfileChecklist({ account, role }) {
  const items = profileChecklist(account, role)
  const open = items.filter((item) => !item.done)
  if (open.length === 0) return null

  return (
    <Card className="gap-0 p-0">
      <h2 className="flex items-center justify-between border-b border-border px-4 py-3 text-sm font-semibold text-foreground">
        Complete your profile
        <span className="font-normal text-muted-foreground">
          {items.length - open.length} of {items.length}
        </span>
      </h2>
      <ul className="divide-y divide-border">
        {items.map(({ key, label, done, to }) => (
          <li key={key} className="flex items-center gap-3 px-4 py-2.5 text-sm">
            <span
              className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${
                done ? 'border-primary bg-primary text-primary-foreground' : 'border-input'
              }`}
              aria-hidden="true"
            >
              {done && <Check className="h-3 w-3" />}
            </span>
            {done ? (
              <span className="text-muted-foreground line-through">{label}</span>
            ) : (
              <Link to={to} className="font-medium text-primary hover:underline">
                {label}
              </Link>
            )}
          </li>
        ))}
      </ul>
    </Card>
  )
}

ProfileChecklist.propTypes = {
  account: PropTypes.object.isRequired,
  role: PropTypes.string,
}
