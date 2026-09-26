import { createContext, useState, useEffect, useMemo, useCallback } from 'react'
import { useAuth } from '../auth/useAuth.js'
import {
  BATCHES,
  GROUPS,
  STUDENTS,
} from '../constants/academicScope.js'

const ScopeContext = createContext(null)

const STORAGE_KEY = 'mentor_active_scope'

export function ScopeProvider({ children }) {
  const { user } = useAuth()
  const isStudent = user?.role === 'student'

  // Identify student record if logged-in user is a student
  const studentProfile = useMemo(() => {
    if (!isStudent || !user) return null
    return (
      STUDENTS.find((s) => s.email?.toLowerCase() === user.email?.toLowerCase()) ||
      STUDENTS.find((s) => s.studentId?.toLowerCase() === user.preferred_username?.toLowerCase()) ||
      STUDENTS[0] // fallback to default student
    )
  }, [isStudent, user])

  // Initial group ID derived from sessionStorage or first group
  const [selectedGroupId, setSelectedGroupIdState] = useState(() => {
    if (typeof window === 'undefined') return GROUPS[0].id
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY)
      if (saved) {
        const parsed = JSON.parse(saved)
        if (parsed.groupId) return parsed.groupId
      }
    } catch {
      // ignore JSON parse error
    }
    return GROUPS[0].id
  })

  // Declarative effective Group ID: locked to enrolled group for students
  const effectiveGroupId = isStudent && studentProfile ? studentProfile.groupId : selectedGroupId

  // Resolved active group object
  const selectedGroup = useMemo(
    () => GROUPS.find((g) => g.id === effectiveGroupId) || GROUPS[0],
    [effectiveGroupId],
  )

  // Students belonging to the active team
  const teamStudents = useMemo(
    () => STUDENTS.filter((s) => s.groupId === effectiveGroupId),
    [effectiveGroupId],
  )

  // Active batch metadata (for display)
  const selectedBatch = useMemo(
    () => BATCHES.find((b) => b.id === selectedGroup?.batchId) || BATCHES[0],
    [selectedGroup],
  )

  // Setter for instructor / admin
  const setGroupId = useCallback((newGroupId) => {
    setSelectedGroupIdState(newGroupId)
  }, [])

  // Persist active group in sessionStorage for instructors
  useEffect(() => {
    if (!isStudent && selectedGroupId) {
      try {
        sessionStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({ groupId: selectedGroupId }),
        )
      } catch {
        // ignore storage errors
      }
    }
  }, [isStudent, selectedGroupId])

  const value = useMemo(
    () => ({
      isStudent,
      studentProfile,
      selectedGroupId: effectiveGroupId,
      selectedGroup,
      teamStudents,
      groups: GROUPS,
      selectedBatch,
      setGroupId,
    }),
    [
      isStudent,
      studentProfile,
      effectiveGroupId,
      selectedGroup,
      teamStudents,
      selectedBatch,
      setGroupId,
    ],
  )

  return <ScopeContext.Provider value={value}>{children}</ScopeContext.Provider>
}

export default ScopeContext
