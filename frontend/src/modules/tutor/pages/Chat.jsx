import { useEffect, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import {
  ArrowLeft,
  Bot,
  ChevronRight,
  Copy,
  MessageSquarePlus,
  SendHorizontal,
  ThumbsDown,
  ThumbsUp,
} from 'lucide-react'
import { useAuth } from '../../../shared/auth/useAuth.js'
import Avatar from '../../../shared/components/Avatar.jsx'
import { showToast } from '../../../shared/utils/toast.jsx'
import { Button } from '@/components/ui/button'
import AgentChip from '../components/AgentChip.jsx'
import { SESSIONS, SUGGESTED_PROMPTS, mockAgentReply } from '../data/mockTutorData.js'

let idCounter = 0
const nextId = (prefix) => `${prefix}-${++idCounter}`

function welcomeMessages(sessionId, prompt) {
  const session = SESSIONS.find((s) => s.id === sessionId)
  const intro = session
    ? {
        id: nextId('bot'),
        role: 'assistant',
        agent: session.agent,
        content: `Welcome back! Last time we worked on “${session.title}”. Where would you like to pick up?`,
      }
    : {
        id: nextId('bot'),
        role: 'assistant',
        agent: 'learning',
        content:
          'Hi! I’m your Tutor Agent. Ask me about your requirements, estimates, sprint tasks or security findings — I’ll explain the concepts and help you plan your next step.',
      }
  return prompt ? [intro, { id: nextId('user'), role: 'user', content: prompt }] : [intro]
}

export default function Chat() {
  const { teamId } = useParams()
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialPrompt = searchParams.get('prompt')
  const initialSession = searchParams.get('session')

  const [activeSessionId, setActiveSessionId] = useState(initialSession || 'new')
  const [messages, setMessages] = useState(() => welcomeMessages(initialSession, initialPrompt))
  const [pendingPrompt, setPendingPrompt] = useState(initialPrompt)
  const [input, setInput] = useState('')
  const [feedback, setFeedback] = useState({})
  const endRef = useRef(null)
  const inputRef = useRef(null)

  const isTyping = pendingPrompt != null

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, isTyping])

  useEffect(() => {
    if (pendingPrompt == null) return
    const timer = setTimeout(() => {
      const reply = mockAgentReply(pendingPrompt)
      setMessages((prev) => [...prev, { id: nextId('bot'), role: 'assistant', ...reply }])
      setPendingPrompt(null)
      setSearchParams(
        (params) => {
          params.delete('prompt')
          return params
        },
        { replace: true },
      )
    }, 900)
    return () => clearTimeout(timer)
  }, [pendingPrompt, setSearchParams])

  const send = (raw) => {
    const text = raw.trim()
    if (!text || isTyping) return
    setMessages((prev) => [...prev, { id: nextId('user'), role: 'user', content: text }])
    setInput('')
    setPendingPrompt(text)
    inputRef.current?.focus()
  }

  const openSession = (sessionId) => {
    setActiveSessionId(sessionId)
    setMessages(welcomeMessages(sessionId === 'new' ? null : sessionId, null))
    setPendingPrompt(null)
    setInput('')
    setSearchParams(sessionId === 'new' ? {} : { session: sessionId }, { replace: true })
  }

  const copyMessage = async (content) => {
    try {
      await navigator.clipboard.writeText(content)
      showToast.success('Copied to clipboard')
    } catch {
      showToast.error('Could not copy the message')
    }
  }

  const rate = (id, value) => {
    setFeedback((prev) => ({ ...prev, [id]: value }))
    showToast.info('Thanks for the feedback', {
      description: 'It helps the Tutor Agent adapt its explanations to you.',
    })
  }

  const showSuggestions = messages.filter((m) => m.role === 'user').length === 0 && !isTyping

  return (
    <div className="flex h-[calc(100svh-7rem)] lg:h-[calc(100svh-8rem)] min-h-[520px] overflow-hidden rounded-xl border border-border/60 bg-card card-elevated">
      <aside className="hidden md:flex w-64 shrink-0 flex-col border-r border-border bg-muted/20">
        <div className="p-3 border-b border-border">
          <Button className="w-full" size="lg" onClick={() => openSession('new')}>
            <MessageSquarePlus className="h-4 w-4" />
            New session
          </Button>
        </div>
        <p className="px-4 pt-4 pb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          Recent sessions
        </p>
        <ul className="flex-1 min-h-0 overflow-y-auto px-2 pb-3 space-y-0.5 column-scroll-contain">
          {SESSIONS.map((s) => {
            const isActive = activeSessionId === s.id
            return (
              <li key={s.id}>
                <button
                  type="button"
                  onClick={() => openSession(s.id)}
                  aria-current={isActive ? 'true' : undefined}
                  className={`w-full rounded-lg px-3 py-2 text-left transition-colors cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                    isActive ? 'bg-accent text-accent-foreground' : 'hover:bg-muted'
                  }`}
                >
                  <span className="block truncate text-sm font-medium">{s.title}</span>
                  <span className="block text-[11px] text-muted-foreground">{s.when}</span>
                </button>
              </li>
            )
          })}
        </ul>
      </aside>

      <section className="flex min-w-0 flex-1 flex-col" aria-label="Tutor conversation">
        <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-border px-4">
          <div className="flex min-w-0 items-center gap-3">
            <Button asChild variant="ghost" size="icon" className="h-8 w-8 shrink-0" aria-label="Back to Tutor Agent dashboard">
              <Link to={`/teams/${teamId}/tutor/landing`}>
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </Button>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-foreground">
                {SESSIONS.find((s) => s.id === activeSessionId)?.title || 'New session'}
              </p>
              <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                Tutor Agent is online
              </p>
            </div>
          </div>
          <Button variant="outline" size="sm" className="md:hidden" onClick={() => openSession('new')}>
            <MessageSquarePlus className="h-3.5 w-3.5" />
            New
          </Button>
        </header>

        <div className="flex-1 min-h-0 overflow-y-auto px-4 py-6 sm:px-6 column-scroll-contain" aria-live="polite">
          <div className="mx-auto flex max-w-3xl flex-col gap-5">
            {messages.map((msg) =>
              msg.role === 'assistant' ? (
                <div key={msg.id} className="flex items-start gap-3 animate-fade-rise">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                    <Bot className="h-4 w-4" />
                  </span>
                  <div className="min-w-0 max-w-[85%] space-y-1.5">
                    <AgentChip agent={msg.agent} />
                    <div className="rounded-2xl rounded-tl-sm border border-border/60 bg-muted/50 px-4 py-3 text-sm leading-relaxed text-foreground whitespace-pre-line">
                      {msg.content}
                    </div>
                    <div className="flex items-center gap-0.5 text-muted-foreground">
                      <button
                        type="button"
                        onClick={() => copyMessage(msg.content)}
                        className="rounded-md p-1.5 hover:bg-muted hover:text-foreground cursor-pointer"
                        aria-label="Copy message"
                      >
                        <Copy className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => rate(msg.id, 'up')}
                        className={`rounded-md p-1.5 hover:bg-muted hover:text-foreground cursor-pointer ${feedback[msg.id] === 'up' ? 'text-primary' : ''}`}
                        aria-label="Helpful"
                        aria-pressed={feedback[msg.id] === 'up'}
                      >
                        <ThumbsUp className="h-3.5 w-3.5" />
                      </button>
                      <button
                        type="button"
                        onClick={() => rate(msg.id, 'down')}
                        className={`rounded-md p-1.5 hover:bg-muted hover:text-foreground cursor-pointer ${feedback[msg.id] === 'down' ? 'text-destructive' : ''}`}
                        aria-label="Not helpful"
                        aria-pressed={feedback[msg.id] === 'down'}
                      >
                        <ThumbsDown className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <div key={msg.id} className="flex items-start justify-end gap-3 animate-fade-rise">
                  <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-primary px-4 py-3 text-sm leading-relaxed text-primary-foreground whitespace-pre-line">
                    {msg.content}
                  </div>
                  <Avatar name={user?.name} size={32} />
                </div>
              ),
            )}

            {isTyping && (
              <div className="flex items-start gap-3 animate-fade-rise">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <Bot className="h-4 w-4" />
                </span>
                <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm border border-border/60 bg-muted/50 px-4 py-3">
                  <span className="sr-only">Tutor Agent is typing</span>
                  <span className="h-1.5 w-1.5 rounded-full bg-primary/70 animate-bounce" />
                  <span className="h-1.5 w-1.5 rounded-full bg-primary/70 animate-bounce [animation-delay:0.2s]" />
                  <span className="h-1.5 w-1.5 rounded-full bg-primary/70 animate-bounce [animation-delay:0.4s]" />
                </div>
              </div>
            )}

            {showSuggestions && (
              <div className="grid gap-2 pt-2 sm:grid-cols-2 sm:pl-11">
                {SUGGESTED_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    onClick={() => send(prompt)}
                    className="group flex items-center justify-between gap-2 rounded-lg border border-border/60 bg-card px-3 py-2.5 text-left text-sm text-foreground transition-colors hover:bg-muted cursor-pointer active:scale-[0.99]"
                  >
                    <span>{prompt}</span>
                    <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5" />
                  </button>
                ))}
              </div>
            )}
            <div ref={endRef} />
          </div>
        </div>

        <div className="shrink-0 border-t border-border p-3 sm:p-4">
          <form
            onSubmit={(e) => {
              e.preventDefault()
              send(input)
            }}
            className="mx-auto flex max-w-3xl items-end gap-2 rounded-xl border border-input bg-background p-2 focus-within:ring-2 focus-within:ring-ring/40"
          >
            <label htmlFor="tutor-input" className="sr-only">
              Message the Tutor Agent
            </label>
            <textarea
              id="tutor-input"
              ref={inputRef}
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  send(input)
                }
              }}
              placeholder="Ask about your sprint, a concept, or a finding…"
              className="max-h-40 min-h-9 flex-1 resize-none bg-transparent px-2 py-2 text-sm text-foreground placeholder:text-muted-foreground outline-none field-sizing-content"
            />
            <Button type="submit" size="icon-lg" disabled={!input.trim() || isTyping} aria-label="Send message">
              <SendHorizontal className="h-4 w-4" />
            </Button>
          </form>
          <p className="mt-2 text-center text-[11px] text-muted-foreground">
            Press Enter to send · Shift + Enter for a new line
          </p>
        </div>
      </section>
    </div>
  )
}
