import { ExternalLink, Loader2, MonitorPlay, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function ActivityFrame({ ref, src, title, platformName, onCheckProgress, isChecking, notice, error }) {
  return (
    <section
      aria-label={`${platformName} activity`}
      className="overflow-hidden rounded-xl border border-border/60 bg-card card-elevated"
    >
      <div className="flex flex-wrap items-center gap-2 border-b border-border/60 px-4 py-2.5">
        <p className="flex min-w-0 basis-full items-center gap-2 text-sm font-semibold text-foreground @lg:flex-1 @lg:basis-0">
          <MonitorPlay className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
          <span className="truncate">{platformName}</span>
        </p>
        <Button asChild variant="ghost" size="sm">
          <a href={src} target="_blank" rel="noopener noreferrer">
            <ExternalLink aria-hidden="true" />
            Open in new tab
          </a>
        </Button>
        <Button variant="outline" size="sm" onClick={onCheckProgress} disabled={isChecking}>
          {isChecking ? <Loader2 className="animate-spin" aria-hidden="true" /> : <RefreshCw aria-hidden="true" />}
          {isChecking ? 'Checking…' : 'Check progress'}
        </Button>
      </div>

      <div aria-live="polite" className="empty:hidden">
        {notice && <p className="border-b border-border/60 bg-muted/50 px-4 py-2 text-xs text-muted-foreground">{notice}</p>}
      </div>
      {error && (
        <p role="alert" className="border-b border-destructive/30 bg-destructive/10 px-4 py-2 text-xs text-destructive">
          {error}
        </p>
      )}

      <iframe
        ref={ref}
        src={src}
        title={title}
        sandbox="allow-scripts allow-forms allow-same-origin allow-popups"
        referrerPolicy="strict-origin-when-cross-origin"
        className="block h-[70svh] min-h-[460px] w-full border-0 bg-white"
      />
    </section>
  )
}
