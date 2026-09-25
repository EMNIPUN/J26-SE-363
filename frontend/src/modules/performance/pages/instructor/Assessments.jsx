import { useState } from 'react'
import {
  CheckCircle2,
  HelpCircle,
  Save,
} from 'lucide-react'
import { useScope } from '@/shared/context/useScope.js'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
import AhpWeightSlider from '../../components/AhpWeightSlider.jsx'

export default function Assessments() {
  const { selectedGroup } = useScope()
  const [isSaved, setIsSaved] = useState(false)

  const handleSaveWeights = () => {
    setIsSaved(true)
    toast.success('AHP Weight Matrix Applied', {
      description: `New evaluation weights have been applied to ${selectedGroup?.code || 'all teams'}. Recalculating student contribution points...`,
    })
    setTimeout(() => setIsSaved(false), 3000)
  }

  return (
    <div className="space-y-6 animate-fade-rise">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            AHP Factor Calibration & Assessment Setup
          </h1>
          <p className="text-xs text-muted-foreground">
            Configure Analytic Hierarchy Process (AHP) pairwise comparison criteria and validate mathematical consistency ($CR &lt; 0.10$).
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={handleSaveWeights}
            disabled={isSaved}
            className="text-xs gap-1.5 cursor-pointer"
          >
            {isSaved ? (
              <>
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                <span>Applied to Cohort</span>
              </>
            ) : (
              <>
                <Save className="h-3.5 w-3.5" />
                <span>Apply Weights to Cohort</span>
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Main Weight Calibration Panel */}
      <AhpWeightSlider onWeightsChange={() => setIsSaved(false)} />

      {/* Research Methodology Documentation Card */}
      <Card className="p-5 bg-card border-border shadow-xs space-y-4">
        <div className="flex items-center gap-2 text-foreground font-semibold text-sm">
          <HelpCircle className="h-4 w-4 text-primary" />
          AHP Theoretical Framework & Consistency Ratio (CR) Rule
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="p-3.5 rounded-lg bg-muted/30 border border-border/70 space-y-1.5">
            <span className="font-semibold text-foreground">1. Multi-Criteria Vector</span>
            <p className="text-muted-foreground leading-relaxed">
              Thomas L. Saaty&apos;s Analytic Hierarchy Process decomposes complex human performance evaluation into 7 orthogonal activity dimensions across code activity, agile process, and oral comprehension.
            </p>
          </div>

          <div className="p-3.5 rounded-lg bg-muted/30 border border-border/70 space-y-1.5">
            <span className="font-semibold text-foreground">2. Consistency Index (CI)</span>
            <p className="text-muted-foreground leading-relaxed">
              The consistency of judgement is measured using $CI = (\lambda_{'{'}\max{'}'} - n) / (n - 1)$, where $\lambda_{'{'}\max{'}'}$ is the principal eigenvalue of the pairwise matrix and $n = 7$.
            </p>
          </div>

          <div className="p-3.5 rounded-lg bg-muted/30 border border-border/70 space-y-1.5">
            <span className="font-semibold text-foreground">3. Consistency Ratio Rule (CR)</span>
            <p className="text-muted-foreground leading-relaxed">
              $CR = CI / RI$. When $CR &lt; 0.10$, the pairwise comparisons are considered mathematically sound and consistent. If $CR \ge 0.10$, the matrix must be calibrated.
            </p>
          </div>
        </div>
      </Card>
    </div>
  )
}
