// Stand-alone preview of the Security Assistant pages on the checked-in sample run: no sign-in and no Core API.
// Served by the dev server at /security-assistant-demo.html?role=student|instructor. Everything it shows is labelled "demo data".
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import '@/index.css'
import { forceDemoMode } from './config.js'
import { DemoRoleContext } from './hooks/useViewerRole.js'
import AssistantRoutes from './routes.jsx'

forceDemoMode()

const params = new URLSearchParams(window.location.search)
const role = ['student', 'instructor', 'admin'].includes(params.get('role')) ? params.get('role') : 'student'
params.delete('role')
const search = params.toString() ? `?${params}` : ''
const client = new QueryClient({ defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } } })

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <QueryClientProvider client={client}>
      <DemoRoleContext.Provider value={role}>
        <MemoryRouter initialEntries={[`/teams/J26-SE-363/security/assistant${search}`]}>
          <main className="mx-auto max-w-6xl p-6">
            <Routes>
              <Route path="/teams/:teamId/security/assistant/*" element={<AssistantRoutes />} />
            </Routes>
          </main>
        </MemoryRouter>
      </DemoRoleContext.Provider>
    </QueryClientProvider>
  </StrictMode>,
)
