import { Routes, Route } from 'react-router-dom'
import TopNav from './shared/layout/TopNav.jsx'
import Home from './shared/pages/Home.jsx'
import NotFound from './shared/pages/NotFound.jsx'
import PlanningRoutes from './modules/planning/routes.jsx'
import PerformanceRoutes from './modules/performance/routes.jsx'
import TutorRoutes from './modules/tutor/routes.jsx'
import SecurityRoutes from './modules/security/routes.jsx'
import './App.css'

function App() {
  return (
    <div className="app-shell">
      <TopNav />
      <main className="app-main">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/planning/*" element={<PlanningRoutes />} />
          <Route path="/performance/*" element={<PerformanceRoutes />} />
          <Route path="/tutor/*" element={<TutorRoutes />} />
          <Route path="/security/*" element={<SecurityRoutes />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
