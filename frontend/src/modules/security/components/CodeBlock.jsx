import { cn } from '@/lib/utils'

// Renders a list of source lines with an optional highlighted (vulnerable) line.
export default function CodeBlock({ lines = [], highlightIndex = -1, className }) {
  return (
    <pre
      className={cn(
        'overflow-x-auto rounded-lg border border-border bg-muted/40 p-3 text-xs font-mono leading-relaxed',
        className,
      )}
    >
      {lines.map((line, index) => (
        <div
          key={`${index}-${line.slice(0, 12)}`}
          className={cn(
            'px-2 -mx-2 rounded',
            index === highlightIndex &&
              'border-l-2 border-amber-500 bg-amber-500/10 text-amber-700 dark:text-amber-300',
          )}
        >
          {line || ' '}
        </div>
      ))}
    </pre>
  )
}
