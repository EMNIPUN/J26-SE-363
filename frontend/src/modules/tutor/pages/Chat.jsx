import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Bot, ChevronDown, ChevronRight, RotateCcw, SendHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '../../../shared/auth/useAuth.js'
import Avatar from '../../../shared/components/Avatar.jsx'
import { useTeamPath } from '../../../shared/hooks/useTeamPath.js'
import LivePipelineBanner from '../components/LivePipelineBanner.jsx'
import TutorMessage from '../components/TutorMessage.jsx'
import { tutorApi } from '../services/tutorApi.js'

let idCounter = 0
const nextId = () => `msg-${++idCounter}`

const WELCOME =
  'Live Adaptive Tutor chat (PP1).\n\nMessages go to Core → AI Backend → SLAP MCP for performance evidence. No adaptive decision is produced yet — replies summarize retrieved evidence.'

export default function Chat() {
  const team = useTeamPath()
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialPrompt = searchParams.get('prompt')

  const [messages, setMessages] = useState(() => {
    const base = [{ id: 'welcome', role: 'assistant', content: WELCOME }]
    if (initialPrompt) base.push({ id: 'prompt', role: 'user', content: initialPrompt })
    return base
  })
  const [input, setInput] = useState('')
  const [pending, setPending] = useState(initialPrompt || null)
  const [failed, setFailed] = useState(null)
  const [lastEvidence, setLastEvidence] = useState([])
  const [showEvidence, setShowEvidence] = useState(true)
  const endRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, pending, failed, lastEvidence])

  useEffect(() => {
    if (!pending) return
    let live = true
    tutorApi
      .chat({ message: pending })
      .then((body) => {
        if (!live) return
        // apiClient already unwraps axios response.data
        const result = body?.result || {}
        const evidence = result.performance_evidence || []
        const normalized = result.normalized_evidence || []
        setLastEvidence(evidence)

        const lines = [
          body?.status === 'completed'
            ? 'Tutor MCP retrieval completed.'
            : `Tutor response status: ${body?.status || 'unknown'}.`,
          '',
          `Performance evidence records: ${evidence.length}`,
          `Normalized evidence items: ${normalized.length}`,
          `Learning activities: ${(result.learning_activities || []).length}`,
          '',
          result.adaptive_decision == null
            ? 'adaptive_decision: null (decision engine not in PP1).'
            : `adaptive_decision: ${JSON.stringify(result.adaptive_decision)}`,
        ]
        if (body?.error?.message) {
          lines.push('', `Error: ${body.error.message}`)
        }
        if (result.detail) {
          lines.push('', String(result.detail))
        }

        setMessages((prev) => [
          ...prev,
          { id: nextId(), role: 'assistant', content: lines.join('\n') },
        ])
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
        setFailed({ text: pending, message: err.message || 'Tutor chat failed.' })
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

  return (
    <div className="space-y-3">
      <LivePipelineBanner mode="live" />
      <div className="flex h-[calc(100svh-12rem)] min-h-[520px] flex-col overflow-hidden rounded-xl border border-border bg-card xl:flex-row">
        <section className="flex min-h-0 min-w-0 flex-1 flex-col" aria-label="Tutor conversation">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-3">
            <div>
              <h1 className="text-sm font-semibold">Tutor chat</h1>
              <p className="text-xs text-muted-foreground">
                Live MCP evidence path. Adaptive decisions are not produced yet.
              </p>
            </div>
            <Button asChild variant="outline" size="sm">
              <Link to={team('/tutor/guidance')}>Sprint guidance</Link>
            </Button>
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
                  <Avatar name={user?.name} picture={user?.picture} size={32} />
                </div>
              ),
            )}
            {pending && (
              <p className="pl-11 text-sm text-muted-foreground" role="status">
                Calling Core tutor chat (mint + MCP)…
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
                placeholder="Ask anything — the reply will report MCP evidence retrieval for PP1."
                className="min-h-11 flex-1 resize-none rounded-lg border border-input bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
              />
              <Button
                type="submit"
                size="icon"
                loading={Boolean(pending)}
                disabled={!input.trim()}
                aria-label="Send message"
              >
                <SendHorizontal className="h-4 w-4" />
              </Button>
            </form>
          </div>
        </section>

        <aside className="flex max-h-64 shrink-0 flex-col gap-3 overflow-y-auto border-t border-border p-4 xl:max-h-none xl:w-80 xl:border-t-0 xl:border-l">
          <button
            type="button"
            className="flex items-center gap-1 text-left text-sm font-semibold"
            onClick={() => setShowEvidence((value) => !value)}
          >
            {showEvidence ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            Evidence retrieved
          </button>
          {showEvidence ? (
            lastEvidence.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Send a message to fetch live MCP performance evidence for the linked student.
              </p>
            ) : (
              <ul className="space-y-2">
                {lastEvidence.map((row) => (
                  <li key={row.id} className="rounded-lg border border-border px-3 py-2 text-xs">
                    <p className="font-medium">{row.sourceType || row.source_type}</p>
                    <p className="text-muted-foreground">
                      status={row.status} · score={row.score ?? 'null'}/{row.maxScore ?? row.max_score ?? '—'}
                    </p>
                    <p className="mt-1 truncate font-mono text-[10px] text-muted-foreground">
                      concept={row.conceptId || row.concept_id || 'null'}
                    </p>
                  </li>
                ))}
              </ul>
            )
          ) : null}
        </aside>
      </div>
    </div>
  )
}
