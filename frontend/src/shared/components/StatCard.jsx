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
  loadingFallback,
}) {
  if (loading) {
    if (loadingFallback) return loadingFallback
    return (
      <Card className="p-5 flex items-start gap-4 border-border bg-card animate-pulse">
        <div className="h-11 w-11 rounded-lg bg-muted shrink-0" />
        <div className="flex-1 space-y-2 py-0.5 min-w-0">
          <div className="h-3 w-20 rounded bg-muted/70" />
          <div className="h-6 w-14 rounded bg-muted" />
          <div className="h-2.5 w-16 rounded bg-muted/50" />
        </div>
      </Card>
    )
  }

  const iconColor = TONE_BG[tone] || TONE_BG.primary

  return (
    <Card className="p-5 flex items-start gap-4 card-hover-lift border-border bg-card cursor-default">
      <div className={`p-3 rounded-lg flex items-center justify-center shrink-0 ${iconColor}`}>
        <Icon className="h-5 w-5" strokeWidth={2} />
      </div>
      <div className="flex flex-col min-w-0">
        <p className="text-xs font-medium text-muted-foreground truncate">{label}</p>
        <p className="text-2xl font-bold text-foreground mt-0.5 tracking-tight">{value}</p>
        {trend && (
          <p className="text-xs text-muted-foreground mt-1 font-medium">{trend}</p>
        )}
      </div>
    </Card>
  )
}

