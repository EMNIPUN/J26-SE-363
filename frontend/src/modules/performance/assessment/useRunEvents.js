import { useEffect, useRef, useState } from 'react'
import { assessmentApi, bearer, streamUrl } from './assessmentApi.js'
import { createSseParser } from './sse.js'

const FINISHED = ['succeeded', 'failed', 'cancelled']

/**
 * The events of one run, live. Reads the server-sent event stream with fetch (so the bearer token is sent) and resumes after the last seen
 * sequence number; when the stream cannot be opened or breaks it polls /events every two seconds instead.
 */
export function useRunEvents(runId) {
  const [data, setData] = useState({ id: null, list: [] })
  const [status, setStatus] = useState(null)
  const [mode, setMode] = useState('connecting')
  const last = useRef(0)

  useEffect(() => {
    if (!runId) return undefined
    let stop = false
    const controller = new AbortController()
    last.current = 0

    const add = (list) => {
      const fresh = list.filter((e) => e.seq > last.current)
      if (!fresh.length) return
      last.current = fresh[fresh.length - 1].seq
      if (fresh.some((e) => ['run_waiting', 'run_resume', 'run_end'].includes(e.type))) refreshStatus()
      setData((prev) => (prev.id === runId ? { id: runId, list: [...prev.list, ...fresh] } : { id: runId, list: fresh }))
    }
    const refreshStatus = async () => {
      try {
        const run = await assessmentApi.run(runId)
        if (!stop) setStatus(run.status)
        return run.status
      } catch {
        return null
      }
    }
    const poll = async () => {
      setMode('polling')
      while (!stop) {
        try {
          add(await assessmentApi.events(runId, last.current))
        } catch { /* try again */ }
        const s = await refreshStatus()
        if (FINISHED.includes(s)) {
          try { add(await assessmentApi.events(runId, last.current)) } catch { /* ignore */ }
          return
        }
        await new Promise((r) => setTimeout(r, 2000))
      }
    }
    const open = async () => {
      try {
        const res = await fetch(streamUrl(runId, last.current), { headers: { Accept: 'text/event-stream', ...bearer() }, credentials: 'include', signal: controller.signal })
        if (!res.ok || !res.body) throw new Error(`stream ${res.status}`)
        setMode('live')
        const feed = createSseParser((e) => {
          if (e.event === 'end') {
            setStatus(JSON.parse(e.data).status)
            return
          }
          try { add([JSON.parse(e.data)]) } catch { /* skip a broken event */ }
        })
        const reader = res.body.pipeThrough(new TextDecoderStream()).getReader()
        for (;;) {
          const { value, done } = await reader.read()
          if (done) break
          feed(value)
        }
        const s = await refreshStatus()
        if (!stop && !FINISHED.includes(s)) await poll()
        else if (!stop) setMode('finished')
      } catch {
        if (!stop) await poll()
      }
    }
    refreshStatus()
    open()
    // The stream keeps flowing while a run waits for a person, so nothing closes it and the status would never be read again: ask for it now and then (and straight away when the run says it is waiting).
    const watch = setInterval(() => { if (!stop) refreshStatus() }, 4000)
    return () => {
      stop = true
      clearInterval(watch)
      controller.abort()
    }
  }, [runId])

  return { events: data.id === runId ? data.list : [], status, mode }
}
