import { BookOpen, ClipboardCheck, Code2, FileStack, GitCommitHorizontal } from 'lucide-react'
import { formatDateTime } from '../../utils/format.js'

const EVIDENCE_ICONS = {
  lesson: BookOpen,
  quiz: ClipboardCheck,
  exercise: Code2,
  commit: GitCommitHorizontal,
}

export default function EvidenceSummary({ evidence, updatedAt }) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-xs font-medium text-muted-foreground">
          Evidence: <span className="font-semibold text-foreground">{evidence.total} activities</span>
        </p>
        {updatedAt && (
          <p className="text-[11px] text-muted-foreground">
            Updated <time dateTime={updatedAt}>{formatDateTime(updatedAt)}</time>
          </p>
        )}
      </div>
      <ul className="mt-2 flex flex-wrap gap-1.5">
        {evidence.breakdown.map((item) => {
          const Icon = EVIDENCE_ICONS[item.type] ?? FileStack
          return (
            <li
              key={item.type}
              className="flex items-center gap-1.5 rounded-md border border-border/60 bg-muted/40 px-2 py-1 text-[11px] text-muted-foreground"
            >
              <Icon className="h-3.5 w-3.5" aria-hidden="true" />
              <span>
                {item.label} <span className="font-semibold tabular-nums text-foreground">{item.count}</span>
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
