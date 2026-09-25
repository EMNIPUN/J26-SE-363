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

export default function InstructorDashboard() {
  const { teamId } = useParams()
  const { selectedGroup, teamStudents } = useScope()
  const [filterRisk, setFilterRisk] = useState('all')

  const teamCode = selectedGroup?.code || teamId || 'J26-SE-363'

  // Summary statistics
  const stats = useMemo(() => {
    const total = teamStudents.length || 1
    const atRiskList = teamStudents.filter(
      (s) => s.riskLevel === 'High' || s.riskLevel === 'Critical' || s.riskProbability > 0.4,
    )
    const avgScore = (
      teamStudents.reduce((sum, s) => sum + (s.currentScore || 8.0), 0) / total
    ).toFixed(1)
    const avgComprehension = Math.round(
      teamStudents.reduce((sum, s) => sum + (s.comprehensionRate || 90), 0) / total,
    )

    return {
      avgScore,
      atRiskCount: atRiskList.length,
      avgComprehension,
      parityIndex: 0.88,
    }
  }, [teamStudents])

  // Filter students if filter selected
  const displayedStudents = useMemo(() => {
    if (filterRisk === 'atRisk') {
      return teamStudents.filter((s) => s.riskProbability >= 0.25 || s.riskLevel !== 'Low')
    }
    return teamStudents
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
          <p className="text-xs text-muted-foreground">
            Continuous individual performance tracking, contribution parity & at-risk detection.
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
            <span>Group AHP Average</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Award className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">
              {stats.avgScore}
            </span>
            <span className="text-xs text-muted-foreground font-mono">/ 10</span>
            <Badge className="ml-auto text-[10px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20">
              Above Benchmark
            </Badge>
          </div>
        </Card>

        {/* Metric 2: At-Risk Students Flagged */}
        <Card className="p-4 bg-card border-border shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>At-Risk Students Flagged</span>
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
              {stats.atRiskCount > 0 ? 'Requires Review' : 'Safe Cohort'}
            </Badge>
          </div>
        </Card>

        {/* Metric 3: Contribution Parity Gini Index */}
        <Card className="p-4 bg-card border-border shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>Contribution Parity (Gini)</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-blue-500/10 text-blue-500">
              <Users2 className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">
              {stats.parityIndex}
            </span>
            <span className="text-xs text-muted-foreground">/ 1.0</span>
            <Badge variant="outline" className="ml-auto text-[10px] text-blue-500 border-blue-500/30">
              Equitable
            </Badge>
          </div>
        </Card>

        {/* Metric 4: Oral Viva Comprehension Rate */}
        <Card className="p-4 bg-card border-border shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>Viva Comprehension Avg</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-violet-500/10 text-violet-500">
              <Sparkles className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">
              {stats.avgComprehension}%
            </span>
            <Badge variant="outline" className="ml-auto text-[10px] bg-violet-500/10 text-violet-500 border-violet-500/30">
              High Authenticity
            </Badge>
          </div>
        </Card>
      </div>

      {/* Team Contribution Parity (Fair Share Visualizer) */}
      <Card className="p-5 bg-card border-border shadow-xs space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-foreground">
            Team Contribution Equity & Free-Rider Detection
          </h3>
          <p className="text-[11px] text-muted-foreground">
            Work distribution across all {teamStudents.length} assigned students in {selectedGroup?.code}
          </p>
        </div>

        <TeamParityBar members={teamStudents} />
      </Card>

      {/* Student Roster Cards */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-foreground">
              Team Member Individual Evaluations
            </h3>
            <p className="text-[11px] text-muted-foreground">
              Click &quot;Inspect Details&quot; to review the student&apos;s full 7-factor breakdown & oral viva transcript
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
              At Risk ({stats.atRiskCount})
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {displayedStudents.map((student) => {
            const isAtRisk = student.riskProbability >= 0.25 || student.riskLevel !== 'Low'
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
                      variant={isAtRisk ? 'destructive' : 'secondary'}
                      className={`text-[10px] font-semibold ${
                        !isAtRisk
                          ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
                          : ''
                      }`}
                    >
                      {student.riskLevel || 'Low Risk'}
                    </Badge>
                  </div>

                  {/* Metrics Row */}
                  <div className="grid grid-cols-3 gap-2 py-3 border-y border-border/60 text-xs text-center my-3">
                    <div>
                      <span className="text-[10px] text-muted-foreground">AHP Score</span>
                      <div className="font-mono font-bold text-sm text-foreground">
                        {student.currentScore || 8.5}/10
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] text-muted-foreground">Commits</span>
                      <div className="font-mono font-bold text-sm text-foreground flex items-center justify-center gap-1">
                        <GitCommit className="h-3 w-3 text-muted-foreground" />
                        {student.commitsCount || 34}
                      </div>
                    </div>
                    <div>
                      <span className="text-[10px] text-muted-foreground">PR Reviews</span>
                      <div className="font-mono font-bold text-sm text-foreground flex items-center justify-center gap-1">
                        <GitPullRequest className="h-3 w-3 text-muted-foreground" />
                        {student.prReviewsCount || 12}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Inspect Action */}
                <div className="pt-1 flex items-center justify-between">
                  <span className="text-[11px] text-muted-foreground">
                    Viva Comprehension: <strong>{student.comprehensionRate || 92}%</strong>
                  </span>

                  <Button
                    asChild
                    variant="ghost"
                    size="sm"
                    className="h-8 text-xs text-primary gap-1 cursor-pointer hover:bg-primary/10"
                  >
                    <Link to={`/teams/${teamCode}/performance/students?studentId=${student.id}`}>
                      <span>Inspect Details</span>
                      <ChevronRight className="h-3.5 w-3.5" />
                    </Link>
                  </Button>
                </div>
              </Card>
            )
          })}
        </div>
      </div>
    </div>
  )
}
