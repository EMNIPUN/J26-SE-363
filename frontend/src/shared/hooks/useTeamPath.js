import { useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { useScope } from '../context/useScope.js'

// Keeps in-app links inside /teams/:teamId so planning steps do not bounce
// through the unscoped redirect.
export function useTeamPath() {
  const { teamId } = useParams()
  const { selectedGroup } = useScope()
  const code = teamId || selectedGroup?.code || ''

  return useCallback(
    (path = '') => {
      if (!path || path.startsWith('/teams/')) return path
      const normalized = path.startsWith('/') ? path : `/${path}`
      return `/teams/${code}${normalized}`
    },
    [code],
  )
}
