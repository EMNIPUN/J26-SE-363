import { CircleCheck, Sparkles, Trophy } from 'lucide-react'
import Badge from '@/shared/components/Badge.jsx'
import { LEVEL, getMeta } from '../../utils/statusMeta.js'

export default function ItemBadges({ level, matchesLevel, recommended, challenge }) {
  const levelMeta = getMeta(LEVEL, level)

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {recommended && (
        <Badge tone="primary">
          <Sparkles className="h-3 w-3" aria-hidden="true" />
          Recommended next
        </Badge>
      )}
      {challenge && (
        <Badge tone="warning">
          <Trophy className="h-3 w-3" aria-hidden="true" />
          Optional challenge
        </Badge>
      )}
      <Badge tone={levelMeta.tone}>{levelMeta.label}</Badge>
      {matchesLevel && (
        <Badge tone="neutral">
          <CircleCheck className="h-3 w-3" aria-hidden="true" />
          Matches your level
        </Badge>
      )}
    </div>
  )
}
