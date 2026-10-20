import { AxiosError } from 'axios'
import topology from '../../e2e/fixtures/topology.json'
import { respond } from './demoData.js'

/**
 * Demo mode, for development only: open any page with ?demo=1 (or ?demo=live for a run that is still going) and the performance pages show invented sample data instead of
 * asking the server, for lecturers and for students. ?demo=0 turns it off. Nothing is read from or written to the server for those pages, and a badge says so.
 * It is loaded only in development (see apiClient.js), so a production build contains none of it.
 */
const KEY = 'selvia-demo'

function mode() {
  try {
    const q = new URLSearchParams(window.location.search).get('demo')
    if (q !== null) {
      if (q === '0' || q === 'off') sessionStorage.removeItem(KEY)
      else sessionStorage.setItem(KEY, q === 'live' ? 'live' : 'on')
    }
    return sessionStorage.getItem(KEY)
  } catch {
    return null
  }
}

let badge = false
function showBadge(current) {
  if (badge || typeof document === 'undefined') return
  badge = true
  const el = document.createElement('div')
  el.textContent = `Sample data (${current === 'live' ? 'a run in progress' : 'a finished run'}) - nothing here is real`
  el.style.cssText = 'position:fixed;left:12px;bottom:12px;z-index:2147483000;padding:6px 12px;border-radius:999px;background:#4f46e5;color:#fff;font:600 12px system-ui,sans-serif;box-shadow:0 4px 14px rgba(0,0,0,.25);pointer-events:none'
  document.body.appendChild(el)
}

/** Answers a request from the sample data when demo mode is on and it is a performance request; otherwise passes it on to the real adapter. */
export async function answer(config, real) {
  const current = mode()
  const path = (config.url || '').split('?')[0]
  if (!current || !path.startsWith('/performance/')) return real(config)
  showBadge(current)
  const method = (config.method || 'get').toUpperCase()
  const reply = (status, data) => ({ data, status, statusText: String(status), headers: {}, config, request: {} })
  if (method !== 'GET') {
    const message = 'This page is showing sample data, so nothing was changed.'
    throw new AxiosError(message, 'ERR_BAD_REQUEST', config, null, reply(400, { detail: message }))
  }
  // The sample data is about one team; whichever team is open gets it.
  const out = respond(path.replace(/\/teams\/[^/]+\//, '/teams/MC01/'), method, { live: current === 'live' }, topology)
  if (out.status >= 400) throw new AxiosError('Not in the sample data', 'ERR_BAD_REQUEST', config, null, reply(out.status, out.body))
  return reply(out.status, rename(out.body))
}

/** The sample data belongs to team MC01; the student's own pages match results to the open team by its code, so the code is swapped. */
function rename(body) {
  const open = window.location.pathname.match(/\/teams\/([^/]+)/)?.[1]
  if (!open || typeof body !== 'object') return body
  return JSON.parse(JSON.stringify(body).replaceAll('"team_ref":"MC01"', `"team_ref":${JSON.stringify(open)}`))
}
