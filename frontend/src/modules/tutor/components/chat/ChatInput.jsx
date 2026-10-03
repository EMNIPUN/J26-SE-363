import { forwardRef, useId, useLayoutEffect, useRef } from 'react'
import { SendHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { MAX_MESSAGE_LENGTH } from '../../utils/constants.js'

const MAX_TEXTAREA_HEIGHT_PX = 160
const COUNTER_THRESHOLD = Math.floor(MAX_MESSAGE_LENGTH * 0.8)

const ChatInput = forwardRef(function ChatInput({ value, onChange, onSubmit, disabled, canSend }, forwardedRef) {
  const inputId = useId()
  const hintId = useId()
  const localRef = useRef(null)

  const setRefs = (node) => {
    localRef.current = node
    if (typeof forwardedRef === 'function') forwardedRef(node)
    else if (forwardedRef) forwardedRef.current = node
  }

  useLayoutEffect(() => {
    const textarea = localRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_TEXTAREA_HEIGHT_PX)}px`
  }, [value])

  const sendEnabled = canSend && !disabled && value.trim().length > 0

  const submit = () => {
    if (sendEnabled) onSubmit()
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <div>
      <form
        onSubmit={(event) => {
          event.preventDefault()
          submit()
        }}
        className="flex items-end gap-2 rounded-xl border border-input bg-background py-1.5 pl-3 pr-1.5 transition-shadow focus-within:border-ring focus-within:ring-2 focus-within:ring-ring/30"
      >
        <label htmlFor={inputId} className="sr-only">
          Message the Tutor
        </label>
        <textarea
          ref={setRefs}
          id={inputId}
          rows={1}
          value={value}
          maxLength={MAX_MESSAGE_LENGTH}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          aria-describedby={hintId}
          placeholder="Ask about your task, a concept, or your code…"
          className="min-h-8 flex-1 resize-none bg-transparent py-1 text-sm leading-6 text-foreground outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-60"
        />
        <Button type="submit" size="icon" className="h-8 w-8 shrink-0" disabled={!sendEnabled} aria-label="Send message">
          <SendHorizontal aria-hidden="true" />
        </Button>
      </form>
      <div className="mt-1.5 flex items-center gap-2 px-1 text-[11px] text-muted-foreground">
        <span id={hintId} className="hidden @2xl:inline">
          Enter to send · Shift + Enter for a new line
        </span>
        {value.length >= COUNTER_THRESHOLD && (
          <span className="ml-auto tabular-nums" aria-live="polite">
            {value.length}/{MAX_MESSAGE_LENGTH}
          </span>
        )}
      </div>
    </div>
  )
})

export default ChatInput
