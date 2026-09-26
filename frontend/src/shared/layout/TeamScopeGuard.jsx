import { useEffect } from 'react'
import { useParams, Outlet, Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/useAuth.js'
import { useScope } from '../context/useScope.js'
import { GROUPS } from '../constants/academicScope.js'
import { toast } from 'sonner'

export default function TeamScopeGuard() {
  const { teamId } = useParams()
  const location = useLocation()
  const { user } = useAuth()
  const { selectedGroup, setGroupId, studentProfile } = useScope()
  const isStudent = user?.role === 'student'

  // Match teamId from URL against GROUPS by code or id (case-insensitive)
  const matchedGroup = GROUPS.find(
    (g) =>
      g.code?.toLowerCase() === teamId?.toLowerCase() ||
      g.id?.toLowerCase() === teamId?.toLowerCase(),
  )

  // Enrolled group for student
  const enrolledGroupId = studentProfile?.groupId || GROUPS[0].id
  const enrolledGroup = GROUPS.find((g) => g.id === enrolledGroupId) || GROUPS[0]

  // Synchronize ScopeContext with URL when valid
  useEffect(() => {
    if (matchedGroup && selectedGroup?.id !== matchedGroup.id) {
      // If student and matched is different from enrolled, don't set to unauthorized group
      if (isStudent && matchedGroup.id !== enrolledGroup.id) {
        return
      }
      setGroupId(matchedGroup.id)
    }
  }, [matchedGroup, selectedGroup, setGroupId, isStudent, enrolledGroup.id])

  // 1. Tenancy Restriction Guard for Students
  if (isStudent) {
    if (matchedGroup && matchedGroup.id !== enrolledGroup.id) {
      toast.error('Access Restricted', {
        description: `You are enrolled in team ${enrolledGroup.code}. Cross-team access is restricted.`,
      })
      const safePath = location.pathname.replace(teamId, enrolledGroup.code)
      return <Navigate to={safePath} replace />
    }
  }

  // 2. Fallback: If teamId in URL does not exist in registry, redirect to default/enrolled team
  if (!matchedGroup) {
    const targetCode = isStudent ? enrolledGroup.code : GROUPS[0].code
    const safePath = location.pathname.replace(teamId, targetCode)
    return <Navigate to={safePath} replace />
  }

  return <Outlet />
}
