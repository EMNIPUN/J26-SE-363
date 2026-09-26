import { useState, useMemo } from 'react'
import {
  BarChart3,
  Award,
  Sparkles,
  Users2,
  TrendingUp,
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
import { MOCK_STUDENT_DETAILED_DATA } from '../../services/performanceService.js'

export default function MyProgress() {
  const { selectedGroup, teamStudents } = useScope()
  const [activeTab, setActiveTab] = useState('factors')

  // Get student's detailed performance evaluation
  const profile = useMemo(() => {
    return MOCK_STUDENT_DETAILED_DATA['std-it23155534']
  }, [])

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
            My Individual Performance & Contribution
          </h1>
          <p className="text-xs text-muted-foreground">
            Multi-metric Analytic Hierarchy Process (AHP) scoring, ML risk prediction & GenAI code comprehension.
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
            <span>AHP Contribution Score</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Award className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">
              {profile.overallScore}
            </span>
            <span className="text-xs text-muted-foreground font-mono">/ 10</span>
            <Badge className="ml-auto text-[10px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20">
              Grade A (Top 5%)
            </Badge>
          </div>
        </Card>

        {/* Metric 2: Team Share Parity */}
        <Card className="p-4 bg-card border-border shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>Team Contribution Share</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-blue-500/10 text-blue-500">
              <Users2 className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">32%</span>
            <span className="text-xs text-muted-foreground">of team total</span>
            <Badge variant="outline" className="ml-auto text-[10px] text-blue-500 border-blue-500/30">
              Target: 25%
            </Badge>
          </div>
        </Card>

        {/* Metric 3: At-Risk ML Prediction */}
        <Card className="p-4 bg-card border-border shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>Free-Rider Risk Probability</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-emerald-500/10 text-emerald-500">
              <Sparkles className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-emerald-500">
              {Math.round(profile.atRisk.probability * 100)}%
            </span>
            <Badge variant="outline" className="ml-auto text-[10px] bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30">
              Low Risk (Safe)
            </Badge>
          </div>
        </Card>

        {/* Metric 4: GenAI Code Comprehension */}
        <Card className="p-4 bg-card border-border shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
            <span>Viva Oral Comprehension</span>
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-violet-500/10 text-violet-500">
              <CheckCircle2 className="h-4 w-4" />
            </div>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">
              {profile.comprehension.score}%
            </span>
            <Badge variant="outline" className="ml-auto text-[10px] bg-violet-500/10 text-violet-500 border-violet-500/30">
              Authentic Author
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
                <p className="text-[11px] text-muted-foreground">
                  Your normalized scores vs team average across 7 research dimensions
                </p>
              </div>

              <div className="py-2">
                <AhpRadarChart factors={profile.factors} size={330} />
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
                {profile.factors.map((f) => {
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
                          {isAboveAvg ? 'Above Avg' : 'Below Avg'}
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
                Team Contribution Parity (Fair-Share Distribution)
              </h3>
              <p className="text-[11px] text-muted-foreground">
                Monitors workload balance to prevent free-riding and avoid single-developer burn-out
              </p>
            </div>

            <TeamParityBar
              members={teamStudents}
              highlightStudentId="std-it23155534"
            />
          </Card>

          {/* Longitudinal Sprint History */}
          <Card className="p-5 bg-card border-border shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-foreground">
                  Multi-Sprint Performance Trajectory
                </h3>
                <p className="text-[11px] text-muted-foreground">
                  Progression across Sprints 1 to 4
                </p>
              </div>
              <Badge variant="outline" className="text-xs text-primary gap-1">
                <TrendingUp className="h-3 w-3" />
                Upward Momentum (+0.7 pts)
              </Badge>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
              {profile.atRisk.sprintTrajectory.map((s) => (
                <div
                  key={s.sprint}
                  className="p-3 rounded-lg border border-border/70 bg-muted/20 text-xs text-center space-y-1"
                >
                  <span className="text-muted-foreground font-medium text-[11px]">
                    {s.sprint}
                  </span>
                  <div className="font-mono text-lg font-bold text-foreground">
                    {s.score}
                  </div>
                  <div className="text-[10px] text-emerald-500 font-medium">
                    Risk: {Math.round(s.probability * 100)}%
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </TabsContent>

        {/* Tab 3: GenAI Code Comprehension Viva Log */}
        <TabsContent value="viva" className="space-y-4 pt-2">
          <CodeComprehensionLog comprehension={profile.comprehension} />
        </TabsContent>

        {/* Tab 4: AI Coaching & Actionable Recommendations */}
        <TabsContent value="coaching" className="space-y-4 pt-2">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-6 space-y-4">
              <AtRiskPredictorCard
                probability={profile.atRisk.probability}
                tier={profile.atRisk.tier}
                primaryFactor={profile.atRisk.primaryFactor}
              />
            </div>

            <div className="lg:col-span-6 space-y-4">
              <Card className="p-5 bg-card border-border shadow-xs space-y-4">
                <div className="flex items-center gap-2 text-foreground font-semibold text-sm">
                  <Lightbulb className="h-4 w-4 text-amber-500" />
                  Prescriptive Recommendations for Next Sprint
                </div>

                <div className="space-y-3 text-xs">
                  <div className="p-3 rounded-lg bg-primary/5 border border-primary/20 space-y-1">
                    <span className="font-semibold text-primary">
                      1. Maintain High PR Review Rigor
                    </span>
                    <p className="text-muted-foreground leading-relaxed">
                      You reviewed 14 pull requests in Sprint 4 with substantial code feedback. Keep this up in Sprint 5 to maintain your Grade A standing.
                    </p>
                  </div>

                  <div className="p-3 rounded-lg bg-muted/30 border border-border/70 space-y-1">
                    <span className="font-semibold text-foreground">
                      2. Code Churn Balance
                    </span>
                    <p className="text-muted-foreground leading-relaxed">
                      Your commits are well-spaced over weekdays. Ensure pull requests remain under 400 lines of net change to maximize code comprehension scores.
                    </p>
                  </div>

                  <div className="p-3 rounded-lg bg-muted/30 border border-border/70 space-y-1">
                    <span className="font-semibold text-foreground">
                      3. Assist Teammate Backlog
                    </span>
                    <p className="text-muted-foreground leading-relaxed">
                      Team member Dilshan has a slight task bottleneck in Sprint 4. Cross-pair review on their pull requests will elevate the entire group parity index.
                    </p>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
