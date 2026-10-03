import { Inbox } from 'lucide-react'

export default function EmptyState({ icon: Icon = Inbox, title, description, action }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-lg border border-dashed border-border px-3 py-5 text-center">
      <Icon className="h-5 w-5 text-muted-foreground stroke-[1.5]" aria-hidden="true" />
      <p className="text-xs font-semibold text-foreground">{title}</p>
      {description && <p className="max-w-xs text-xs leading-relaxed text-muted-foreground">{description}</p>}
      {action}
    </div>
  )
}
