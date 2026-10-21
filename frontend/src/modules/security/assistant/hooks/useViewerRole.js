import { createContext, useContext } from 'react'
import { AuthContext } from '@/shared/auth/context.js'

// Lets the stand-alone demo page choose a role without the sign-in provider (see demoEntry.jsx).
export const DemoRoleContext = createContext(null)

// 'student' | 'instructor' | 'admin' | null. The signed-in role normally; the stand-alone demo page sets its own.
export function useViewerRole() {
  const demoRole = useContext(DemoRoleContext)
  const auth = useContext(AuthContext)
  return demoRole ?? auth?.user?.role ?? null
}

export const canPickStudent = (role) => role === 'instructor' || role === 'admin'
