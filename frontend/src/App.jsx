import { Routes, Route, Navigate } from 'react-router-dom'
import { ThemeProvider } from './shared/theme/ThemeProvider.jsx'
import { Toaster } from './components/ui/sonner.jsx'
import { ModalProvider } from './shared/context/ModalContext.jsx'
import { AuthProvider } from './shared/auth/AuthContext.jsx'
import { useAuth } from './shared/auth/useAuth.js'
import RequireAuth from './shared/auth/RequireAuth.jsx'
import DashboardShell from './shared/layout/DashboardShell.jsx'
import Login from './shared/pages/Login.jsx'
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
  const { user } = useAuth()
  return <Navigate to={user ? `/${user.role}` : '/login'} replace />
}

function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="eduflow-theme">
      <ModalProvider>
        <Toaster />
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />

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
    </AuthProvider>
    </ModalProvider>
    </ThemeProvider>
  )
}

export default App
