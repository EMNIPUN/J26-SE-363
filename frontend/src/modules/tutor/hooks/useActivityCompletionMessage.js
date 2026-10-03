import { useEffect } from 'react'
import { ACTIVITY_COMPLETED_MESSAGE } from '../utils/constants.js'

// Calls `onCompleted` when the embedded learning platform reports that the
// student finished `activityId`. Messages are accepted only from the frame's
// own window and origin, and are treated purely as a signal to sync.
export function useActivityCompletionMessage({ frameRef, frameOrigin, activityId, onCompleted, enabled = true }) {
  useEffect(() => {
    if (!enabled || !frameOrigin) return undefined

    function handleMessage(event) {
      if (event.source !== frameRef.current?.contentWindow) return
      if (event.origin !== frameOrigin) return
      const { data } = event
      if (data?.type !== ACTIVITY_COMPLETED_MESSAGE || data.activityId !== activityId) return
      onCompleted()
    }

    window.addEventListener('message', handleMessage)
    return () => window.removeEventListener('message', handleMessage)
  }, [frameRef, frameOrigin, activityId, onCompleted, enabled])
}
