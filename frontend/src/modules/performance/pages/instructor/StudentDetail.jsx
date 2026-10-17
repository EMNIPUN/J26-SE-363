import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { User } from 'lucide-react'
import { useScope } from '@/shared/context/useScope.js'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import AhpRadarChart from '../../components/AhpRadarChart.jsx'
import AtRiskPredictorCard from '../../components/AtRiskPredictorCard.jsx'
import CodeComprehensionLog from '../../components/CodeComprehensionLog.jsx'
import { MOCK_STUDENT_DETAILED_DATA } from '../../services/performanceService.js'

export default function StudentDetail() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { teamStudents, selectedGroup } = useScope()

  // Currently inspected student ID from URL query or first in team
  const activeStudentId = searchParams.get('studentId') || teamStudents[0]?.id || 'std-it23155534'

  // Switch student
  const handleSelectStudent = (id) => {
    setSearchParams({ studentId: id })
  }

  // Active student object from roster
  const student = useMemo(() => {
    return teamStudents.find((s) => s.id === activeStudentId) || teamStudents[0]
  }, [teamStudents, activeStudentId])

  // Detailed profile (mock fallback)
  const detailedProfile = useMemo(() => {
    const defaultData = MOCK_STUDENT_DETAILED_DATA['std-it23155534']
    if (activeStudentId === 'std-it23155534') return defaultData

    // Dynamic mock for other team members
    return {
      ...defaultData,
      studentId: student?.studentId || 'IT23152878',
      name: student?.name || 'Chathush Vishmika',
      overallScore: student?.currentScore || 8.4,
      atRisk: {
        isAtRisk: student?.riskLevel !== 'Low',
        probability: student?.riskProbability || 0.15,
        tier: student?.riskLevel || 'Low',
        trend: 'stable',
        sprintTrajectory: defaultData.atRisk.sprintTrajectory,
        primaryFactor: 'Steady commit activity with balanced backlog task closure',
      },
    }
  }, [student, activeStudentId])

  return (
    <div className="space-y-6 animate-fade-rise">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="text-xs font-mono">
              {selectedGroup?.code} Roster
            </Badge>
            <span className="text-xs text-muted-foreground">Detailed Evaluation Review</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Student Performance & Viva Investigation
          </h1>
          <p className="text-xs text-muted-foreground">
            Forensic analysis of individual contribution using 7-Factor AHP, ML at-risk classification, and oral viva verification.
          </p>
        </div>
      </div>

      {/* Team Member Switcher Chips */}
      <div className="p-2 rounded-xl bg-card border border-border shadow-2xs flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-muted-foreground px-2">
          Select Member:
        </span>
        {teamStudents.map((m) => {
          const isSelected = m.id === activeStudentId
          return (
            <Button
              key={m.id}
              variant={isSelected ? 'default' : 'ghost'}
              size="sm"
              onClick={() => handleSelectStudent(m.id)}
              className="h-8 text-xs cursor-pointer gap-2 font-medium"
            >
              <User className="h-3.5 w-3.5" />
              <span>{m.name.split(' ')[0]}</span>
              <span className="font-mono text-[10px] opacity-75">
                ({m.studentId})
              </span>
            </Button>
          )
        })}
      </div>

      {/* Student Overview Ribbon Card */}
      <Card className="p-5 bg-card border-border shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="h-12 w-12 rounded-xl bg-primary/10 text-primary flex items-center justify-center font-bold text-lg border border-primary/20">
              {student?.avatar || student?.name?.slice(0, 2).toUpperCase() || 'SS'}
            </div>
            <div>
              <div className="flex items-center gap-2 mb-0.5">
                <h2 className="text-lg font-bold text-foreground">{student?.name}</h2>
                <Badge
                  variant={student?.riskLevel === 'Low' ? 'secondary' : 'destructive'}
                  className={`text-[10px] font-semibold ${
                    student?.riskLevel === 'Low'
                      ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
                      : ''
                  }`}
                >
                  {student?.riskLevel || 'Low'} Risk
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                <strong className="text-foreground">{student?.studentId}</strong> • {student?.email} • Role: {student?.roleInGroup || 'Research Lead'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs">
            <div className="text-right">
              <span className="text-[11px] text-muted-foreground">AHP Score</span>
              <div className="font-mono font-bold text-lg text-foreground">
                {student?.currentScore || 8.8} / 10
              </div>
            </div>
            <div className="h-8 w-px bg-border" />
            <div className="text-right">
              <span className="text-[11px] text-muted-foreground">Viva Score</span>
              <div className="font-mono font-bold text-lg text-foreground">
                {student?.comprehensionRate || 94}%
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Main Analysis Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: 7-Factor Radar & AHP Breakdown */}
        <div className="lg:col-span-7 space-y-6">
          <Card className="p-5 bg-card border-border shadow-xs flex flex-col items-center">
            <div className="w-full mb-2">
              <h3 className="text-sm font-semibold text-foreground">
                7-Factor Analytic Hierarchy Process (AHP) Radar
              </h3>
              <p className="text-[11px] text-muted-foreground">
                Compares individual activity metrics against the group baseline
              </p>
            </div>

            <div className="py-2">
              <AhpRadarChart
                factors={detailedProfile.factors}
                size={320}
                studentLabel={student?.name?.split(' ')[0] || 'Student'}
              />
            </div>
          </Card>

          {/* Factor Points Matrix */}
          <Card className="p-5 bg-card border-border shadow-xs space-y-3">
            <h3 className="text-sm font-semibold text-foreground">
              Weighted Factor Contribution Points
            </h3>
            <div className="space-y-2 text-xs">
              {detailedProfile.factors.map((f) => (
                <div
                  key={f.id}
                  className="flex items-center justify-between p-2.5 rounded-lg border border-border/60 bg-muted/20"
                >
                  <div>
                    <span className="font-semibold text-foreground">{f.label}</span>
                    <span className="text-[11px] text-muted-foreground ml-2">
                      (Weight: {Math.round(f.weight * 100)}%)
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-muted-foreground">
                      Student: <strong>{f.studentValue}%</strong>
                    </span>
                    <Badge variant="outline" className="font-mono text-[10px]">
                      +{((f.studentValue * f.weight) / 10).toFixed(2)} pts
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Right Column: ML At-Risk Predictor & Oral Viva Transcripts */}
        <div className="lg:col-span-5 space-y-6">
          {/* ML At-Risk Card */}
          <AtRiskPredictorCard
            probability={detailedProfile.atRisk.probability}
            tier={detailedProfile.atRisk.tier}
            primaryFactor={detailedProfile.atRisk.primaryFactor}
          />

          {/* Oral Viva Transcript Log */}
          <CodeComprehensionLog
            comprehension={detailedProfile.comprehension}
          />
        </div>
      </div>
    </div>
  )
}
