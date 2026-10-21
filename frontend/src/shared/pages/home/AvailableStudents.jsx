import { useState } from 'react'
import PropTypes from 'prop-types'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useAvailableStudents, useInviteToTeam } from '../../hooks/useTeams.js'
import { useTerms } from '../../hooks/useTerms.js'
import { showToast } from '../../utils/toast.jsx'
import Avatar from '../../components/Avatar.jsx'

/**
 * Students of the lecturer's own institution who have no team in a term, to invite in one go.
 * The list has no emails; the invitation is sent by id and the address is looked up by the API.
 */
export default function AvailableStudents({ teams, defaultTerm }) {
  const terms = useTerms()
  const [chosenTerm, setChosenTerm] = useState(null)
  const term = chosenTerm ?? defaultTerm ?? terms.data?.[0] ?? null
  const available = useAvailableStudents(term)
  const [picked, setPicked] = useState([])
  const [chosenTeam, setChosenTeam] = useState('')

  // Teams that are set up come first, so a draft is never the one picked by default.
  const termTeams = teams
    .filter((team) => team.term === term)
    .sort((a, b) => Number(a.status === 'pending') - Number(b.status === 'pending'))
  const targetCode = termTeams.some((team) => team.code === chosenTeam) ? chosenTeam : termTeams[0]?.code
  const target = termTeams.find((team) => team.code === targetCode)
  const invite = useInviteToTeam(targetCode)

  const students = available.data?.students ?? []
  const toggle = (id, on) => setPicked((now) => (on ? [...now, id] : now.filter((other) => other !== id)))
  const changeTerm = (next) => {
    setChosenTerm(next)
    setPicked([])
  }

  const send = () =>
    invite.mutate(
      { student_ids: picked },
      {
        onSuccess: () => {
          const count = picked.length
          setPicked([])
          showToast.success(
            target?.status === 'pending'
              ? `${count} saved. They are invited when you finish setting up ${target.name}.`
              : `${count} invited to ${target?.name}`,
          )
        },
      },
    )

  return (
    <Card className="gap-0 p-0">
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <h2 className="text-sm font-semibold text-foreground">Students without a team</h2>
        {terms.data?.length > 0 && (
          <Select value={term ?? undefined} onValueChange={changeTerm}>
            <SelectTrigger className="h-8 w-32" aria-label="Term">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {terms.data.map((item) => (
                <SelectItem key={item} value={item}>
                  {item}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {available.isSuccess && !available.data.institution && (
        <p className="px-4 py-4 text-sm text-muted-foreground">
          Students are listed by institution.{' '}
          <Link to="/profile" className="font-medium text-primary hover:underline">
            Add yours on your profile
          </Link>{' '}
          to see students from it.
        </p>
      )}
      {available.isSuccess && available.data.institution && students.length === 0 && (
        <p className="px-4 py-4 text-sm text-muted-foreground">
          Every student from {available.data.institution} who has signed up has a team in {term}.
        </p>
      )}
      {!term && <p className="px-4 py-4 text-sm text-muted-foreground">Add a term by creating a team first.</p>}

      {students.length > 0 && (
        <ul className="max-h-72 divide-y divide-border overflow-y-auto">
          {students.map((student) => (
            <li key={student.id}>
              <label className="flex cursor-pointer items-center gap-3 px-4 py-2 hover:bg-muted/40">
                <Checkbox
                  checked={picked.includes(student.id)}
                  onCheckedChange={(on) => toggle(student.id, on === true)}
                />
                <Avatar name={student.name} picture={student.picture} size={28} />
                <span className="min-w-0 flex-1 truncate text-sm font-medium text-foreground">{student.name}</span>
                {student.github_username && (
                  <span className="truncate text-xs text-muted-foreground">@{student.github_username}</span>
                )}
              </label>
            </li>
          ))}
        </ul>
      )}

      {picked.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 border-t border-border px-4 py-3">
          {termTeams.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              You have no team in {term}.{' '}
              <Link to="/teams/new" className="font-medium text-primary hover:underline">
                Create one
              </Link>{' '}
              to invite them.
            </p>
          ) : (
            <>
              <span className="text-sm text-muted-foreground">Invite {picked.length} to</span>
              <Select value={targetCode} onValueChange={setChosenTeam}>
                <SelectTrigger className="h-8 w-44" aria-label="Team">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {termTeams.map((team) => (
                    <SelectItem key={team.id} value={team.code}>
                      {team.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button size="sm" className="ml-auto" loading={invite.isPending} onClick={send}>
                Invite
              </Button>
            </>
          )}
        </div>
      )}
    </Card>
  )
}

AvailableStudents.propTypes = {
  teams: PropTypes.arrayOf(PropTypes.object).isRequired,
  defaultTerm: PropTypes.string,
}
