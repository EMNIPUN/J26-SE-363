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
import RequireAccount from './shared/auth/RequireAccount.jsx'
import RequireRole from './shared/auth/RequireRole.jsx'
import DashboardShell from './shared/layout/DashboardShell.jsx'
import HubLayout from './shared/layout/HubLayout.jsx'
import TeamScopeGuard from './shared/layout/TeamScopeGuard.jsx'
import TeamAccessPage from './shared/github/TeamAccessPage.jsx'
import GithubPopupDone from './shared/github/GithubPopupDone.jsx'
import TeamScopeRedirect from './shared/layout/TeamScopeRedirect.jsx'
import NotFound from './shared/pages/NotFound.jsx'
import OnboardingPage from './shared/pages/onboarding/OnboardingPage.jsx'
import HomePage from './shared/pages/home/HomePage.jsx'
import TeamSetupPage from './shared/pages/teams/TeamSetupPage.jsx'
import TeamMembersPage from './shared/pages/teams/TeamMembersPage.jsx'
import InvitationPage from './shared/pages/invitations/InvitationPage.jsx'
import TeamsPage from './shared/pages/teams/TeamsPage.jsx'
import ProfileLayout from './shared/pages/profile/ProfileLayout.jsx'
import ProfilePage from './shared/pages/profile/ProfilePage.jsx'
import SecurityPage from './shared/pages/profile/SecurityPage.jsx'
import MyTeamsPage from './shared/pages/profile/MyTeamsPage.jsx'
import NotificationSettingsPage from './shared/pages/profile/NotificationSettingsPage.jsx'
import NotificationsPage from './shared/pages/notifications/NotificationsPage.jsx'
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

  return <Navigate to="/home" replace />
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
        {/* The small window GitHub ends on; it reports back to the window that opened it and closes */}
        <Route path="/github/popup-done" element={<GithubPopupDone />} />

        <Route element={<RequireAuth />}>
          {/* First sign-in: choose student or lecturer and give the details */}
          <Route element={<RequireAccount onboarding />}>
            <Route path="/onboarding" element={<OnboardingPage />} />
          </Route>

          <Route element={<RequireAccount />}>
          {/* The check in front of a team: GitHub sends people back here, and a student reaches the dashboard only through it */}
          <Route path="/teams/:teamId/access" element={<TeamAccessPage />} />
          {/* Before a team's workspace: the team list, creating a team, invitations, profile */}
          <Route element={<HubLayout />}>
            <Route path="/home" element={<HomePage />} />
            <Route path="/teams" element={<TeamsPage />} />
            <Route element={<RequireRole allowedRoles={['instructor']} />}>
              <Route path="/teams/new" element={<TeamSetupPage />} />
              <Route path="/teams/new/:code" element={<TeamSetupPage />} />
            </Route>
            <Route path="/invitations" element={<InvitationPage />} />
            <Route path="/notifications" element={<NotificationsPage />} />
            <Route path="/profile" element={<ProfileLayout />}>
              <Route index element={<ProfilePage />} />
              <Route path="security" element={<SecurityPage />} />
              <Route path="teams" element={<MyTeamsPage />} />
              <Route path="notifications" element={<NotificationSettingsPage />} />
            </Route>
          </Route>

          <Route element={<DashboardShell />}>
            {/* Team-Scoped Core Application Routes */}
            <Route path="/teams/:teamId" element={<TeamScopeGuard />}>
              <Route index element={<RoleDashboard />} />
              <Route path="app" element={<RoleDashboard />} />
              <Route path="members" element={<TeamMembersPage />} />
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
        </Route>

        <Route path="/" element={<RootRedirect />} />
      </Routes>
    </>
  )
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider defaultTheme="light" storageKey="selvia-theme">
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
