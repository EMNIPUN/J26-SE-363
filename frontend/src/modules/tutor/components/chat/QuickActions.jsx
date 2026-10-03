import { Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { QUICK_ACTION_ICONS } from '../../utils/statusMeta.js'

export default function QuickActions({ actions, disabled, onSelect }) {
  if (!actions?.length) return null

  return (
    <div
      role="group"
      aria-label="Quick actions"
      className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1 [scrollbar-width:none] @2xl:flex-wrap @2xl:overflow-visible @2xl:pb-0"
    >
      {actions.map((action) => {
        const Icon = QUICK_ACTION_ICONS[action.id] ?? Sparkles
        return (
          <Button
            key={action.id}
            type="button"
            variant="outline"
            size="sm"
            className="h-7 shrink-0 rounded-full px-3 text-xs"
            disabled={disabled}
            title={action.prompt}
            onClick={() => onSelect(action)}
          >
            <Icon aria-hidden="true" />
            {action.label}
          </Button>
        )
      })}
    </div>
  )
}
