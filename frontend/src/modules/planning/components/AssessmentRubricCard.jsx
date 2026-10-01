import { useState } from 'react'
import { Award, GraduationCap, CheckCircle2, AlertTriangle, BookOpen, ChevronRight } from 'lucide-react'
import Card from '../../../shared/components/Card.jsx'
import Badge from '../../../shared/components/Badge.jsx'
import { Progress } from '@/components/ui/progress'
import { ASSESSMENT_RUBRIC } from '../data/lmsAcademicData.js'

export default function AssessmentRubricCard() {
  const [selectedCriteria, setSelectedCriteria] = useState(null)

  // Compute weighted score based on rubric
  const totalWeightedScore = Math.round(
    ASSESSMENT_RUBRIC.reduce((acc, r) => {
      const weightNum = parseInt(r.weight, 10) / 100
      return acc + r.currentPerformance * weightNum
    }, 0),
  )

  const getGradeClassification = (score) => {
    if (score >= 85) return { grade: 'A', label: 'First Class Honours / Exemplary', tone: 'success' }
    if (score >= 75) return { grade: 'A-', label: 'Upper Second Class / Proficient', tone: 'primary' }
    if (score >= 65) return { grade: 'B', label: 'Lower Second Class / Competent', tone: 'warning' }
    return { grade: 'C', label: 'Developing / Needs Intervention', tone: 'danger' }
  }

  const standing = getGradeClassification(totalWeightedScore)

  return (
    <Card className="p-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 mb-4 border-b border-border">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1 rounded bg-amber-500/10 text-amber-600 dark:text-amber-400">
              <GraduationCap className="h-4 w-4" />
            </span>
            <h3 className="text-base font-semibold text-foreground">Assessment Rubric &amp; Projected Grade</h3>
            <Badge tone={standing.tone} className="text-xs font-semibold">
              Projected: Grade {standing.grade} ({totalWeightedScore}%)
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">
            Academic evaluation criteria mapped to Capstone Learning Outcomes (IEEE 830 &amp; Agile Engineering)
          </p>
        </div>

        <div className="flex items-center gap-2 bg-muted/40 px-3 py-1.5 rounded-lg border border-border">
          <Award className="h-4 w-4 text-amber-500 shrink-0" />
          <div className="text-xs">
            <span className="text-muted-foreground">Standing: </span>
            <span className="font-semibold text-foreground">{standing.label}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {ASSESSMENT_RUBRIC.map((item) => {
          const isSelected = selectedCriteria?.id === item.id
          const tone =
            item.status === 'Exemplary' ? 'success' : item.status === 'Proficient' ? 'primary' : 'warning'

          return (
            <div
              key={item.id}
              onClick={() => setSelectedCriteria(isSelected ? null : item)}
              className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                isSelected
                  ? 'border-primary bg-primary/5 ring-1 ring-primary/20'
                  : 'border-border/70 hover:border-border hover:bg-muted/30'
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-1.5">
                <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
                  {item.category}
                </span>
                <div className="flex items-center gap-1.5">
                  <Badge tone="neutral" className="text-[10px] px-1.5 py-0">
                    {item.weight}
                  </Badge>
                  <Badge tone={tone} className="text-[10px] px-1.5 py-0">
                    {item.status}
                  </Badge>
                </div>
              </div>

              <h4 className="text-sm font-semibold text-foreground mb-1">{item.criterion}</h4>
              <p className="text-xs text-muted-foreground mb-2.5 line-clamp-1">{item.learningOutcome}</p>

              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground text-[11px]">{item.targetScore}</span>
                  <span className="font-bold text-foreground">{item.currentPerformance}%</span>
                </div>
                <Progress
                  value={item.currentPerformance}
                  className={`h-1.5 ${
                    item.currentPerformance >= 85
                      ? '[&>div]:bg-emerald-500'
                      : item.currentPerformance >= 70
                        ? '[&>div]:bg-primary'
                        : '[&>div]:bg-amber-500'
                  }`}
                />
              </div>

              {isSelected && (
                <div className="mt-3 pt-2.5 border-t border-border/60 text-xs text-muted-foreground space-y-1 animate-fade-rise">
                  <p className="text-[11px] text-foreground font-medium">{item.remarks}</p>
                  <p className="text-[10px] text-muted-foreground/80">{item.learningOutcome}</p>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </Card>
  )
}
