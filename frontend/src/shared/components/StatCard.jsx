import { Card } from '@/components/ui/card'

const TONE_BG = {
  primary: 'bg-primary/10 text-primary',
  success: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400',
  warning: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400',
  danger: 'bg-destructive/10 text-destructive',
}

export default function StatCard({
  icon: Icon,
  label,
  value,
  trend,
  tone = 'primary',
  loading = false,
  query,
  loadingFallback,
}) {
  const isLoading = loading || Boolean(query?.isLoading || query?.isPending)

  if (isLoading) {
    if (loadingFallback) return loadingFallback
    return (
      <Card className="p-4 flex-row items-center gap-4 card-elevated ring-0 border border-border/60 bg-card animate-pulse">
        <div className="h-11 w-11 rounded-xl bg-muted shrink-0" />
        <div className="flex-1 space-y-2 min-w-0">
          <div className="h-3 w-24 rounded bg-muted/70" />
          <div className="h-6 w-14 rounded bg-muted" />
        </div>
      </Card>
    )
  }

  const iconColor = TONE_BG[tone] || TONE_BG.primary

  return (
    <Card className="p-4 flex-row items-center gap-4 card-elevated ring-0 border border-border/60 bg-card">
      <div className={`h-11 w-11 rounded-xl flex items-center justify-center shrink-0 ${iconColor}`}>
        <Icon className="h-5 w-5" strokeWidth={2} />
      </div>
      <div className="flex flex-col min-w-0">
        <p className="text-xs font-medium text-muted-foreground truncate">{label}</p>
        <p className="text-2xl font-bold text-foreground leading-tight tracking-tight">{value}</p>
        {trend && (
          <p className="text-xs text-muted-foreground truncate">{trend}</p>
        )}
      </div>
    </Card>
  )
}
