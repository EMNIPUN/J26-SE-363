import { createContext, useState, useEffect, useMemo, useCallback } from 'react'
import { useAuth } from '../auth/useAuth.js'
import { useMyTeams, useTeam } from '../hooks/useTeams.js'

const ScopeContext = createContext(null)

const STORAGE_KEY = 'selvia_active_scope'

function readStoredGroupId() {
  try {
    const saved = sessionStorage.getItem(STORAGE_KEY)
    return saved ? JSON.parse(saved).groupId || null : null
  } catch {
    return null
  }
}

// The shape the module pages already use for "the active team".
function toGroup(team) {
  return {
    id: team.id,
    code: team.code,
    name: team.name,
    projectTitle: team.project?.title ?? '',
    repositoryUrl: team.repo_url ?? '',
    batchId: team.term ?? '',
    status: team.status,
    myRole: team.my_role,
  }
}

function toStudent(member, group) {
  return {
    id: member.user_id,
    name: member.name,
    email: member.email ?? '',
    githubUsername: member.github_username ?? '',
    groupId: group?.id,
    isLeader: member.role === 'leader',
  }
}

/**
 * The teams the signed-in person belongs to, and which one the app is focused on.
 * The home page lists the teams; opening one (/teams/:code) makes it the active team.
 */
export function ScopeProvider({ children }) {
  const { user } = useAuth()
  const ready = Boolean(user?.onboarded)

  const teamsQuery = useMyTeams({ enabled: ready })
  // A team still being set up has no workspace yet.
  const groups = useMemo(
    () => (teamsQuery.data ?? []).filter((team) => team.status !== 'pending').map(toGroup),
    [teamsQuery.data],
  )

  const [selectedGroupId, setSelectedGroupIdState] = useState(readStoredGroupId)
  const selectedGroup = useMemo(
    () => groups.find((g) => g.id === selectedGroupId) ?? groups[0] ?? null,
    [groups, selectedGroupId],
  )

  // Members of the active team (students only), for the pages that list students.
  const detailQuery = useTeam(selectedGroup?.code, { enabled: ready })
  const teamStudents = useMemo(
    () =>
      (detailQuery.data?.members ?? [])
        .filter((member) => member.role !== 'lecturer')
        .map((member) => toStudent(member, selectedGroup)),
    [detailQuery.data, selectedGroup],
  )

  const isStudent = user?.role === 'student'
  const studentProfile = useMemo(
    () => (isStudent ? (teamStudents.find((s) => s.name === user?.name) ?? null) : null),
    [isStudent, teamStudents, user?.name],
  )

  const setGroupId = useCallback((newGroupId) => setSelectedGroupIdState(newGroupId), [])

  useEffect(() => {
    if (!selectedGroupId) return
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ groupId: selectedGroupId }))
    } catch {
      // ignore storage errors
    }
  }, [selectedGroupId])

  const value = useMemo(
    () => ({
      isStudent,
      isLoading: ready && teamsQuery.isPending,
      studentProfile,
      groups,
      selectedGroupId: selectedGroup?.id ?? null,
      selectedGroup,
      selectedBatch: selectedGroup ? { id: selectedGroup.batchId, name: selectedGroup.batchId } : null,
      teamStudents,
      setGroupId,
    }),
    [isStudent, ready, teamsQuery.isPending, studentProfile, groups, selectedGroup, teamStudents, setGroupId],
  )

  return <ScopeContext.Provider value={value}>{children}</ScopeContext.Provider>
}

export default ScopeContext
