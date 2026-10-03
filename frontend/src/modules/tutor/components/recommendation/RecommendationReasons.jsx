import { Check } from 'lucide-react'

export default function RecommendationReasons({ reasons }) {
  if (!reasons?.length) return null

  return (
    <div>
      <h4 className="text-xs font-semibold text-foreground">Why this was recommended</h4>
      <ul className="mt-2 space-y-1.5">
        {reasons.map((reason) => (
          <li key={reason} className="flex items-start gap-2 text-xs leading-relaxed text-muted-foreground">
            <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Check className="h-3 w-3" aria-hidden="true" />
            </span>
            {reason}
          </li>
        ))}
      </ul>
    </div>
  )
}
