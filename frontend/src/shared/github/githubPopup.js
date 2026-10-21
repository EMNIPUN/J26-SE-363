import { useCallback, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { showToast } from '../utils/toast.jsx'
import { reasonText } from './gateCopy.js'

/**
 * GitHub opens in a small window, the way sign-in with Google or Microsoft does, so the page behind it stays where it is. GitHub sends the small window to the
 * callback address, which redirects to POPUP_DONE_PATH; that page reports the result back to this window and closes itself. The button stays busy the whole time.
 */
export const POPUP_DONE_PATH = '/github/popup-done'
const NAME = 'selvia-github'

function features() {
  const w = 620
  const h = 760
  const left = Math.max(0, Math.round(window.screenX + (window.outerWidth - w) / 2))
  const top = Math.max(0, Math.round(window.screenY + (window.outerHeight - h) / 2))
  return `popup=yes,width=${w},height=${h},left=${left},top=${top}`
}

/** Called by the small window when GitHub has sent it back. Both ways are used, because some sites cut the link to the opener. */
export function announceResult(result) {
  try { const ch = new BroadcastChannel(NAME); ch.postMessage(result); ch.close() } catch { /* not supported: the opener message below still works */ }
  try { window.opener?.postMessage({ type: NAME, ...result }, window.location.origin) } catch { /* the opener is gone */ }
}

/** Resolves with what the small window reported, or `{ closed: true }` when the person closed it without finishing. */
export function waitForResult(win) {
  return new Promise((resolve) => {
    let channel = null
    let closedAt = 0
    let done = false
    let timer = 0
    const onMessage = (e) => { if (e.origin === window.location.origin && e.data?.type === NAME) finish({ github: e.data.github, reason: e.data.reason }) }
    function finish(result) {
      if (done) return
      done = true
      clearInterval(timer)
      window.removeEventListener('message', onMessage)
      channel?.close()
      resolve(result)
    }
    window.addEventListener('message', onMessage)
    try { channel = new BroadcastChannel(NAME); channel.onmessage = (e) => finish(e.data || {}) } catch { /* fall back to the message above */ }
    timer = setInterval(() => {
      let closed
      try { closed = win.closed } catch { closed = true }
      if (!closed) return
      closedAt ||= Date.now()
      if (Date.now() - closedAt > 1500) finish({ closed: true }) // a short wait: the result may arrive just as the window closes
    }, 400)
  })
}

/**
 * `run(getUrl)`: open the small window at once (so the browser allows it), ask the API where to send it (`getUrl(true)`), and keep `pending` true until the result is back
 * and the access has been checked again. If the browser blocks the window, the whole page goes to GitHub instead (`getUrl(false)`) and comes back the usual way.
 */
export function useGithubPopup() {
  const qc = useQueryClient()
  const [pending, setPending] = useState(false)
  const run = useCallback(async (getUrl) => {
    if (pending) return
    const win = window.open('', NAME, features())
    if (win) {
      try {
        win.document.title = 'GitHub'
        win.document.body.style.cssText = 'font:15px system-ui,sans-serif;color:#555;display:grid;place-items:center;height:100vh;margin:0'
        win.document.body.textContent = 'Opening GitHub...'
      } catch { /* the window is already elsewhere */ }
    }
    setPending(true)
    try {
      const { url } = await getUrl(Boolean(win))
      if (!win) {
        window.location.assign(url)
        await new Promise(() => {}) // the page is leaving; the button stays busy until it does
      }
      win.location.href = url
      win.focus?.()
      const r = await waitForResult(win)
      try { win.close() } catch { /* already closed */ }
      if (r.github === 'installed') showToast.success('GitHub App installed. Now choose the repository.')
      else if (r.github === 'connected') showToast.success('Your GitHub account is connected.')
      else if (r.github) showToast.error(reasonText(r.reason))
      await qc.invalidateQueries({ queryKey: ['github'] })
    } catch (e) {
      try { win?.close() } catch { /* ignore */ }
      showToast.error(e?.message || 'GitHub could not be opened.')
    } finally {
      setPending(false)
    }
  }, [pending, qc])
  return { run, pending }
}
