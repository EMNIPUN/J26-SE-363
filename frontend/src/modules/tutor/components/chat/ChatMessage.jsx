import { RotateCcw, PencilLine } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import TutorAvatar from './TutorAvatar.jsx'
import MessageContext from './MessageContext.jsx'
import { formatTime } from '../../utils/format.js'

function FailedFooter({ error, onRetry, onEdit }) {
  return (
    <div className="mt-1 flex flex-wrap items-center justify-end gap-x-2 gap-y-1 text-[11px]">
      <span className="text-destructive">Not sent{error ? `: ${error}` : ''}</span>
      <Button variant="ghost" size="sm" className="h-6 px-2 text-[11px]" onClick={onRetry}>
        <RotateCcw aria-hidden="true" />
        Retry
      </Button>
      <Button variant="ghost" size="sm" className="h-6 px-2 text-[11px]" onClick={onEdit}>
        <PencilLine aria-hidden="true" />
        Edit
      </Button>
    </div>
  )
}

// `status` is 'sent' (default), 'sending' or 'failed'.
export default function ChatMessage({ message, status = 'sent', error, onRetry, onEdit }) {
  const isTutor = message.role === 'tutor'
  const time = formatTime(message.createdAt)

  return (
    <li className={cn('flex gap-2.5', isTutor ? 'justify-start' : 'justify-end')}>
      {isTutor && <TutorAvatar className="mt-0.5" />}
      <div className={cn('flex min-w-0 max-w-[85%] flex-col', isTutor ? 'items-start' : 'items-end')}>
        <span className="sr-only">{isTutor ? 'Tutor:' : 'You:'}</span>
        <div
          className={cn(
            'whitespace-pre-line break-words rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed',
            isTutor ? 'rounded-tl-sm bg-muted text-foreground' : 'rounded-tr-sm bg-primary text-primary-foreground',
            status === 'sending' && 'opacity-70',
            status === 'failed' && 'bg-destructive/10 text-foreground ring-1 ring-destructive/30',
          )}
        >
          {message.content}
        </div>
        {isTutor && <MessageContext context={message.context} action={message.action} />}
        {status === 'failed' ? (
          <FailedFooter error={error} onRetry={onRetry} onEdit={onEdit} />
        ) : (
          <span className="mt-1 px-1 text-[11px] text-muted-foreground">
            {status === 'sending' ? 'Sending…' : time && <time dateTime={message.createdAt}>{time}</time>}
          </span>
        )}
      </div>
    </li>
  )
}
