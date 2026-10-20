/**
 * Development-only harness: renders the assessment pages without Keycloak, with the API answered by the browser test (e2e/).
 * It is a separate entry (preview.html) and is not part of the application build.
 *
 *   /preview.html?role=instructor#/teams/MC01/performance/assessment
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import '../index.css'
import { Toaster } from '../components/ui/sonner.jsx'
import { AuthContext } from '../shared/auth/context.js'
import { ModalProvider } from '../shared/context/ModalContext.jsx'
import { ThemeProvider } from '../shared/theme/ThemeProvider.jsx'
import GithubLinkCard from '../shared/github/GithubLinkCard.jsx'
import TeamAccessGate from '../shared/github/TeamAccessGate.jsx'
import TeamAccessPage from '../shared/github/TeamAccessPage.jsx'
import GithubPopupDone from '../shared/github/GithubPopupDone.jsx'
import PerformanceRoutes from '../modules/performance/routes.jsx'

const role = new URLSearchParams(window.location.search).get('role') || 'instructor'
const auth = { user: { name: 'Preview', role }, isInitialized: true, isLoggingOut: false, isAuthenticated: true }
const client = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } })

// eslint-disable-next-line react-refresh/only-export-components
function Frame({ children }) {
  return <main className="workspace-container mx-auto w-full min-w-0 max-w-6xl p-4 sm:p-6">{children}</main>
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThemeProvider defaultTheme={new URLSearchParams(window.location.search).get('theme') || 'light'}>
      <QueryClientProvider client={client}>
        <AuthContext.Provider value={auth}>
          <ModalProvider>
            <HashRouter>
              <Frame>
                <Routes>
                  <Route path="/teams/:teamId/performance/*" element={<PerformanceRoutes />} />
                  <Route path="/github/popup-done" element={<GithubPopupDone />} />
                  <Route path="/teams/:teamId/access" element={<TeamAccessPage />} />
                  <Route path="/teams/:teamId/gate" element={<TeamAccessGate teamId="MC01"><div className="p-10 text-center text-lg">The team dashboard</div></TeamAccessGate>} />
                  <Route path="/teams/:teamId/github" element={<GithubLinkCard team="MC01" repoUrl="https://github.com/acme/app" canEditRepo />} />
                </Routes>
              </Frame>
            </HashRouter>
            <Toaster />
          </ModalProvider>
        </AuthContext.Provider>
      </QueryClientProvider>
    </ThemeProvider>
  </StrictMode>,
)
