import { useEffect, useRef } from 'react'
import ChatMessage from './ChatMessage.jsx'
import TypingIndicator from './TypingIndicator.jsx'

// Scrollable message log. `outgoing` is the student message currently being
// sent (or that failed to send); it is not yet part of the stored conversation.
export default function ChatThread({ messages, outgoing, onRetry, onEdit }) {
  const scrollRef = useRef(null)
  const hasScrolledRef = useRef(false)

  useEffect(() => {
    const container = scrollRef.current
    if (!container) return
    container.scrollTo({ top: container.scrollHeight, behavior: hasScrolledRef.current ? 'smooth' : 'instant' })
    hasScrolledRef.current = true
  }, [messages.length, outgoing?.status])

  return (
    <div ref={scrollRef} className="relative min-h-0 flex-1 overflow-y-auto column-scroll-contain">
      <ol
        role="log"
        aria-live="polite"
        aria-label="Conversation with the Tutor"
        className="mx-auto flex w-full max-w-3xl flex-col gap-4 px-4 py-5"
      >
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
        {outgoing && (
          <ChatMessage
            message={outgoing.message}
            status={outgoing.status}
            error={outgoing.error}
            onRetry={onRetry}
            onEdit={onEdit}
          />
        )}
        {outgoing?.status === 'sending' && <TypingIndicator />}
      </ol>
    </div>
  )
}
