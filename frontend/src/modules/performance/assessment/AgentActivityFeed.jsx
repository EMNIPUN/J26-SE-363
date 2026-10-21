import React, { useState, useMemo, useRef, useEffect } from 'react'
import PropTypes from 'prop-types'
import { ChevronRight, AlertTriangle, UserCheck } from 'lucide-react'
import { Button } from '@/components/ui/button'
import IdentityDecision from './IdentityDecision.jsx'

/** Ticks every 100 ms while a step is running, to show how long it has taken (e.g. 1.4). */
function useLiveElapsed(isActive, startTs) {
  const [elapsed, setElapsed] = useState('0.0')

  useEffect(() => {
    if (!isActive) return undefined
    const t0 = startTs ? new Date(startTs).getTime() : Date.now()
    const interval = setInterval(() => setElapsed(((Date.now() - t0) / 1000).toFixed(1)), 100)
    return () => clearInterval(interval)
  }, [isActive, startTs])

  return elapsed
}

/** The one quiet sign that a step is still running. */
function ActiveDot() {
  return (
    <span className="relative flex h-2 w-2 shrink-0" aria-hidden="true">
      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary/50" />
      <span className="relative inline-flex h-2 w-2 rounded-full bg-primary" />
    </span>
  )
}

function Chevron({ open }) {
  return <ChevronRight className={`h-3.5 w-3.5 shrink-0 text-muted-foreground/70 transition-transform duration-150 ${open ? 'rotate-90' : ''}`} aria-hidden="true" />
}
Chevron.propTypes = { open: PropTypes.bool }

const ROW = 'group flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left transition-colors'
// the step that is running stands out from the tinted stream: white, lifted, with an accent edge
const ACTIVE = 'rounded-md border-l-2 border-l-primary bg-card shadow-sm'
const TIME = 'shrink-0 text-xs tabular-nums text-muted-foreground'

/** The model's reasoning: plain, muted text under a one-line header, with a thin rule down the left when open. */
function ThoughtItem({ event, isExpanded, onToggle, isActive = false }) {
  const text = event.payload?.thinking || event.message || ''
  const duration = event.payload?.duration ? Number(event.payload.duration).toFixed(1) : null
  const summary = event.payload?.summary || event.message || 'Reasoning'
  const liveElapsed = useLiveElapsed(isActive, event.ts)

  return (
    <div className={`animate-fade-rise ${isActive ? ACTIVE : ''}`}>
      <button type="button" onClick={onToggle} aria-expanded={isExpanded} className={`${ROW} hover:bg-muted`}>
        <Chevron open={isExpanded} />
        <span className={`min-w-0 flex-1 truncate text-sm ${isActive ? 'font-medium text-foreground' : 'text-muted-foreground'}`}>{summary}</span>
        {isActive ? <><ActiveDot /><span className={TIME}>{liveElapsed}s</span></> : duration && <span className={TIME}>{duration}s</span>}
      </button>
      {isExpanded && text && (
        <div className="ml-[15px] mt-0.5 mb-1.5 select-text whitespace-pre-wrap break-words border-l-2 border-muted-foreground/30 pl-4 text-[13px] leading-relaxed text-muted-foreground">
          {text}
        </div>
      )}
    </div>
  )
}

ThoughtItem.propTypes = {
  event: PropTypes.object.isRequired,
  isExpanded: PropTypes.bool,
  onToggle: PropTypes.func,
  isActive: PropTypes.bool,
}

