// Demo mode of the Security Assistant pages: show the checked-in sample run (demo/demoBundle.json) instead of calling the Core API.
// It is on only when VITE_SECURITY_ASSISTANT_DEMO=true is set on purpose; nothing switches it on by itself (an API error stays an error),
// and every page says "demo data" while it is on.
// The stand-alone demo page (demoEntry.jsx) switches it on for itself, openly, before anything renders.
let forced = false
export function forceDemoMode() {
  forced = true
}

export function isDemoMode(env = import.meta.env) {
  return forced || String(env?.VITE_SECURITY_ASSISTANT_DEMO ?? '').toLowerCase() === 'true'
}

export const DEMO_NOTE =
  'The checked-in sample run of a synthetic repository, produced with a mock LLM and the mock Tutor. It is not a real student result.'
