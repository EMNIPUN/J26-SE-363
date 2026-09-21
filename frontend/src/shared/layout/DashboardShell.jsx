import { useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sparkles } from 'lucide-react'
import TopNavbar from './TopNavbar.jsx'
import Sidebar from './Sidebar.jsx'
import AiChatPanel from '../components/AiChatPanel.jsx'
import { useAuth } from '../auth/useAuth.js'
import { getNavForRole } from './navConfig.js'
import { Sheet, SheetContent } from '@/components/ui/sheet'

const PORTAL_LABEL = {
  student: 'Student Portal',
  instructor: 'Instructor Portal',
  admin: 'Admin Portal',
}

const AI_PANEL_STORAGE_KEY = 'eduflow-ai-panel-open'

export default function DashboardShell() {
  const { user } = useAuth()
  const location = useLocation()
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const [mobileAiOpen, setMobileAiOpen] = useState(false)
  const [aiPanelOpen, setAiPanelOpen] = useState(() => {
    try {
      const saved = localStorage.getItem(AI_PANEL_STORAGE_KEY)
      return saved !== null ? saved === 'true' : true
    } catch {
      return true
    }
  })

  const sections = getNavForRole(user.role)

  const handleToggleAi = () => {
    if (typeof window !== 'undefined' && window.innerWidth < 1024) {
      setMobileAiOpen((prev) => !prev)
    } else {
      setAiPanelOpen((prev) => {
        const next = !prev
        try {
          localStorage.setItem(AI_PANEL_STORAGE_KEY, String(next))
        } catch {
          // ignore localStorage errors
        }
        return next
      })
    }
  }

  return (
    <div className="h-screen flex flex-col bg-background text-foreground overflow-hidden">
      <TopNavbar onToggleMobileMenu={() => setMobileNavOpen(true)} />

      {/* Mobile Nav Drawer */}
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="p-0 w-72">
          <div className="pt-6 h-full overflow-y-auto column-scroll-contain">
            <Sidebar
              sections={sections}
              portalLabel={PORTAL_LABEL[user.role]}
              onNavigate={() => setMobileNavOpen(false)}
            />
          </div>
        </SheetContent>
      </Sheet>

      {/* Mobile/Tablet AI Drawer */}
      <Sheet open={mobileAiOpen} onOpenChange={setMobileAiOpen}>
        <SheetContent side="right" className="p-0 w-[92vw] sm:w-[420px]">
          <div className="h-full pt-4">
            <AiChatPanel onClose={() => setMobileAiOpen(false)} />
          </div>
        </SheetContent>
      </Sheet>

      {/* 3-Column Dashboard Body: fills entire viewport below navbar */}
      <div className="flex-1 flex w-full min-h-0 overflow-hidden">
        {/* Column 1: Left Navigation Sidebar (Desktop) - fixed to screen */}
        <div className="hidden md:block w-64 shrink-0 border-r border-sidebar-border bg-sidebar h-full overflow-y-auto column-scroll-contain">
          <Sidebar sections={sections} portalLabel={PORTAL_LABEL[user.role]} />
        </div>

        {/* Column 2: Content Area (Independently scrollable with fluid fade-rise tab entrance & shaded canvas) */}
        <main className="flex-1 min-w-0 h-full overflow-y-auto p-4 sm:p-6 lg:p-8 bg-background column-scroll-contain transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]">
          <div key={location.pathname} className="max-w-7xl mx-auto animate-fade-rise">
            <Outlet />
          </div>
        </main>

        {/* Column 3: AI Chat Panel (Desktop, fixed to screen, fluid width collapse) */}
        {aiPanelOpen && (
          <div className="hidden lg:flex flex-col w-80 xl:w-96 shrink-0 h-full border-l border-sidebar-border bg-sidebar overflow-hidden transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)]">
            <AiChatPanel onClose={handleToggleAi} />
          </div>
        )}
      </div>

      {/* Floating AI Copilot Trigger (Appears in bottom-right corner when 3rd column is closed) */}
      <div
        className={`fixed bottom-6 right-6 z-50 ${
          aiPanelOpen ? 'lg:hidden' : ''
        } ${mobileAiOpen ? 'hidden' : ''}`}
      >
        <button
          type="button"
          onClick={handleToggleAi}
          aria-label="Open AI Copilot"
          className="flex items-center gap-2 px-4 py-2.5 rounded-full bg-primary text-primary-foreground shadow-lg hover:shadow-xl hover:scale-105 active:scale-95 transition-all duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] cursor-pointer group animate-scale-in"
        >
          <Sparkles className="h-4 w-4 text-amber-300 group-hover:rotate-12 transition-transform duration-200 shrink-0" />
          <span className="text-xs font-semibold tracking-tight">AI Copilot</span>
          <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
        </button>
      </div>
    </div>
  )
}


