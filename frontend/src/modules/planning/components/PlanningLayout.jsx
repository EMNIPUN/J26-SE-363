import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { useQualityResults } from '../hooks/useQuality.js'
import { useStories } from '../hooks/useDecomposition.js'
import { mapPersistedRows } from '../adapters/quality.js'
import { mapStoryRows } from '../adapters/decomposition.js'
import { usePlanningData } from '../context/usePlanningData.js'

/**
 * Enterprise Module-Level Planning Hydration Layout.
 * 
 * Provides centralized, unified data hydration for all planning sub-routes
 * (/planning/dashboard, /planning/requirements/srs-quality, /planning/requirements/decomposition,
 * /planning/requirements/estimation, /planning/sprint-management, etc.).
 * 
 * Ensures that whenever any page in the planning pipeline is mounted or refreshed:
 * 1. SRS requirements and quality results are automatically fetched from the Quality Agent.
 * 2. User stories are automatically fetched from the Decomposition Agent.
 * 3. The central planningStore and local cache are kept strictly up to date.
 * 4. Eliminates empty-state flashes and 0% milestone calculation errors across pages.
 */
export default function PlanningLayout() {
  const { loadRequirements, loadStories } = usePlanningData()
  const qualityQuery = useQualityResults()
  const storiesQuery = useStories()

  // Centralized requirement hydration across all planning routes
  useEffect(() => {
    const rows = qualityQuery.data?.requirements
    if (Array.isArray(rows)) {
      loadRequirements(mapPersistedRows(rows))
    }
  }, [qualityQuery.data]) // eslint-disable-line react-hooks/exhaustive-deps

  // Centralized user stories hydration across all planning routes
  useEffect(() => {
    const stories = storiesQuery.data?.stories ?? storiesQuery.data?.data?.stories
    if (Array.isArray(stories)) {
      const mapped = mapStoryRows(stories)
      loadStories(mapped, { replace: true })
    }
  }, [storiesQuery.data]) // eslint-disable-line react-hooks/exhaustive-deps

  return <Outlet />
}
