import { Routes, Route, Navigate } from 'react-router-dom'
import ModuleLayout from '../../shared/layout/ModuleLayout.jsx'
import { getModule } from '../../shared/constants/modules'

import Dashboard from './pages/Dashboard.jsx'
import ScanReport from './pages/ScanReport.jsx'
import Remediation from './pages/Remediation.jsx'

const module = getModule('security')

const navLinks = [
  { to: 'dashboard', label: 'Dashboard' },
  { to: 'scan-report', label: 'Scan Report' },
  { to: 'remediation', label: 'Remediation' },
]

export default function SecurityRoutes() {
  return (
    <Routes>
      <Route element={<ModuleLayout module={module} navLinks={navLinks} />}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="scan-report" element={<ScanReport />} />
        <Route path="remediation" element={<Remediation />} />
      </Route>
    </Routes>
  )
}
