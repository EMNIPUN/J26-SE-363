import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { Users } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useMyTeams } from '../../hooks/useTeams.js'
import { teamHref } from '../../utils/teams.js'
import EmptyState from '../../components/EmptyState.jsx'
import PageHeader from '../../components/PageHeader.jsx'
import { TeamRoleBadge, TeamStatusBadge } from '../../components/TeamBadges.jsx'

const NO_TERM = 'No term'

/** Every team the person is in, by term, newest first, including past terms. */
export default function MyTeamsPage() {
  const teams = useMyTeams()

  const byTerm = useMemo(() => {
    const groups = new Map()
    for (const team of teams.data ?? []) {
      const key = team.term ?? NO_TERM
      groups.set(key, [...(groups.get(key) ?? []), team])
    }
    return [...groups.entries()].sort(([a], [b]) => b.localeCompare(a))
  }, [teams.data])

  return (
    <div className="grid gap-6">
      <PageHeader title="Teams" description="Every team you have been part of." />

      {teams.isPending && <Skeleton className="h-32 w-full" aria-busy="true" />}
      {teams.isSuccess && teams.data.length === 0 && (
        <EmptyState icon={Users} title="No teams yet" description="Teams you join or create appear here." />
      )}

      {byTerm.map(([term, list]) => (
        <section key={term} className="grid gap-2">
          <h2 className="text-sm font-semibold text-muted-foreground">{term}</h2>
          <Card className="gap-0 divide-y divide-border p-0">
            {list.map((team) => (
              <Link
                key={team.id}
                to={teamHref(team)}
                className="flex items-center gap-3 px-4 py-3 outline-none transition-colors hover:bg-muted/40 focus-visible:bg-muted/40"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">
                    {team.name} <span className="font-mono text-xs font-normal text-muted-foreground">{team.code}</span>
                  </p>
                  <p className="truncate text-sm text-muted-foreground">{team.project?.title ?? 'No project yet'}</p>
                </div>
                <TeamRoleBadge role={team.my_role} />
                <TeamStatusBadge status={team.status} />
              </Link>
            ))}
          </Card>
        </section>
      ))}
    </div>
  )
}
