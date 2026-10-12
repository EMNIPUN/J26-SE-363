import { useState, useMemo } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  Users2,
  Award,
  AlertTriangle,
  Sparkles,
  GitPullRequest,
  GitCommit,
  ExternalLink,
  ChevronRight,
} from 'lucide-react'
import { useScope } from '@/shared/context/useScope.js'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import TeamParityBar from '../../components/TeamParityBar.jsx'
import EmptyState from '@/shared/components/EmptyState.jsx'

function needsLook(student) {
  return student.riskLevel === 'High' || student.riskLevel === 'Critical' || student.riskProbability >= 0.5
}

export default function InstructorDashboard() {
  const { teamId } = useParams()
  const { selectedGroup, teamStudents } = useScope()
  const [filterRisk, setFilterRisk] = useState('all')

  const teamCode = selectedGroup?.code || teamId || 'J26-SE-363'

  // Summary statistics
  const stats = useMemo(() => {
    const scored = teamStudents.filter((student) => typeof student.currentScore === 'number')
    const explained = teamStudents.filter((student) => typeof student.comprehensionRate === 'number')
    const avgScore = scored.length
      ? (scored.reduce((sum, student) => sum + student.currentScore, 0) / scored.length).toFixed(1)
      : null
    const avgComprehension = explained.length
      ? Math.round(explained.reduce((sum, student) => sum + student.comprehensionRate, 0) / explained.length)
      : null

    return {
      avgScore,
      atRiskCount: teamStudents.filter(needsLook).length,
      avgComprehension,
    }
  }, [teamStudents])

  const displayedStudents = useMemo(() => {
    const list = filterRisk === 'atRisk' ? teamStudents.filter(needsLook) : teamStudents
    return [...list].sort((a, b) => (b.riskProbability || 0) - (a.riskProbability || 0))
  }, [teamStudents, filterRisk])

  return (
    <div className="space-y-6 animate-fade-rise">
      {/* Supervised Team Overview Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="text-xs font-mono font-bold text-primary border-primary/30">
              {selectedGroup?.code}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {selectedGroup?.name}
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            {selectedGroup?.projectTitle || 'Research Project Dashboard'}
          </h1>
          <p className="text-sm text-muted-foreground">
            Commits, reviews, and stand-ups are observed. Risk labels are inferred. Students do not see this page as a ranking.
          </p>
        </div>

        {selectedGroup?.repositoryUrl && (
          <a
            href={selectedGroup.repositoryUrl}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-card border border-border text-xs text-muted-foreground hover:text-foreground hover:border-foreground/40 transition-colors shadow-2xs"
          >
            <span>Repository</span>
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        )}
      </div>

      {/* Top 4 KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: Group Average AHP Score */}
        <Card className="p-4 bg-card border-border shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>Recorded score average</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Award className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">
              {stats.avgScore ?? '—'}
            </span>
            <span className="text-xs text-muted-foreground font-mono">/ 10</span>
            <Badge className="ml-auto text-xs bg-primary/10 text-primary border-primary/20">
              Observed
            </Badge>
          </div>
        </Card>

        {/* Metric 2: At-Risk Students Flagged */}
        <Card className="p-4 bg-card border-border shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>Inferred signals to check</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-amber-500/10 text-amber-500">
              <AlertTriangle className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className={`text-2xl font-bold ${stats.atRiskCount > 0 ? 'text-amber-500' : 'text-emerald-500'}`}>
              {stats.atRiskCount}
            </span>
            <span className="text-xs text-muted-foreground">of {teamStudents.length} members</span>
            <Badge
              variant="outline"
              className={`ml-auto text-[10px] ${
                stats.atRiskCount > 0
                  ? 'bg-amber-500/10 text-amber-500 border-amber-500/30'
                  : 'bg-emerald-500/10 text-emerald-500 border-emerald-500/30'
              }`}
            >
              {stats.atRiskCount > 0 ? 'Inferred' : 'None on record'}
            </Badge>
          </div>
        </Card>

        {/* Metric 3: Contribution Parity Gini Index */}
        <Card className="p-4 bg-card border-border shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>Students on this team</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Users2 className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">
              {teamStudents.length}
            </span>
            <span className="text-xs text-muted-foreground">with a profile</span>
            <Badge variant="outline" className="ml-auto text-xs text-primary border-primary/30">
              This team
            </Badge>
          </div>
        </Card>

        {/* Metric 4: Oral Viva Comprehension Rate */}
        <Card className="p-4 bg-card border-border shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>Explanation scores on record</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Sparkles className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">
              {stats.avgComprehension != null ? `${stats.avgComprehension}%` : '—'}
            </span>
            <Badge variant="outline" className="ml-auto text-xs bg-primary/10 text-primary border-primary/30">
              Observed
            </Badge>
          </div>
        </Card>
      </div>

      {/* Team Contribution Parity (Fair Share Visualizer) */}
      <Card className="p-5 bg-card border-border shadow-xs space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-foreground">
            Contribution balance
          </h3>
          <p className="text-sm text-muted-foreground">
            Shares use the recorded scores for {selectedGroup?.code}. An uneven bar is a prompt to look, not a finding by itself.
          </p>
        </div>

        <TeamParityBar members={teamStudents} />
      </Card>

      {/* Student Roster Cards */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-foreground">
              People on this team
            </h3>
            <p className="text-sm text-muted-foreground">
              Open a person to see what is stored. A missing factor chart means it was not copied from someone else.
            </p>
          </div>

          <div className="flex items-center gap-1.5 text-xs">
            <Button
              variant={filterRisk === 'all' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilterRisk('all')}
              className="h-7 text-xs cursor-pointer"
            >
              All Members ({teamStudents.length})
            </Button>
            <Button
              variant={filterRisk === 'atRisk' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setFilterRisk('atRisk')}
              className="h-7 text-xs cursor-pointer"
            >
              Needs a look ({stats.atRiskCount})
            </Button>
          </div>
        </div>

        {displayedStudents.length === 0 ? (
          <EmptyState
            title="No one in this filter"
            description="Everyone on the selected team is below the inferred check-in line, or this team has no profiles yet."
          />
        ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {displayedStudents.map((student) => {
            const inferred = needsLook(student)
            return (
              <Card
                key={student.id}
                className="p-4 sm:p-5 bg-card border-border hover:border-primary/40 transition-all duration-200 shadow-xs flex flex-col justify-between"
              >
                <div>
                  {/* Top line: Name & Risk Badge */}
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div>
                      <h4 className="font-semibold text-foreground text-sm">
                        {student.name}
                      </h4>
                      <p className="text-xs text-muted-foreground font-mono">
                        {student.studentId} • {student.assignedComponent || 'Engineering Lead'}
                      </p>
                    </div>

                    <Badge
                      variant={inferred ? 'destructive' : 'secondary'}
                      className={`text-xs font-semibold ${
                        !inferred
                          ? 'bg-primary/10 text-primary border-primary/20'
                          : ''
                      }`}
                    >
                      Inferred · {student.riskLevel || 'Low'}
                    </Badge>
                  </div>

                  {/* Metrics Row */}
                  <div className="grid grid-cols-3 gap-2 py-3 border-y border-border/60 text-xs text-center my-3">
                    <div>
                      <span className="text-xs text-muted-foreground">Recorded score</span>
                      <div className="font-mono font-bold text-sm text-foreground">
                        {typeof student.currentScore === 'number' ? `${student.currentScore}/10` : '—'}
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] text-muted-foreground">Commits</span>
                      <div className="font-mono font-bold text-sm text-foreground flex items-center justify-center gap-1">
                        <GitCommit className="h-3 w-3 text-muted-foreground" />
                        {typeof student.commitsCount === 'number' ? student.commitsCount : '—'}
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] text-muted-foreground">PR Reviews</span>
                      <div className="font-mono font-bold text-sm text-foreground flex items-center justify-center gap-1">
                        <GitPullRequest className="h-3 w-3 text-muted-foreground" />
                        {typeof student.prReviewsCount === 'number' ? student.prReviewsCount : '—'}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Inspect Action */}
                <div className="pt-1 flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">
                    Stand-ups {student.standupAttendance || '—'}
                    {typeof student.comprehensionRate === 'number' ? ` · explanation ${student.comprehensionRate}%` : ''}
                  </span>

                  <Button
                    asChild
                    variant="ghost"
                    size="sm"
                    className="h-8 text-xs text-primary gap-1 cursor-pointer hover:bg-primary/10"
                  >
                    <Link to={`/teams/${teamCode}/performance/students?studentId=${student.id}`}>
                      <span>View evidence</span>
                      <ChevronRight className="h-3.5 w-3.5" />
                    </Link>
                  </Button>
                </div>
              </Card>
            )
          })}
        </div>
        )}
      </div>
    </div>
  )
}
