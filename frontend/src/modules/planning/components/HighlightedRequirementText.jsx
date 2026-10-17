import { Popover, PopoverTrigger, PopoverContent } from '@/components/ui/popover'
import { findAmbiguousPhrases, DIMENSION_ISSUE } from '../utils.js'

export default function HighlightedRequirementText({ text, className = '' }) {
  const matches = findAmbiguousPhrases(text)

  if (matches.length === 0) {
    return <p className={className}>{text}</p>
  }

  const nodes = []
  let cursor = 0
  matches.forEach((m, i) => {
    if (m.start > cursor) nodes.push(<span key={`t-${i}`}>{text.slice(cursor, m.start)}</span>)
    const phraseText = text.slice(m.start, m.end)
    nodes.push(
      <Popover key={`m-${i}`}>
        <PopoverTrigger asChild>
          <mark className="bg-amber-200/60 dark:bg-amber-400/20 text-inherit rounded px-0.5 cursor-pointer underline decoration-amber-500 decoration-dotted underline-offset-2">
            {phraseText}
          </mark>
        </PopoverTrigger>
        <PopoverContent className="text-xs space-y-1.5">
          <p className="font-semibold text-foreground">Dimension: {DIMENSION_ISSUE.clarity.label}</p>
          <p className="text-muted-foreground">
            <span className="font-medium text-foreground">Problem: </span>
            "{phraseText}" is not measurable or objectively verifiable.
          </p>
          <p className="text-muted-foreground">
            <span className="font-medium text-foreground">Suggestion: </span>
            {DIMENSION_ISSUE.clarity.suggestion}
          </p>
        </PopoverContent>
      </Popover>,
    )
    cursor = m.end
  })
  if (cursor < text.length) nodes.push(<span key="t-last">{text.slice(cursor)}</span>)

  return <p className={className}>{nodes}</p>
}
