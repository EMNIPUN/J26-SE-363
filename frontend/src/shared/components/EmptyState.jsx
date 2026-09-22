import { Inbox } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export default function EmptyState({
  icon: Icon = Inbox,
  title = 'No items found',
  description = 'There are no records matching your current criteria.',
  actionLabel,
  onAction,
  className = '',
  card = true,
}) {
  const content = (
    <div className={`flex flex-col items-center justify-center text-center p-8 sm:p-12 ${className}`}>
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted border border-border/60 text-muted-foreground mb-4 shadow-xs">
        <Icon className="h-6 w-6 stroke-[1.5]" />
      </div>
      <h3 className="text-sm font-semibold text-foreground tracking-tight mb-1">
        {title}
      </h3>
      <p className="text-xs text-muted-foreground max-w-sm leading-relaxed mb-5">
        {description}
      </p>
      {actionLabel && onAction && (
        <Button
          onClick={onAction}
          size="sm"
          className="cursor-pointer active:scale-95 transition-transform"
        >
          {actionLabel}
        </Button>
      )}
    </div>
  )

  if (card) {
    return <Card className="border-border bg-card">{content}</Card>
  }

  return content
}
