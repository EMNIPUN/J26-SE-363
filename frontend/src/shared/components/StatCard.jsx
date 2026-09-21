import { Card } from '@/components/ui/card'

const TONE_BG = {
  primary: 'bg-primary/10 text-primary',
  success: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-400',
  warning: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-400',
  danger: 'bg-destructive/10 text-destructive',
}

export default function StatCard({ icon: Icon, label, value, trend, tone = 'primary' }) {
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

