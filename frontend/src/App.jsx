import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import queryClient from './shared/api/queryClient.js'
import { ThemeProvider } from './shared/theme/ThemeProvider.jsx'
import { Toaster } from './components/ui/sonner.jsx'
import { ModalProvider } from './shared/context/ModalContext.jsx'
import SplashScreen from './shared/components/SplashScreen.jsx'
import { AuthProvider } from './shared/auth/AuthContext.jsx'
import { ScopeProvider } from './shared/context/ScopeContext.jsx'
import { useAuth } from './shared/auth/useAuth.js'
import RequireAuth from './shared/auth/RequireAuth.jsx'
import RequireRole from './shared/auth/RequireRole.jsx'
import DashboardShell from './shared/layout/DashboardShell.jsx'
import TeamScopeGuard from './shared/layout/TeamScopeGuard.jsx'
import TeamScopeRedirect from './shared/layout/TeamScopeRedirect.jsx'
import NotFound from './shared/pages/NotFound.jsx'
import StudentHome from './shared/pages/dashboards/StudentHome.jsx'
import InstructorHome from './shared/pages/dashboards/InstructorHome.jsx'
import AdminHome from './shared/pages/dashboards/AdminHome.jsx'
import PlanningRoutes from './modules/planning/routes.jsx'
import PerformanceRoutes from './modules/performance/routes.jsx'
import TutorRoutes from './modules/tutor/routes.jsx'
import SecurityRoutes from './modules/security/routes.jsx'
import AdminRoutes from './modules/admin/routes.jsx'

function RootRedirect() {
  const { user, isInitialized, isLoggingOut, loginWithKeycloak } = useAuth()

  useEffect(() => {
    if (isInitialized && !user && !isLoggingOut) {
      loginWithKeycloak()
    }
  }, [isInitialized, user, isLoggingOut, loginWithKeycloak])

  if (!isInitialized || !user || isLoggingOut) {
    return <div className="min-h-screen bg-background" />
  }

  return <Navigate to="/app" replace />
}

function RoleDashboard() {
  const { user } = useAuth()

  if (user?.role === 'admin') {
    return <AdminHome />
  }
  if (user?.role === 'instructor') {
    return <InstructorHome />
  }
  return <StudentHome />
}

function AppContent() {
  const { user, isInitialized, isLoggingOut } = useAuth()
  const isBuffering = !isInitialized || !user || isLoggingOut

  return (
    <>
      <SplashScreen isBuffering={isBuffering} />
      <Routes>
        <Route path="/login" element={<RootRedirect />} />

        <Route element={<RequireAuth />}>
          <Route element={<DashboardShell />}>
            {/* Team-Scoped Core Application Routes */}
            <Route path="/teams/:teamId" element={<TeamScopeGuard />}>
              <Route index element={<RoleDashboard />} />
              <Route path="app" element={<RoleDashboard />} />
              <Route path="planning/*" element={<PlanningRoutes />} />
              <Route path="performance/*" element={<PerformanceRoutes />} />
              <Route path="tutor/*" element={<TutorRoutes />} />
              <Route path="security/*" element={<SecurityRoutes />} />
            </Route>

            {/* Admin-only system routes */}
            <Route element={<RequireRole allowedRoles={['admin']} />}>
              <Route path="/admin/*" element={<AdminRoutes />} />
            </Route>

            {/* Backward-compatibility / Unscoped URL Redirectors */}
            <Route path="/app" element={<TeamScopeRedirect />} />
            <Route path="/planning/*" element={<TeamScopeRedirect />} />
            <Route path="/performance/*" element={<TeamScopeRedirect />} />
            <Route path="/tutor/*" element={<TeamScopeRedirect />} />
            <Route path="/security/*" element={<TeamScopeRedirect />} />

            {/* Legacy bookmark redirects */}
            <Route path="/student" element={<Navigate to="/app" replace />} />
            <Route path="/instructor" element={<Navigate to="/app" replace />} />

            <Route path="*" element={<NotFound />} />
          </Route>
        </Route>

        <Route path="/" element={<RootRedirect />} />
      </Routes>
    </>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="system" storageKey="mentor-theme">
        <ModalProvider>
          <Toaster />
          <AuthProvider>
            <ScopeProvider>
              <AppContent />
            </ScopeProvider>
          </AuthProvider>
        </ModalProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

export default App
