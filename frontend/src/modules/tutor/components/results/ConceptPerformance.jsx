import Badge from '@/shared/components/Badge.jsx'
import ProgressBar from '../common/ProgressBar.jsx'
import { PERFORMANCE_BAND, getMeta } from '../../utils/statusMeta.js'

export default function ConceptPerformance({ items }) {
  return (
    <ul className="space-y-3">
      {items.map((item) => {
        const band = getMeta(PERFORMANCE_BAND, item.band)
        return (
          <li key={item.conceptId} className="space-y-1.5">
            <div className="flex items-center gap-2 text-sm">
              <span className="font-medium text-foreground">{item.name}</span>
              <Badge tone={band.tone}>{band.label}</Badge>
              <span className="ml-auto font-semibold tabular-nums text-foreground">{item.score}%</span>
            </div>
            <ProgressBar value={item.score} label={`${item.name} score`} barClass={band.barClass} className="h-2" />
          </li>
        )
      })}
    </ul>
  )
}
