import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useAuth } from '../../auth/useAuth.js'
import { useMyInvitations, useMyTeams } from '../../hooks/useTeams.js'
import PageHeader from '../../components/PageHeader.jsx'
import TeamList from '../home/TeamList.jsx'

const ALL_TERMS = 'all'

function matches(team, query) {
  const text = [team.name, team.code, team.project?.title, team.term].join(' ').toLowerCase()
  return text.includes(query.toLowerCase())
}

/** Every team the person belongs to, from any term, with a search and a term filter. */
export default function TeamsPage() {
  const { user } = useAuth()
  const canCreate = user.role === 'instructor'
  const isStaff = canCreate || user.role === 'admin'
  const teams = useMyTeams()
  const invitations = useMyInvitations()
  const [query, setQuery] = useState('')
  const [term, setTerm] = useState(ALL_TERMS)

  const terms = useMemo(
    () => [...new Set((teams.data ?? []).map((team) => team.term).filter(Boolean))].sort().reverse(),
    [teams.data],
  )
  const visible = useMemo(
    () =>
      (teams.data ?? []).filter(
        (team) => (term === ALL_TERMS || team.term === term) && matches(team, query.trim()),
      ),
    [teams.data, query, term],
  )
  const hasTeams = (teams.data ?? []).length > 0

  return (
    <div className="grid gap-6">
      <PageHeader
        title="Teams"
        description={isStaff ? 'The teams you supervise.' : 'The teams you are part of.'}
        actions={
          canCreate && (
            <Button asChild>
              <Link to="/teams/new">
                <Plus className="h-4 w-4" aria-hidden="true" />
                Create team
              </Link>
            </Button>
          )
        }
      />

      {hasTeams && (
        <div className="-mt-2 flex flex-wrap items-center gap-3">
          <div className="relative w-full max-w-xs">
            <Search
              className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden="true"
            />
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search teams"
              aria-label="Search teams"
              className="pl-8"
            />
          </div>
          {terms.length > 1 && (
            <Select value={term} onValueChange={setTerm}>
              <SelectTrigger className="w-40" aria-label="Term">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_TERMS}>All terms</SelectItem>
                {terms.map((item) => (
                  <SelectItem key={item} value={item}>
                    {item}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>
      )}

      <TeamList
        teamsQuery={teams}
        visible={visible}
        isStaff={isStaff}
        canCreate={canCreate}
        email={user.email}
        hasInvitations={(invitations.data ?? []).length > 0}
      />
    </div>
  )
}
