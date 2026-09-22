import { Badge as ShadcnBadge } from '@/components/ui/badge'

const TONE_CLASSES = {
  neutral: 'bg-muted text-muted-foreground hover:bg-muted border-border',
  primary: 'bg-primary/10 text-primary hover:bg-primary/15 border-primary/20',
  success: 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-400 dark:border-emerald-800',
  warning: 'bg-amber-50 text-amber-800 hover:bg-amber-100 border-amber-200 dark:bg-amber-950/40 dark:text-amber-400 dark:border-amber-800',
  danger: 'bg-destructive/10 text-destructive hover:bg-destructive/15 border-destructive/20',
}

export default function Badge({ tone = 'neutral', className = '', children, ...props }) {
  const toneClass = TONE_CLASSES[tone] || TONE_CLASSES.neutral
  return (
    <ShadcnBadge
      variant="outline"
      className={`font-medium px-2 py-0.5 text-xs rounded-md inline-flex items-center gap-1 ${toneClass} ${className}`}
      {...props}
    >
      {children}
    </ShadcnBadge>
  )
}

