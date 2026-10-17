import PropTypes from 'prop-types'
import { FolderGit2, Hourglass, Mail, UsersRound } from 'lucide-react'
import StatCard from '../../components/StatCard.jsx'

const sum = (teams, key) => teams.reduce((total, team) => total + (team[key] ?? 0), 0)

/** A short row of numbers about the person's teams. Lecturers and students see different ones. */
export default function HomeStats({ teams, invitations, isStaff, loading }) {
  const cards = isStaff
    ? [
        { icon: UsersRound, label: 'Teams', value: teams.length },
        { icon: UsersRound, label: 'Students', value: sum(teams, 'student_count'), tone: 'success' },
        { icon: Hourglass, label: 'Awaiting reply', value: sum(teams, 'pending_invitations'), tone: 'warning' },
        {
          icon: FolderGit2,
          label: 'No repository yet',
          value: teams.filter((team) => !team.repo_url).length,
          tone: 'danger',
        },
      ]
    : [
        { icon: UsersRound, label: 'Teams', value: teams.length },
        { icon: Mail, label: 'Invitations', value: invitations, tone: 'warning' },
        {
          icon: FolderGit2,
          label: 'Repositories linked',
          value: teams.filter((team) => team.repo_url).length,
          tone: 'success',
        },
      ]

  return (
    <div className={`grid gap-4 sm:grid-cols-2 ${isStaff ? 'lg:grid-cols-4' : 'lg:grid-cols-3'}`}>
      {cards.map((card) => (
        <StatCard key={card.label} loading={loading} {...card} />
      ))}
    </div>
  )
}

HomeStats.propTypes = {
  teams: PropTypes.arrayOf(PropTypes.object).isRequired,
  invitations: PropTypes.number.isRequired,
  isStaff: PropTypes.bool.isRequired,
  loading: PropTypes.bool,
}
