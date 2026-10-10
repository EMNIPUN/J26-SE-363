import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Bot, MessageSquarePlus, RotateCcw, SendHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '../../../shared/auth/useAuth.js'
import Avatar from '../../../shared/components/Avatar.jsx'
import { useTeamPath } from '../../../shared/hooks/useTeamPath.js'
import { CHAT_PROMPTS, CHAT_SESSIONS, CHAT_TRANSCRIPTS, CONCEPTS } from '../data/tutorWorkspace.js'
import SampleBanner from '../components/SampleBanner.jsx'
import TutorMessage from '../components/TutorMessage.jsx'
import { tutorWorkspaceService } from '../services/tutorWorkspaceService.js'

let idCounter = 0
const nextId = () => `msg-${++idCounter}`

export default function Chat() {
  const team = useTeamPath()
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialPrompt = searchParams.get('prompt')
  const initialSession = searchParams.get('session') || 'new'

  const [sessionId, setSessionId] = useState(initialSession)
  const [messages, setMessages] = useState(() => seedMessages(initialSession, initialPrompt))
  const [input, setInput] = useState('')
  const [pending, setPending] = useState(initialPrompt)
  const [failed, setFailed] = useState(null)
  const [context, setContext] = useState(null)
  const [showContext, setShowContext] = useState(false)
  const endRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    tutorWorkspaceService.getRecommendation().then(setContext).catch(() => setContext(null))
  }, [])

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, pending, failed])

  useEffect(() => {
    if (!pending) return
    let live = true
    tutorWorkspaceService
      .sendTutorMessage(pending)
      .then((reply) => {
        if (!live) return
        setMessages((prev) => [...prev, { id: nextId(), ...reply }])
        setPending(null)
        setSearchParams(
          (params) => {
            params.delete('prompt')
            return params
          },
          { replace: true },
        )
      })
      .catch((err) => {
        if (!live) return
        setFailed({ text: pending, message: err.message || 'The sample reply failed.' })
        setPending(null)
      })
    return () => {
      live = false
    }
  }, [pending, setSearchParams])

  const send = (raw) => {
    const text = raw.trim()
    if (!text || pending) return
    setFailed(null)
    setMessages((prev) => [...prev, { id: nextId(), role: 'user', content: text }])
    setInput('')
    setPending(text)
    inputRef.current?.focus()
  }

  const openSession = (nextIdValue) => {
    setSessionId(nextIdValue)
    setMessages(seedMessages(nextIdValue, null))
    setPending(null)
    setFailed(null)
    setInput('')
    setSearchParams(nextIdValue === 'new' ? {} : { session: nextIdValue }, { replace: true })
  }

  const concept = context ? CONCEPTS[context.recommendation.conceptId] : null
  const task = context?.tasks.find((item) => item.id === context.recommendation.taskId)
  const gaps = (context?.estimates || []).filter(
    (item) => item.status === 'Needs Attention' || item.status === 'Developing' || item.status === 'Insufficient Evidence',
  )

  return (
    <div className="space-y-3">
      <SampleBanner />
      <div className="flex h-[calc(100svh-12rem)] min-h-[520px] flex-col overflow-hidden rounded-xl border border-border bg-card xl:flex-row">
        <aside className="hidden w-56 shrink-0 flex-col border-r border-border bg-muted/20 md:flex">
          <div className="p-3">
            <Button className="w-full" onClick={() => openSession('new')}>
              <MessageSquarePlus className="h-4 w-4" />
              New conversation
            </Button>
          </div>
          <ul className="flex-1 space-y-1 overflow-y-auto px-2 pb-3">
            {CHAT_SESSIONS.filter((item) => item.id !== 'new').map((session) => (
              <li key={session.id}>
                <button
                  type="button"
                  onClick={() => openSession(session.id)}
                  aria-current={sessionId === session.id ? 'page' : undefined}
                  className={`w-full rounded-lg px-3 py-2 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                    sessionId === session.id ? 'bg-primary/10 text-foreground' : 'hover:bg-muted'
                  }`}
                >
                  <span className="block truncate text-sm font-medium">{session.title}</span>
                  <span className="text-xs text-muted-foreground">{session.when}</span>
                </button>
              </li>
            ))}
          </ul>
        </aside>

        <section className="flex min-h-0 min-w-0 flex-1 flex-col" aria-label="Tutor conversation">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
            <div>
              <h1 className="text-sm font-semibold">Tutor chat</h1>
              <p className="text-xs text-muted-foreground">One Adaptive Tutor. Replies on this page are sample text.</p>
            </div>
            <div className="flex items-center gap-2">
              <label htmlFor="tutor-session" className="sr-only">
                Conversation
              </label>
              <select
                id="tutor-session"
                value={sessionId}
                onChange={(event) => openSession(event.target.value)}
                className="h-8 rounded-lg border border-input bg-background px-2 text-xs outline-none focus-visible:ring-2 focus-visible:ring-ring md:hidden"
              >
                {CHAT_SESSIONS.map((session) => (
                  <option key={session.id} value={session.id}>
                    {session.title}
                  </option>
                ))}
              </select>
              <Button type="button" variant="outline" size="sm" className="xl:hidden" onClick={() => setShowContext((value) => !value)}>
                {showContext ? 'Hide context' : 'Task context'}
              </Button>
            </div>
          </header>

          <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4" aria-live="polite">
            {messages.map((message) =>
              message.role === 'assistant' ? (
                <div key={message.id} className="flex items-start gap-3">
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                    <Bot className="h-4 w-4" aria-hidden="true" />
                  </span>
                  <div className="max-w-[90%] rounded-2xl rounded-tl-sm border border-border bg-muted/40 px-4 py-3">
                    <TutorMessage content={message.content} />
                  </div>
                </div>
              ) : (
                <div key={message.id} className="flex items-start justify-end gap-3">
                  <div className="max-w-[90%] rounded-2xl rounded-tr-sm bg-primary px-4 py-3 text-sm text-primary-foreground whitespace-pre-line">
                    {message.content}
                  </div>
                  <Avatar name={user?.name} size={32} />
                </div>
              ),
            )}
            {pending && (
              <p className="pl-11 text-sm text-muted-foreground" role="status">
                Preparing a sample reply…
              </p>
            )}
            {failed && (
              <div className="rounded-lg border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm">
                <p>{failed.message}</p>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  className="mt-2"
                  onClick={() => {
                    const text = failed.text
                    setFailed(null)
                    setPending(text)
                  }}
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  Retry
                </Button>
              </div>
            )}
            <div ref={endRef} />
          </div>

          <div className="border-t border-border p-3">
            <div className="mb-2 flex gap-2 overflow-x-auto pb-1">
              {CHAT_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => send(prompt)}
                  className="shrink-0 rounded-full border border-border px-3 py-1 text-xs hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring"
                >
                  {prompt}
                </button>
              ))}
            </div>
            <form
              onSubmit={(event) => {
                event.preventDefault()
                send(input)
              }}
              className="flex items-end gap-2"
            >
              <label htmlFor="tutor-input" className="sr-only">
                Message the Adaptive Tutor
              </label>
              <textarea
                id="tutor-input"
                ref={inputRef}
                rows={2}
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    send(input)
                  }
                }}
                placeholder="Ask a software engineering question, or ask about the sample task."
                className="min-h-11 flex-1 resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <Button type="submit" size="icon" disabled={!input.trim() || Boolean(pending)} aria-label="Send message">
                <SendHorizontal className="h-4 w-4" />
              </Button>
            </form>
          </div>
        </section>

        <aside className={`${showContext ? 'flex' : 'hidden'} max-h-64 shrink-0 flex-col gap-3 overflow-y-auto border-t border-border p-4 xl:flex xl:max-h-none xl:w-72 xl:border-t-0 xl:border-l`}>
          <h2 className="text-sm font-semibold">Current sample context</h2>
          {context ? (
            <>
              <p className="text-sm">{context.project.name}</p>
              <p className="text-xs text-muted-foreground">{context.project.sprintName}</p>
              <div>
                <p className="text-xs font-medium">Selected task</p>
                <p className="text-sm">{task?.title}</p>
                <p className="text-xs text-muted-foreground">{task?.status}</p>
              </div>
              <div>
                <p className="text-xs font-medium">Related concept</p>
                <p className="text-sm">{concept?.label}</p>
                <p className="text-xs text-muted-foreground">{concept?.status}</p>
              </div>
              <div>
                <p className="text-xs font-medium">Knowledge gaps in the snapshot</p>
                <ul className="mt-1 space-y-1 text-xs text-muted-foreground">
                  {gaps.map((item) => (
                    <li key={item.conceptId}>
                      {CONCEPTS[item.conceptId]?.label}: {item.status}
                    </li>
                  ))}
                </ul>
              </div>
              <Button asChild variant="outline" size="sm">
                <Link to={team('/tutor/guidance')}>Open sprint guidance</Link>
              </Button>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Context will appear when the sample workspace loads.</p>
          )}
        </aside>
      </div>
    </div>
  )
}

function seedMessages(sessionId, prompt) {
  const stored = CHAT_TRANSCRIPTS[sessionId] || []
  const base =
    stored.length > 0
      ? stored.map((message) => ({ ...message }))
      : [
          {
            id: 'welcome',
            role: 'assistant',
            content:
              'Sample reply, not from the tutor service.\n\nAsk about the campus portal task, a concept such as JWT, or a general software engineering question. I will answer from the sample project context.',
          },
        ]
  if (prompt) base.push({ id: 'prompt', role: 'user', content: prompt })
  return base
}
