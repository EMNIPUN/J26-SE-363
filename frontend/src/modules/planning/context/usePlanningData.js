import { useSyncExternalStore } from 'react'
import { getSnapshot, subscribe, actions } from './planningStore.js'
import { TEAM_MEMBERS, PROJECT_INFO } from '../data/mockData.js'

export function usePlanningData() {
  const snapshot = useSyncExternalStore(subscribe, getSnapshot)
  return {
    ...snapshot,
    teamMembers: TEAM_MEMBERS,
    projectInfo: PROJECT_INFO,
    ...actions,
  }
}
