import { AlertCircle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function ErrorState({ title = 'Could not load this section', message, onRetry }) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-4 text-center"
    >
      <AlertCircle className="h-4 w-4 text-destructive" aria-hidden="true" />
      <p className="text-xs font-semibold text-foreground">{title}</p>
      {message && <p className="max-w-xs text-xs leading-relaxed text-muted-foreground">{message}</p>}
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry} className="mt-1">
          <RefreshCw aria-hidden="true" />
          Try again
        </Button>
      )}
    </div>
  )
}
