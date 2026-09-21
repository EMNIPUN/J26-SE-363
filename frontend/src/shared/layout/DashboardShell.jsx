import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import TopNavbar from './TopNavbar.jsx'
import Sidebar from './Sidebar.jsx'
import { useAuth } from '../auth/useAuth.js'
import { getNavForRole } from './navConfig.js'
import { Sheet, SheetContent } from '@/components/ui/sheet'

const PORTAL_LABEL = {
  student: 'Student Portal',
  instructor: 'Instructor Portal',
  admin: 'Admin Portal',
}

export default function DashboardShell() {
  const { user } = useAuth()
  const [mobileNavOpen, setMobileNavOpen] = useState(false)
  const sections = getNavForRole(user.role)

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <TopNavbar onToggleMobileMenu={() => setMobileNavOpen(true)} />

      {/* Mobile Drawer */}
      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="p-0 w-72">
          <div className="pt-6">
            <Sidebar
              sections={sections}
              portalLabel={PORTAL_LABEL[user.role]}
              onNavigate={() => setMobileNavOpen(false)}
            />
          </div>
        </SheetContent>
      </Sheet>

      <div className="flex-1 flex w-full">
        {/* Desktop Sidebar */}
        <div className="hidden md:block border-r border-border bg-card">
          <div className="sticky top-16 h-[calc(100vh-4rem)] overflow-y-auto">
            <Sidebar sections={sections} portalLabel={PORTAL_LABEL[user.role]} />
          </div>
        </div>

        {/* Main Content Area */}
        <main className="flex-1 min-w-0 p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto w-full">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

