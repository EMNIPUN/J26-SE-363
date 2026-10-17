import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { Check } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import Avatar from '../../components/Avatar.jsx'
import { getRoleLabel } from '../../constants/roles.js'

/** What a lecturer does first, ticked from what already exists. Hidden once all is done. */
export function NextSteps({ teams }) {
  const steps = [
    { label: 'Create your first team', done: teams.length > 0, to: '/teams/new' },
    {
      label: 'Invite students',
      done: teams.some((team) => team.student_count > 0 || (team.pending_invitations ?? 0) > 0),
    },
    { label: 'Link a repository', done: teams.some((team) => team.repo_url) },
  ]
  if (steps.every((step) => step.done)) return null

  return (
    <Card className="gap-0 p-0">
      <h2 className="border-b border-border px-4 py-3 text-sm font-semibold text-foreground">
        Get started
      </h2>
      <ol className="grid gap-3 p-4">
        {steps.map(({ label, done, to }) => (
          <li key={label} className="flex items-center gap-3 text-sm">
            <span
              className={cn(
                'flex h-5 w-5 shrink-0 items-center justify-center rounded-full border',
                done ? 'border-primary bg-primary text-primary-foreground' : 'border-input',
              )}
              aria-hidden="true"
            >
              {done && <Check className="h-3 w-3" />}
            </span>
            {to && !done ? (
              <Link to={to} className="font-medium text-primary hover:underline">
                {label}
              </Link>
            ) : (
              <span className={done ? 'text-muted-foreground line-through' : 'text-foreground'}>
                {label}
              </span>
            )}
          </li>
        ))}
      </ol>
    </Card>
  )
}

NextSteps.propTypes = { teams: PropTypes.arrayOf(PropTypes.object).isRequired }

/** Who the person is signed in as, with a way to change it. */
export function ProfileCard({ user, profile }) {
  const details = [
    profile?.institution,
    profile?.department,
    profile?.github_username && `@${profile.github_username}`,
  ].filter(Boolean)

  return (
    <Card className="gap-0 p-0">
      <div className="flex items-center gap-3 p-4">
        <Avatar name={user.name} size={40} />
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-foreground">{user.name}</p>
          <p className="truncate text-xs text-muted-foreground">{user.email}</p>
        </div>
      </div>
      <div className="grid gap-1 border-t border-border px-4 py-3 text-sm">
        <p className="font-medium text-foreground">{getRoleLabel(user.role)}</p>
        {details.map((detail) => (
          <p key={detail} className="truncate text-muted-foreground">
            {detail}
          </p>
        ))}
      </div>
      <div className="border-t border-border px-4 py-2.5">
        <Link to="/profile" className="text-sm font-medium text-primary hover:underline">
          Edit profile
        </Link>
      </div>
    </Card>
  )
}

ProfileCard.propTypes = {
  user: PropTypes.shape({
    name: PropTypes.string,
    email: PropTypes.string,
    role: PropTypes.string,
  }).isRequired,
  profile: PropTypes.object,
}
