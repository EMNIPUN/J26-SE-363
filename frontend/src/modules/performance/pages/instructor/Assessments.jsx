import { useState } from 'react'
import {
  CheckCircle2,
  Save,
} from 'lucide-react'
import { useScope } from '@/shared/context/useScope.js'
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
    </div>
  )
}

