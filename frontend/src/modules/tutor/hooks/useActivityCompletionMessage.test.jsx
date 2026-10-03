import { useRef } from 'react'
import { act, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { useActivityCompletionMessage } from './useActivityCompletionMessage.js'
import { ACTIVITY_COMPLETED_MESSAGE } from '../utils/constants.js'

const FRAME_ORIGIN = 'https://lab.example.com'

function Harness({ onCompleted, enabled = true, activityId = 'act-quiz-jwt' }) {
  const frameRef = useRef(null)
  useActivityCompletionMessage({ frameRef, frameOrigin: FRAME_ORIGIN, activityId, onCompleted, enabled })
  return <iframe ref={frameRef} title="activity" />
}

function renderHarness(props = {}) {
  const onCompleted = vi.fn()
  const view = render(<Harness onCompleted={onCompleted} {...props} />)
  const frameWindow = screen.getByTitle('activity').contentWindow
  return { onCompleted, frameWindow, ...view }
}

function post({ source, origin = FRAME_ORIGIN, data = { type: ACTIVITY_COMPLETED_MESSAGE, activityId: 'act-quiz-jwt' } }) {
  act(() => {
    window.dispatchEvent(new MessageEvent('message', { source, origin, data }))
  })
}

describe('useActivityCompletionMessage', () => {
  it('reports a completion sent by the embedded activity', () => {
    const { onCompleted, frameWindow } = renderHarness()

    post({ source: frameWindow })

    expect(onCompleted).toHaveBeenCalledTimes(1)
  })

  it('ignores messages from another window or origin', () => {
    const { onCompleted, frameWindow } = renderHarness()

    post({ source: window })
    post({ source: frameWindow, origin: 'https://evil.example.com' })

    expect(onCompleted).not.toHaveBeenCalled()
  })

  it('ignores other message types and other activities', () => {
    const { onCompleted, frameWindow } = renderHarness()

    post({ source: frameWindow, data: { type: 'something-else', activityId: 'act-quiz-jwt' } })
    post({ source: frameWindow, data: { type: ACTIVITY_COMPLETED_MESSAGE, activityId: 'act-quiz-rest-challenge' } })
    post({ source: frameWindow, data: 'selvia:activity-completed' })

    expect(onCompleted).not.toHaveBeenCalled()
  })

  it('stops listening while disabled and after unmount', () => {
    const { onCompleted, frameWindow, rerender, unmount } = renderHarness({ enabled: false })

    post({ source: frameWindow })
    expect(onCompleted).not.toHaveBeenCalled()

    rerender(<Harness onCompleted={onCompleted} />)
    post({ source: frameWindow })
    expect(onCompleted).toHaveBeenCalledTimes(1)

    unmount()
    post({ source: frameWindow })
    expect(onCompleted).toHaveBeenCalledTimes(1)
  })
})
