import { describe, expect, it } from 'vitest'
import { createSseParser } from './sse.js'

describe('createSseParser', () => {
  it('reads events split across chunks and skips keep-alives', () => {
    const got = []
    const feed = createSseParser((e) => got.push(e))
    feed('id: 1\nevent: log\ndata: {"a":1}\n\n: keep-alive\n\nid: 2\neve')
    feed('nt: node_end\ndata: {"b":2}\n\n')
    expect(got).toEqual([{ id: '1', event: 'log', data: '{"a":1}' }, { id: '2', event: 'node_end', data: '{"b":2}' }])
  })

  it('handles CRLF and an end event without id', () => {
    const got = []
    const feed = createSseParser((e) => got.push(e))
    feed('event: end\r\ndata: {"status":"succeeded"}\r\n\r\n')
    expect(got[0]).toMatchObject({ event: 'end', data: '{"status":"succeeded"}' })
  })
})
