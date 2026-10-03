import { Bot } from 'lucide-react'
import { cn } from '@/lib/utils'

export default function TutorAvatar({ className }) {
  return (
    <span
      className={cn(
        'flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground',
        className,
      )}
      aria-hidden="true"
    >
      <Bot className="h-4 w-4" />
    </span>
  )
}
