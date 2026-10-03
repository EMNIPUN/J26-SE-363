import { useRef, useState } from 'react'
import { MessagesSquare, Target } from 'lucide-react'
import TutorAvatar from '../chat/TutorAvatar.jsx'
import ChatThread from '../chat/ChatThread.jsx'
import QuickActions from '../chat/QuickActions.jsx'
import ChatInput from '../chat/ChatInput.jsx'
import LoadingState from '../common/LoadingState.jsx'
import ErrorState from '../common/ErrorState.jsx'
import { useTutorContext } from '../../hooks/useTutorOverview.js'
import { useQuickActions, useSendTutorMessage, useTutorConversation } from '../../hooks/useTutorChat.js'

function TaskFocusChip() {
  const { data } = useTutorContext()
  if (!data?.task) return null

  return (
    <p
      className="ml-auto flex min-w-0 max-w-[55%] items-center gap-1.5 rounded-md border border-border/60 bg-muted/50 px-2 py-1 text-[11px] text-muted-foreground"
      title={data.task.title}
    >
      <Target className="h-3.5 w-3.5 shrink-0 text-primary" aria-hidden="true" />
      <span className="sr-only">Current task:</span>
      <span className="truncate font-medium text-foreground">{data.task.title}</span>
    </p>
  )
}

function ChatBody({ conversationQuery, outgoing, onRetry, onEdit }) {
  if (conversationQuery.isPending) {
    return (
      <div className="mx-auto w-full max-w-3xl flex-1 px-4 py-5">
        <LoadingState rows={4} label="Loading your conversation" />
      </div>
    )
  }

  if (conversationQuery.isError) {
    return (
      <div className="mx-auto w-full max-w-md flex-1 px-4 py-8">
        <ErrorState
          title="Could not load your conversation"
          message={conversationQuery.error?.message}
          onRetry={() => conversationQuery.refetch()}
        />
      </div>
    )
  }

  const messages = conversationQuery.data ?? []
  if (messages.length === 0 && !outgoing) {
    return (
      <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-xl border border-border/60 bg-muted text-muted-foreground">
          <MessagesSquare className="h-6 w-6 stroke-[1.5]" aria-hidden="true" />
        </span>
        <p className="max-w-xs text-xs leading-relaxed text-muted-foreground">
          Ask the Tutor about your current task, or start with one of the quick actions below.
        </p>
      </div>
    )
  }

  return <ChatThread messages={messages} outgoing={outgoing} onRetry={onRetry} onEdit={onEdit} />
}

export default function TutorChat() {
  const conversationQuery = useTutorConversation()
  const quickActionsQuery = useQuickActions()
  const sendMessage = useSendTutorMessage()
  const [draft, setDraft] = useState('')
  const inputRef = useRef(null)

  const { isPending, isError, variables, error } = sendMessage
  const isReady = conversationQuery.isSuccess

  const outgoing =
    (isPending || isError) && variables
      ? {
          message: { id: 'outgoing', role: 'student', content: variables.message },
          status: isPending ? 'sending' : 'failed',
          error: error?.message,
        }
      : null

  const send = (payload) => {
    if (isPending || !isReady) return
    sendMessage.mutate(payload)
  }

  const handleSubmit = () => {
    const message = draft.trim()
    if (!message) return
    send({ message })
    setDraft('')
  }

  const handleRetry = () => send(variables)

  const handleEdit = () => {
    setDraft(variables?.message ?? '')
    sendMessage.reset()
    inputRef.current?.focus()
  }

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-border/60 bg-card card-elevated">
      <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border px-4">
        <TutorAvatar className="h-8 w-8" />
        <div className="min-w-0 shrink-0">
          <p className="truncate text-sm font-semibold text-foreground">SELVIA Tutor</p>
          <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden="true" />
            Adaptive AI Tutor · Online
          </p>
        </div>
        <TaskFocusChip />
      </header>

      <ChatBody conversationQuery={conversationQuery} outgoing={outgoing} onRetry={handleRetry} onEdit={handleEdit} />

      <footer className="shrink-0 border-t border-border px-4 pb-2 pt-3">
        <div className="mx-auto w-full max-w-3xl space-y-2.5">
          <QuickActions
            actions={quickActionsQuery.data}
            disabled={isPending || !isReady}
            onSelect={(action) => send({ message: action.prompt, quickActionId: action.id })}
          />
          <ChatInput
            ref={inputRef}
            value={draft}
            onChange={setDraft}
            onSubmit={handleSubmit}
            disabled={!isReady}
            canSend={!isPending}
          />
        </div>
      </footer>
    </div>
  )
}
