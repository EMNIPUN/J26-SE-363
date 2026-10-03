import { Lightbulb } from 'lucide-react'
import ContextSection from '../layout/ContextSection.jsx'
import { RecommendationDetails } from '../recommendation/RecommendationCard.jsx'

export default function NextRecommendation({ recommendation }) {
  return (
    <ContextSection
      icon={Lightbulb}
      title="Recommended Next Action"
      description="Updated from your new knowledge gaps"
      className="border-primary/30 ring-1 ring-primary/10"
    >
      {recommendation ? (
        <RecommendationDetails recommendation={recommendation} />
      ) : (
        <p className="text-xs leading-relaxed text-muted-foreground">
          You now meet every requirement for your current task. Optional challenges are in your learning plan.
        </p>
      )}
    </ContextSection>
  )
}
