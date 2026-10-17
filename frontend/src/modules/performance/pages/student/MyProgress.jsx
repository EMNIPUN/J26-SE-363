import { useState, useMemo } from 'react'
import {
  BarChart3,
  Award,
  Sparkles,
  Users2,
  Lightbulb,
  CheckCircle2,
  Calendar,
} from 'lucide-react'
import { useScope } from '@/shared/context/useScope.js'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import AhpRadarChart from '../../components/AhpRadarChart.jsx'
import TeamParityBar from '../../components/TeamParityBar.jsx'
import AtRiskPredictorCard from '../../components/AtRiskPredictorCard.jsx'
import CodeComprehensionLog from '../../components/CodeComprehensionLog.jsx'
import EmptyState from '@/shared/components/EmptyState.jsx'
import { MOCK_STUDENT_DETAILED_DATA } from '../../services/performanceService.js'

export default function MyProgress() {
  const { selectedGroup, teamStudents, studentProfile } = useScope()
  const [activeTab, setActiveTab] = useState('factors')

  const record = studentProfile
  const detailed = useMemo(
    () => (record ? MOCK_STUDENT_DETAILED_DATA[record.id] || null : null),
    [record],
  )
  const scoreTotal = teamStudents.reduce((sum, member) => sum + (member.currentScore || 0), 0)
  const scoreShare = record?.currentScore && scoreTotal
    ? Math.round((record.currentScore / scoreTotal) * 100)
    : null

  return (
    <div className="space-y-6 animate-fade-rise">
      {/* Page Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="text-xs font-mono">
              {selectedGroup?.code} • {selectedGroup?.name}
            </Badge>
            <span className="text-xs text-muted-foreground">Sprint 4 Cycle</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Your learning progress
          </h1>
          <p className="text-sm text-muted-foreground">
            {record
              ? `A private look at ${record.name.split(' ')[0]}'s recorded work. These counts are not a rank.`
              : 'Sign in as a student to see your own recorded work.'}
          </p>
        </div>

        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-card border border-border text-xs shadow-2xs">
          <Calendar className="h-3.5 w-3.5 text-primary" />
          <span className="text-muted-foreground">Evaluation Cycle:</span>
          <span className="font-semibold text-foreground">Active Sprint</span>
        </div>
      </div>

      {/* Top 4 KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Metric 1: AHP Overall Score */}
        <Card className="p-4 bg-card border-border shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>Contribution so far</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Award className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">
              {record?.currentScore ?? '—'}
            </span>
            <span className="text-xs text-muted-foreground font-mono">/ 10</span>
            <Badge className="ml-auto text-xs bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20">
              Recorded
            </Badge>
          </div>
        </Card>

        {/* Metric 2: Team Share Parity */}
        <Card className="p-4 bg-card border-border shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>Share of recorded scores</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Users2 className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">{scoreShare != null ? `${scoreShare}%` : '—'}</span>
            <span className="text-xs text-muted-foreground">of this team</span>
            <Badge variant="outline" className="ml-auto text-xs text-primary border-primary/30">
              From profile scores
            </Badge>
          </div>
        </Card>

        {/* Metric 3: At-Risk ML Prediction */}
        <Card className="p-4 bg-card border-border shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>Commits on record</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-500">
              <Sparkles className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">
              {record?.commitsCount ?? '—'}
            </span>
            <Badge variant="outline" className="ml-auto text-xs bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30">
              Observed
            </Badge>
          </div>
        </Card>

        {/* Metric 4: GenAI Code Comprehension */}
        <Card className="p-4 bg-card border-border shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>Stand-ups on record</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
              <CheckCircle2 className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">
              {record?.standupAttendance ?? '—'}
            </span>
            <Badge variant="outline" className="ml-auto text-xs bg-primary/10 text-primary border-primary/30">
              Observed
            </Badge>
          </div>
        </Card>
      </div>

      {/* Tabs Navigation */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid grid-cols-2 sm:grid-cols-4 max-w-xl h-9 bg-muted/60 p-1">
          <TabsTrigger value="factors" className="text-xs cursor-pointer gap-1.5">
            <BarChart3 className="h-3.5 w-3.5" />
            7 Factors
          </TabsTrigger>
          <TabsTrigger value="parity" className="text-xs cursor-pointer gap-1.5">
            <Users2 className="h-3.5 w-3.5" />
            Team Parity
          </TabsTrigger>
          <TabsTrigger value="viva" className="text-xs cursor-pointer gap-1.5">
            <Award className="h-3.5 w-3.5" />
            Viva Transcripts
          </TabsTrigger>
          <TabsTrigger value="coaching" className="text-xs cursor-pointer gap-1.5">
            <Lightbulb className="h-3.5 w-3.5" />
            AI Advice
          </TabsTrigger>
        </TabsList>

        {/* Tab 1: 7-Factor AHP Spider Radar & Matrix Breakdown */}
        <TabsContent value="factors" className="space-y-4 pt-2">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left Column: Spider Radar Chart */}
            <Card className="lg:col-span-5 p-5 bg-card border-border shadow-xs flex flex-col items-center justify-center">
              <div className="w-full mb-2">
                <h3 className="text-sm font-semibold text-foreground">
                  Multi-Factor Contribution Radar
                </h3>
                <p className="text-xs text-muted-foreground">
                  Your scores beside the team average, so you can see where to practice. This is not a ranking.
                </p>
              </div>

              <div className="py-2">
                {detailed ? (
                  <AhpRadarChart factors={detailed.factors} size={330} />
                ) : (
                  <EmptyState
                    card={false}
                    title="No factor breakdown yet"
                    description="A seven-factor chart appears only when it is stored for you. Your commits, reviews, and stand-ups above are the record we have."
                  />
                )}
              </div>
            </Card>

            {/* Right Column: Factor Details Table */}
            <Card className="lg:col-span-7 p-5 bg-card border-border shadow-xs space-y-4">
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  AHP Weighted Factor Points
                </h3>
                <p className="text-[11px] text-muted-foreground">
                  Calculated using pairwise eigenvalue eigenvector weighting ($CR &lt; 0.10$)
                </p>
              </div>

              <div className="space-y-2.5">
                {(detailed?.factors || []).map((f) => {
                  const contributionPoints = ((f.studentValue * f.weight) / 10).toFixed(2)
                  const isAboveAvg = f.studentValue >= f.groupAvg

                  return (
                    <div
                      key={f.id}
                      className="p-3 rounded-lg border border-border/60 bg-muted/20 flex items-center justify-between gap-4 text-xs"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-semibold text-foreground truncate">
                            {f.label}
                          </span>
                          <span className="text-[10px] font-mono text-muted-foreground">
                            (Weight: {Math.round(f.weight * 100)}%)
                          </span>
                        </div>
                        <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
                          <span>
                            You: <strong className="text-foreground">{f.studentValue}%</strong>
                          </span>
                          <span>•</span>
                          <span>Team Avg: {f.groupAvg}%</span>
                        </div>
                      </div>

                      <div className="text-right shrink-0">
                        <div className="font-mono font-bold text-sm text-foreground">
                          +{contributionPoints} pts
                        </div>
                        <Badge
                          variant={isAboveAvg ? 'default' : 'secondary'}
                          className={`text-[9px] px-1.5 py-0 ${
                            isAboveAvg
                              ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
                              : 'text-muted-foreground'
                          }`}
                        >
                          {isAboveAvg ? 'A strength' : 'Room to grow'}
                        </Badge>
                      </div>
                    </div>
                  )
                })}
              </div>
            </Card>
          </div>
        </TabsContent>

        {/* Tab 2: Team Parity & Contribution Equity */}
        <TabsContent value="parity" className="space-y-6 pt-2">
          <Card className="p-5 bg-card border-border shadow-xs space-y-4">
            <div>
              <h3 className="text-sm font-semibold text-foreground">
                How the work is shared
              </h3>
              <p className="text-xs text-muted-foreground">
                A lighter or heavier share is a signal to rebalance the sprint, not a judgment of you.
              </p>
            </div>

            <TeamParityBar
              members={teamStudents}
              highlightStudentId={record?.id}
              audience="student"
            />
          </Card>

          {detailed?.atRisk?.sprintTrajectory?.length > 0 && (
            <Card className="p-5 bg-card border-border shadow-xs space-y-3">
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  Scores across recent sprints
                </h3>
                <p className="text-xs text-muted-foreground">
                  Stored with this sample profile. Not a comparison with your classmates.
                </p>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                {detailed.atRisk.sprintTrajectory.map((s) => (
                  <div
                    key={s.sprint}
                    className="p-3 rounded-lg border border-border/70 bg-muted/20 text-xs text-center space-y-1"
                  >
                    <span className="text-muted-foreground font-medium">{s.sprint}</span>
                    <div className="font-mono text-lg font-bold text-foreground">{s.score}</div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </TabsContent>

        {/* Tab 3: GenAI Code Comprehension Viva Log */}
        <TabsContent value="viva" className="space-y-4 pt-2">
          {detailed?.comprehension ? (
            <CodeComprehensionLog comprehension={detailed.comprehension} />
          ) : (
            <EmptyState
              title="No explanation transcript yet"
              description="A viva transcript is shown only when it is stored for you. Nothing here is copied from another student."
            />
          )}
        </TabsContent>

        {/* Tab 4: AI Coaching & Actionable Recommendations */}
        <TabsContent value="coaching" className="space-y-4 pt-2">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-6 space-y-4">
              {detailed?.atRisk ? (
                <AtRiskPredictorCard
                  audience="student"
                  probability={detailed.atRisk.probability}
                  tier={detailed.atRisk.tier}
                  primaryFactor={detailed.atRisk.primaryFactor}
                />
              ) : (
                <EmptyState
                  title="No pattern estimate yet"
                  description="Your commits and stand-ups are on the summary above. A pattern estimate is not stored for this profile."
                />
              )}
            </div>

            <div className="lg:col-span-6 space-y-4">
              {detailed ? (
                <Card className="p-5 bg-card border-border shadow-xs space-y-4">
                  <div className="flex items-center gap-2 text-foreground font-semibold text-sm">
                    <Lightbulb className="h-4 w-4 text-amber-500" />
                    Ideas for the next sprint
                  </div>
                  <div className="space-y-3 text-sm">
                    <div className="p-3 rounded-lg bg-primary/5 border border-primary/20 space-y-1">
                      <span className="font-semibold text-primary">Keep reviewing your teammates’ work</span>
                      <p className="text-muted-foreground leading-relaxed">
                        {record?.prReviewsCount ?? 0} pull request reviews are on this profile. That habit helps the whole team.
                      </p>
                    </div>
                    <div className="p-3 rounded-lg bg-muted/30 border border-border/70 space-y-1">
                      <span className="font-semibold text-foreground">Keep changes easy to explain</span>
                      <p className="text-muted-foreground leading-relaxed">
                        Smaller pull requests are easier to talk through later. This note comes with the sample factor breakdown.
                      </p>
                    </div>
                  </div>
                </Card>
              ) : (
                <EmptyState
                  title="No suggestions stored"
                  description="When a factor breakdown exists for you, practice ideas will show here. They will not be copied from someone else."
                />
              )}
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
