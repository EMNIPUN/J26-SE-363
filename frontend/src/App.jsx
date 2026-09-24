import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import queryClient from './shared/api/queryClient.js'
import { ThemeProvider } from './shared/theme/ThemeProvider.jsx'
import { Toaster } from './components/ui/sonner.jsx'
import { ModalProvider } from './shared/context/ModalContext.jsx'
import SplashScreen from './shared/components/SplashScreen.jsx'
import { AuthProvider } from './shared/auth/AuthContext.jsx'
import { useAuth } from './shared/auth/useAuth.js'
import RequireAuth from './shared/auth/RequireAuth.jsx'
import DashboardShell from './shared/layout/DashboardShell.jsx'
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

  return <Navigate to={`/${user.role}`} replace />
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
            <Route path="/student" element={<StudentHome />} />
            <Route path="/instructor" element={<InstructorHome />} />
            <Route path="/admin" element={<AdminHome />} />
            <Route path="/admin/*" element={<AdminRoutes />} />
            <Route path="/planning/*" element={<PlanningRoutes />} />
            <Route path="/performance/*" element={<PerformanceRoutes />} />
            <Route path="/tutor/*" element={<TutorRoutes />} />
            <Route path="/security/*" element={<SecurityRoutes />} />
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
            <AppContent />
          </AuthProvider>
        </ModalProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

export default App
