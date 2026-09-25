import { createContext, useState, useEffect, useMemo, useCallback } from 'react'
import { useAuth } from '../auth/useAuth.js'
import {
  BATCHES,
  SPECIALIZATIONS,
  GROUPS,
  STUDENTS,
} from '../constants/academicScope.js'

const ScopeContext = createContext(null)

const STORAGE_KEY = 'mentor_academic_scope'

export function ScopeProvider({ children }) {
  const { user } = useAuth()
  const isStudent = user?.role === 'student'

  // Identify student record if logged-in user is a student
  const studentProfile = useMemo(() => {
    if (!isStudent || !user) return null
    return (
      STUDENTS.find((s) => s.email?.toLowerCase() === user.email?.toLowerCase()) ||
      STUDENTS.find((s) => s.studentId?.toLowerCase() === user.preferred_username?.toLowerCase()) ||
      STUDENTS[0] // fallback to first student in group if mocked
    )
  }, [isStudent, user])

  // Initial state derived from storage or default active entities
  const [selectedBatchId, setSelectedBatchIdState] = useState(() => {
    if (typeof window === 'undefined') return BATCHES[0].id
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY)
      if (saved) {
        const parsed = JSON.parse(saved)
        if (parsed.batchId) return parsed.batchId
      }
    } catch {
      // ignore JSON parse error
    }
    return BATCHES[0].id
  })

  const [selectedSpecializationId, setSelectedSpecializationIdState] = useState(() => {
    if (typeof window === 'undefined') return SPECIALIZATIONS[0].id
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY)
      if (saved) {
        const parsed = JSON.parse(saved)
        if (parsed.specializationId) return parsed.specializationId
      }
    } catch {
      // ignore
    }
    return SPECIALIZATIONS[0].id
  })

  const [selectedGroupId, setSelectedGroupIdState] = useState(() => {
    if (typeof window === 'undefined') return GROUPS[0].id
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY)
      if (saved) {
        const parsed = JSON.parse(saved)
        if (parsed.groupId) return parsed.groupId
      }
    } catch {
      // ignore
    }
    return GROUPS[0].id
  })

  const [selectedStudentId, setSelectedStudentIdState] = useState(() => {
    if (typeof window === 'undefined') return 'all'
    try {
      const saved = sessionStorage.getItem(STORAGE_KEY)
      if (saved) {
        const parsed = JSON.parse(saved)
        if (parsed.studentId) return parsed.studentId
      }
    } catch {
      // ignore
    }
    return 'all'
  })

  // Declarative effective IDs: If user is a student, their scope is locked to their enrolled profile
  const effectiveBatchId = isStudent && studentProfile ? studentProfile.batchId : selectedBatchId
  const effectiveSpecializationId = isStudent && studentProfile ? studentProfile.specializationId : selectedSpecializationId
  const effectiveGroupId = isStudent && studentProfile ? studentProfile.groupId : selectedGroupId
  const effectiveStudentId = isStudent && studentProfile ? studentProfile.id : selectedStudentId

  // Available lists filtered by parent tier
  const availableSpecializations = useMemo(() => {
    return SPECIALIZATIONS.filter((s) => s.batchId === effectiveBatchId)
  }, [effectiveBatchId])

  const availableGroups = useMemo(() => {
    return GROUPS.filter((g) => g.batchId === effectiveBatchId)
  }, [effectiveBatchId])

  const availableStudents = useMemo(() => {
    if (effectiveGroupId === 'all') {
      return STUDENTS.filter((s) => s.batchId === effectiveBatchId)
    }
    return STUDENTS.filter((s) => s.groupId === effectiveGroupId)
  }, [effectiveBatchId, effectiveGroupId])

  // Cascading setters
  const setBatchId = useCallback((newBatchId) => {
    setSelectedBatchIdState(newBatchId)
    const newGroups = GROUPS.filter((g) => g.batchId === newBatchId)
    const firstGroup = newGroups[0]?.id || ''
    setSelectedGroupIdState(firstGroup)
    setSelectedStudentIdState('all')
  }, [])

  const setSpecializationId = useCallback((newSpecId) => {
    setSelectedSpecializationIdState(newSpecId)
    const newGroups = GROUPS.filter(
      (g) => g.batchId === selectedBatchId && g.specializationId === newSpecId,
    )
    const firstGroup = newGroups[0]?.id || ''
    setSelectedGroupIdState(firstGroup)
    setSelectedStudentIdState('all')
  }, [selectedBatchId])

  const setGroupId = useCallback((newGroupId) => {
    setSelectedGroupIdState(newGroupId)
    const grp = GROUPS.find((g) => g.id === newGroupId)
    if (grp) {
      setSelectedSpecializationIdState(grp.specializationId)
    }
    setSelectedStudentIdState('all')
  }, [])

  const setStudentId = useCallback((newStudentId) => {
    setSelectedStudentIdState(newStudentId)
  }, [])

  const resetScope = useCallback(() => {
    setBatchId(BATCHES[0].id)
  }, [setBatchId])

  // Save changes to storage (for instructors/admins)
  useEffect(() => {
    if (!isStudent) {
      try {
        sessionStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({
            batchId: selectedBatchId,
            specializationId: selectedSpecializationId,
            groupId: selectedGroupId,
            studentId: selectedStudentId,
          }),
        )
      } catch {
        // ignore storage errors
      }
    }
  }, [isStudent, selectedBatchId, selectedSpecializationId, selectedGroupId, selectedStudentId])

  // Resolved active objects
  const selectedBatch = useMemo(
    () => BATCHES.find((b) => b.id === effectiveBatchId) || BATCHES[0],
    [effectiveBatchId],
  )

  const selectedSpecialization = useMemo(
    () =>
      SPECIALIZATIONS.find((s) => s.id === effectiveSpecializationId) ||
      availableSpecializations[0] ||
      null,
    [effectiveSpecializationId, availableSpecializations],
  )

  const selectedGroup = useMemo(
    () =>
      GROUPS.find((g) => g.id === effectiveGroupId) ||
      availableGroups[0] ||
      null,
    [effectiveGroupId, availableGroups],
  )

  const selectedStudent = useMemo(() => {
    if (effectiveStudentId === 'all') return null
    return STUDENTS.find((s) => s.id === effectiveStudentId) || null
  }, [effectiveStudentId])

  const value = useMemo(
    () => ({
      // State
      isStudent,
      isLocked: isStudent,
      studentProfile,
      selectedBatchId: effectiveBatchId,
      selectedSpecializationId: effectiveSpecializationId,
      selectedGroupId: effectiveGroupId,
      selectedStudentId: effectiveStudentId,

      // Entities
      selectedBatch,
      selectedSpecialization,
      selectedGroup,
      selectedStudent,

      // Available sets
      batches: BATCHES,
      specializations: availableSpecializations,
      groups: availableGroups,
      students: availableStudents,

      // Actions
      setBatchId,
      setSpecializationId,
      setGroupId,
      setStudentId,
      resetScope,
    }),
    [
      isStudent,
      studentProfile,
      effectiveBatchId,
      effectiveSpecializationId,
      effectiveGroupId,
      effectiveStudentId,
      selectedBatch,
      selectedSpecialization,
      selectedGroup,
      selectedStudent,
      availableSpecializations,
      availableGroups,
      availableStudents,
      setBatchId,
      setSpecializationId,
      setGroupId,
      setStudentId,
      resetScope,
    ],
  )

  return <ScopeContext.Provider value={value}>{children}</ScopeContext.Provider>
}

export default ScopeContext
