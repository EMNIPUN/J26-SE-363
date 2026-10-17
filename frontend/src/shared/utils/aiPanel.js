export const OPEN_AI_PANEL_EVENT = 'selvia:open-ai-panel'

let pendingPrompt = null

// Opens the shell's AI panel from anywhere in the app. A prompt is held until
// a mounted panel takes it, because the mobile drawer mounts after it opens.
export function openAiPanel(prompt) {
  pendingPrompt = prompt || null
  window.dispatchEvent(new CustomEvent(OPEN_AI_PANEL_EVENT))
}

export function takePendingPrompt() {
  const prompt = pendingPrompt
  pendingPrompt = null
  return prompt
}
