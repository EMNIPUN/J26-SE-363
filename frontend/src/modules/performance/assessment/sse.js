/**
 * Server-sent events from a fetch response body: feed it text chunks, it calls onEvent({id, event, data}) for each complete event.
 * Lines starting with ':' are keep-alives and are ignored.
 */
export function createSseParser(onEvent) {
  let buffer = ''
  return (chunk) => {
    buffer += chunk.replace(/\r\n/g, '\n')
    let cut
    while ((cut = buffer.indexOf('\n\n')) >= 0) {
      const block = buffer.slice(0, cut)
      buffer = buffer.slice(cut + 2)
      const ev = { id: undefined, event: 'message', data: '' }
      for (const line of block.split('\n')) {
        if (!line || line.startsWith(':')) continue
        const i = line.indexOf(':')
        const field = i < 0 ? line : line.slice(0, i)
        const value = i < 0 ? '' : line.slice(i + 1).replace(/^ /, '')
        if (field === 'id') ev.id = value
        else if (field === 'event') ev.event = value
        else if (field === 'data') ev.data += (ev.data ? '\n' : '') + value
      }
      if (ev.data || ev.event !== 'message') onEvent(ev)
    }
  }
}
