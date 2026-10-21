// Fake answers of the Core API for the screenshot tests. The data lives in src/preview/demoData.js.
import { readFileSync } from 'node:fs'
import { respond } from '../src/preview/demoData.js'

export { STUDENTS, runsList, liveEvents } from '../src/preview/demoData.js'

const topology = JSON.parse(readFileSync(new URL('./fixtures/topology.json', import.meta.url), 'utf8'))

export async function mockApi(page, { role = 'instructor', live = false, gate = 'ok', popupFlow = false } = {}) {
  let connected = false
  await page.route((url) => url.pathname.startsWith('/api/'), async (route) => {
    const url = new URL(route.request().url())
    const p = url.pathname.replace(/^\/api/, '')
    const json = (body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) })
    if (popupFlow && p === '/me/github/connect') { connected = true; return json({ url: `${url.origin}/preview.html?role=student#/github/popup-done?github=connected` }) }
    if (popupFlow && p === '/teams/MC01/gate' && connected) { await new Promise((r) => setTimeout(r, 700)); return json({ state: 'ok' }) }
    const out = respond(p, route.request().method(), { role, live, gate }, topology)
    return route.fulfill({ status: out.status, contentType: 'application/json', body: typeof out.body === 'string' ? out.body : JSON.stringify(out.body) })
  })
}
