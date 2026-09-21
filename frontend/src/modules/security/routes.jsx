import { Routes, Route, Navigate } from 'react-router-dom'

import Dashboard from './pages/Dashboard.jsx'
import ScanReport from './pages/ScanReport.jsx'
import Remediation from './pages/Remediation.jsx'

export default function SecurityRoutes() {
  return (
    <Routes>
      <Route index element={<Navigate to="dashboard" replace />} />
      <Route path="dashboard" element={<Dashboard />} />
      <Route path="scan-report" element={<ScanReport />} />
      <Route path="remediation" element={<Remediation />} />
    </Routes>
  )
}