/** One action the agent took: a single line (what it did, on what, and the result), with the input and result one click away. */
function ToolCallItem({ event, isExpanded, onToggle, isActive = false }) {
  let rawName = event.payload?.tool
  let messageSummary = ''

  if (!rawName && event.message?.includes(':')) {
    const colonIdx = event.message.indexOf(':')
    rawName = event.message.slice(0, colonIdx).trim()
    messageSummary = event.message.slice(colonIdx + 1).trim()
  } else if (event.message?.includes(':')) {
    const colonIdx = event.message.indexOf(':')
    messageSummary = event.message.slice(colonIdx + 1).trim()
  } else if (!rawName) {
    rawName = event.message || 'tool'
  }

  const toolName = String(rawName).replace(/^tool call:\s*/i, '').replace(/^tool:\s*/i, '').trim()

  const args = useMemo(() => event.payload?.args || {}, [event.payload?.args])
  const payloadOutput = event.payload?.output ?? event.payload?.output_preview ?? event.payload?.result ?? ''
  const payloadSummary = event.payload?.summary ?? ''
  const liveElapsed = useLiveElapsed(isActive, event.ts)

  // the short result shown on the line, e.g. "read-only mirror up to date", "12 tasks for 4 students"
  let inlineSummary = payloadSummary || messageSummary
  if (!inlineSummary && typeof payloadOutput === 'string' && payloadOutput.length > 0 && !payloadOutput.includes('\n')) {
    inlineSummary = payloadOutput.trim()
  }

  let fullOutput = payloadOutput || messageSummary || payloadSummary || ''
  if (typeof fullOutput === 'object' && fullOutput !== null) {
    try {
      fullOutput = JSON.stringify(fullOutput, null, 2)
    } catch {
      fullOutput = String(fullOutput)
    }
  } else {
    fullOutput = String(fullOutput || '').trim()
  }

  const argSummary = useMemo(() => {
    if (args.path) return `${args.path}${args.lines ? `:${args.lines}` : ''}`
    if (args.query) return `"${args.query}"`
    if (args.sha) return `commit ${String(args.sha).slice(0, 8)}`
    if (args.sprint_id) return `sprint: ${args.sprint_id}`
    if (args.task_id) return `task: ${args.task_id}`
    if (args.student_id) return `student: ${args.student_id}`
    const keys = Object.keys(args)
    if (keys.length === 1 && typeof args[keys[0]] === 'string') {
      return `${keys[0]}: ${args[keys[0]]}`
    }
    return ''
  }, [args])

  // do not say the same thing twice
  if (inlineSummary === argSummary || inlineSummary.toLowerCase() === toolName.toLowerCase()) {
    inlineSummary = ''
  }

  const hasArgs = Object.keys(args).length > 0
  const hasOutput = Boolean(fullOutput)
  const hasDetails = hasArgs || hasOutput
  const label = toolName.replace(/_/g, ' ')

  const line = (
    <>
      {hasDetails ? <Chevron open={isExpanded} /> : <span className="w-3.5 shrink-0" />}
      <span className={`shrink-0 text-sm capitalize ${isActive ? 'font-medium text-foreground' : 'text-foreground/90'}`}>{label}</span>
      {argSummary && <span className="min-w-0 max-w-[45%] shrink truncate font-mono text-xs text-muted-foreground">{argSummary}</span>}
      {!isActive && inlineSummary && <span className="min-w-0 flex-1 truncate text-xs text-muted-foreground">{inlineSummary}</span>}
      {(isActive || !inlineSummary) && <span className="flex-1" />}
      {isActive && <><ActiveDot /><span className={TIME}>{liveElapsed}s</span></>}
    </>
  )

  return (
    <div className={`animate-fade-rise ${isActive ? ACTIVE : ''}`}>
      {hasDetails ? (
        <button type="button" onClick={onToggle} aria-expanded={isExpanded} className={`${ROW} hover:bg-muted`}>{line}</button>
      ) : (
        <div className={ROW}>{line}</div>
      )}

      {isExpanded && hasDetails && (
        <div className="ml-[15px] mt-0.5 mb-1.5 space-y-3 overflow-hidden rounded-md border bg-card p-3">
          {hasArgs && (
            <div>
              <p className="mb-1 text-[11px] font-medium text-muted-foreground">Input</p>
              <pre className="whitespace-pre-wrap break-all font-mono text-[11.5px] leading-relaxed text-foreground/80">{JSON.stringify(args, null, 2)}</pre>
            </div>
          )}
          {hasOutput && (
            <div>
              <p className="mb-1 text-[11px] font-medium text-muted-foreground">Result</p>
              <pre className="max-h-60 overflow-y-auto whitespace-pre-wrap break-all font-mono text-[11.5px] leading-relaxed text-foreground/80">{fullOutput}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

ToolCallItem.propTypes = {
  event: PropTypes.object.isRequired,
  isExpanded: PropTypes.bool,
  onToggle: PropTypes.func,
  isActive: PropTypes.bool,
}

const VERDICTS = {
  met: { label: 'Met', accent: 'border-l-emerald-500', text: 'text-emerald-700 dark:text-emerald-400' },
  partly: { label: 'Partly met', accent: 'border-l-amber-500', text: 'text-amber-700 dark:text-amber-400' },
  not_met: { label: 'Not met', accent: 'border-l-rose-500', text: 'text-rose-700 dark:text-rose-400' },
}

/** A conclusion the agent reached. The only item drawn as a card, because it is what the lecturer reads for. */
function DecisionItem({ event, isExpanded, onToggle }) {
  const verdictKey = event.payload?.verdict || 'completed'
  const verdict = VERDICTS[verdictKey] || { label: 'Completed', accent: 'border-l-border', text: 'text-muted-foreground' }
  const reason = event.payload?.reason || event.message || ''
  const evidence = event.payload?.evidence || []
  const hasDetails = Boolean(reason) || evidence.length > 0

  return (
    <div className={`animate-fade-rise my-1.5 overflow-hidden rounded-lg border border-l-2 bg-card ${verdict.accent}`}>
      <button type="button" onClick={hasDetails ? onToggle : undefined} aria-expanded={hasDetails ? isExpanded : undefined} className={`flex w-full items-start gap-2 px-3 py-2 text-left ${hasDetails ? 'cursor-pointer hover:bg-muted/40' : 'cursor-default'}`}>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-baseline gap-x-2">
            <span className="text-sm font-medium text-foreground">{event.message || 'Verdict'}</span>
            <span className={`text-xs font-medium ${verdict.text}`}>{verdict.label}</span>
          </div>
          {!isExpanded && reason && <p className="mt-0.5 truncate text-xs text-muted-foreground">{reason}</p>}
        </div>
        {hasDetails && <span className="mt-0.5"><Chevron open={isExpanded} /></span>}
      </button>

      {isExpanded && (
        <div className="space-y-3 border-t px-3 py-2.5">
          {reason && <p className="whitespace-pre-wrap break-words text-[13px] leading-relaxed text-foreground/85">{reason}</p>}
          {evidence.length > 0 && (
            <div>
              <p className="mb-1.5 text-[11px] font-medium text-muted-foreground">Evidence</p>
              <ul className="divide-y rounded-md border">
                {evidence.map((ev, i) => (
                  <li key={i} className="flex items-baseline gap-3 px-2.5 py-1.5 text-xs">
                    <span className="shrink-0 font-mono text-muted-foreground">{String(ev.sha || '').slice(0, 7)}</span>
                    <span className="min-w-0 flex-1 break-all font-mono text-foreground/85">{ev.path}</span>
                    <span className="shrink-0 whitespace-nowrap tabular-nums text-muted-foreground">lines {ev.lines}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

DecisionItem.propTypes = {
  event: PropTypes.object.isRequired,
  isExpanded: PropTypes.bool,
  onToggle: PropTypes.func,
}

/** The agent's last word on one student: the explanation of the mark in plain prose, always open (it is the answer, not a step). */
function SummaryItem({ event, names }) {
  const { student, mark, text, brief } = event.payload || {}
  const who = names?.[student] || student || ''
  return (
    <div className="animate-fade-rise my-2 rounded-lg border bg-card px-4 py-3 shadow-sm">
      <div className="flex items-baseline justify-between gap-3">
        <p className="min-w-0 truncate text-xs font-medium text-muted-foreground">Summary{who ? ` for ${who}` : ''}</p>
        {mark != null && <p className="shrink-0 text-xs text-muted-foreground">Predicted mark <span className="text-sm font-semibold tabular-nums text-foreground">{Math.round(mark)}</span></p>}
      </div>
      {text && <p className="mt-1.5 select-text text-sm leading-relaxed text-foreground">{text}</p>}
      {brief && brief !== text && <p className="mt-2 select-text text-[13px] leading-relaxed text-muted-foreground">{brief}</p>}
    </div>
  )
}

SummaryItem.propTypes = {
  event: PropTypes.object.isRequired,
  names: PropTypes.object,
}

/** A plain progress line. */
function LogItem({ event }) {
  const isWarn = event.level === 'warn' || event.type === 'node_wait'
  return (
    <div className={`flex items-center gap-2 px-2 py-1 text-xs ${isWarn ? 'text-amber-700 dark:text-amber-400' : 'text-muted-foreground'}`}>
      {isWarn ? <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" /> : <span className="w-3.5 shrink-0" />}
      <span className="min-w-0 flex-1 truncate">{event.message || event.type}</span>
    </div>
  )
}

LogItem.propTypes = {
  event: PropTypes.object.isRequired,
}

const STATUS = { running: 'Working', waiting_human: 'Waiting for your review', succeeded: 'Finished', failed: 'Failed', queued: 'Queued' }

/** What the agent is doing, step by step: its reasoning, the actions it took and the conclusions it reached. */
export default function AgentActivityFeed({
  events = [],
  current,
  identityReview,
  runId,
  onReviewDone,
  names = {},
}) {
  const [openReviewDialog, setOpenReviewDialog] = useState(false)
  const [userOverrides, setUserOverrides] = useState({})
  const [globalExpandMode, setGlobalExpandMode] = useState(null) // 'all' | 'none' | null
  const [autoScroll, setAutoScroll] = useState(true)
  const scrollRef = useRef(null)

  // De-duplicate paired thinking events & filter silent internal markers
  const displayEvents = useMemo(() => {
    const list = []
    const seenThinking = new Set()

    for (const e of events) {
      if (e.type === 'node_start' || e.type === 'node_end' || e.type === 'produce') continue
      if (e.type === 'result' || e.message === 'result') continue

      const isThinking = e.type === 'thinking' || Boolean(e.payload?.thinking)
      if (isThinking) {
        const txt = (e.payload?.thinking || e.message || '').trim()
        if (seenThinking.has(txt)) continue
        seenThinking.add(txt)
      }
      list.push(e)
    }
    return list
  }, [events])

  const totalThoughts = useMemo(() => {
    return displayEvents.filter(e => e.type === 'thinking' || e.payload?.thinking).length
  }, [displayEvents])

  // Identify the currently active executing event (the last event while run is 'running')
  const activeEventSeq = useMemo(() => {
    if (current !== 'running' || displayEvents.length === 0) return null
    return displayEvents[displayEvents.length - 1].seq
  }, [current, displayEvents])

  // Track all tool execution events
  const toolEvents = useMemo(() => {
    return displayEvents.filter(e => e.type === 'tool' || e.type === 'rf_tool')
  }, [displayEvents])

  // Automatically track the latest finished tool execution:
  // When an execution finishes running, its output expands automatically.
  // When the next execution finishes and its output arrives, the previous one collapses.
  const latestFinishedToolSeq = useMemo(() => {
    if (toolEvents.length === 0) return null
    const lastTool = toolEvents[toolEvents.length - 1]
    if (current === 'running' && lastTool.seq === activeEventSeq) {
      // The last tool is currently actively running; the one before it is the latest finished
      return toolEvents.length > 1 ? toolEvents[toolEvents.length - 2].seq : null
    }
    // The last tool has finished running
    return lastTool.seq
  }, [toolEvents, current, activeEventSeq])

  // Track thoughts
  const thoughtEvents = useMemo(() => {
    return displayEvents.filter(e => e.type === 'thinking' || Boolean(e.payload?.thinking))
  }, [displayEvents])

  const latestFinishedThoughtSeq = useMemo(() => {
    if (thoughtEvents.length === 0) return null
    const lastThought = thoughtEvents[thoughtEvents.length - 1]
    if (current === 'running' && lastThought.seq === activeEventSeq) {
      return thoughtEvents.length > 1 ? thoughtEvents[thoughtEvents.length - 2].seq : null
    }
    return lastThought.seq
  }, [thoughtEvents, current, activeEventSeq])

  // Determine whether an item should be expanded
  const isItemExpanded = (e) => {
    if (globalExpandMode === 'all') return true
    if (globalExpandMode === 'none') return false

    // Explicit manual click by user takes precedence
    if (userOverrides[e.seq] !== undefined) {
      return userOverrides[e.seq]
    }

    const isTool = e.type === 'tool' || e.type === 'rf_tool'
    const isThinking = e.type === 'thinking' || Boolean(e.payload?.thinking)
    const isDecision = e.type === 'decision' || e.type === 'rf_decision'

    // Automatically expand the latest finished tool output; previous ones collapse
    if (isTool) {
      return e.seq === latestFinishedToolSeq
    }
    if (isThinking) {
      return e.seq === latestFinishedThoughtSeq
    }
    if (isDecision) {
      return true
    }
    return false
  }

  const toggleExpand = (seq, currentVal) => {
    setGlobalExpandMode(null)
    setUserOverrides(prev => ({
      ...prev,
      [seq]: !currentVal
    }))
  }

  // Expand / Collapse All items
  const toggleAll = (shouldExpand) => {
    setGlobalExpandMode(shouldExpand ? 'all' : 'none')
    setUserOverrides({})
  }

  // User scroll detection
  const handleScroll = (e) => {
    const el = e.currentTarget
    const isAtBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 50
    setAutoScroll(isAtBottom)
  }

  // Auto-scroll to bottom only if user hasn't scrolled up, and follow new expanded items
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [displayEvents.length, latestFinishedToolSeq, autoScroll])

  const isReviewActive = current === 'waiting_human' && Boolean(identityReview)
  const status = STATUS[current] || (current ? current.replace(/_/g, ' ') : 'Idle')

  return (
    <div className="flex h-full w-full max-w-full flex-col overflow-hidden rounded-xl border border-foreground/15 bg-card text-card-foreground shadow-sm">
      <div className="flex shrink-0 items-center justify-between gap-3 border-b px-4 py-2.5">
        <div className="flex min-w-0 items-baseline gap-2">
          <h3 className="text-sm font-semibold text-foreground">Live reasoning trace</h3>
          <span className="text-xs text-muted-foreground">{totalThoughts} {totalThoughts === 1 ? 'thought' : 'thoughts'}</span>
        </div>
        <div className="flex shrink-0 items-center gap-3 text-xs text-muted-foreground">
          <button type="button" onClick={() => toggleAll(true)} className="hover:text-foreground">Expand all</button>
          <button type="button" onClick={() => toggleAll(false)} className="hover:text-foreground">Collapse all</button>
        </div>
      </div>

      {isReviewActive && (
        <div className="flex shrink-0 items-center justify-between gap-3 border-b bg-amber-50/70 px-4 py-2 text-sm text-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
          <div className="flex min-w-0 items-center gap-2">
            <UserCheck className="h-4 w-4 shrink-0" aria-hidden="true" />
            <span className="truncate">Waiting for your review: identity mapping</span>
          </div>
          <Button size="xs" onClick={() => setOpenReviewDialog(true)}>Review</Button>
          <IdentityDecision open={openReviewDialog} onOpenChange={setOpenReviewDialog} review={identityReview} names={names} onDone={onReviewDone} />
        </div>
      )}

      <div ref={scrollRef} onScroll={handleScroll} className="min-h-0 w-full flex-1 overflow-y-auto overflow-x-hidden bg-muted/40 px-3 py-2">
        {displayEvents.length === 0 ? (
          <div className="flex h-40 flex-col items-center justify-center gap-1 text-center">
            <span className="text-sm text-foreground/80">No activity yet</span>
            <span className="text-xs text-muted-foreground">The steps the agent takes will appear here.</span>
          </div>
        ) : (
          displayEvents.map((e) => {
            const isThinking = e.type === 'thinking' || Boolean(e.payload?.thinking)
            const isTool = e.type === 'tool' || e.type === 'rf_tool'
            const isDecision = e.type === 'decision' || e.type === 'rf_decision'
            const isExpanded = isItemExpanded(e)
            const isActive = e.seq === activeEventSeq

            if (isThinking) return <ThoughtItem key={e.seq} event={e} isExpanded={isExpanded} onToggle={() => toggleExpand(e.seq, isExpanded)} isActive={isActive} />
            if (isTool) return <ToolCallItem key={e.seq} event={e} isExpanded={isExpanded} onToggle={() => toggleExpand(e.seq, isExpanded)} isActive={isActive} />
            if (isDecision) return <DecisionItem key={e.seq} event={e} isExpanded={isExpanded} onToggle={() => toggleExpand(e.seq, isExpanded)} />
            if (e.type === 'summary') return <SummaryItem key={e.seq} event={e} names={names} />
            return <LogItem key={e.seq} event={e} />
          })
        )}
      </div>

      <div className="flex shrink-0 items-center justify-between border-t px-4 py-1.5 text-xs text-muted-foreground">
        <span className="flex items-center gap-2">{current === 'running' && <ActiveDot />}{status}</span>
        <span className="font-mono">{runId ? String(runId).slice(0, 8) : ''}</span>
      </div>
    </div>
  )
}

AgentActivityFeed.propTypes = {
  events: PropTypes.array,
  current: PropTypes.string,
  identityReview: PropTypes.object,
  runId: PropTypes.string,
  onReviewDone: PropTypes.func,
  names: PropTypes.object,
}
