import {
  LayoutDashboard,
  BookOpen,
  BarChart3,
  ShieldCheck,
  Users,
  Settings,
} from 'lucide-react'

// One nav tree per role. `to` on a parent makes the whole group a link too
// (used for single-page sections); `children` renders an expandable list.
export function getNavForRole(role, teamCode = 'J26-SE-363') {
  const t = (path) => `/teams/${teamCode}${path}`

  if (role === 'student') {
    return [
      { label: 'Overview', icon: LayoutDashboard, to: t('/app') },
      {
        label: 'Project Planning',
        icon: BookOpen,
        color: '#2563eb',
        children: [
          { label: 'Dashboard', to: t('/planning/dashboard') },
          { label: 'Blackboard', to: t('/planning/blackboard') },
          { label: 'Traceability', to: t('/planning/requirements/traceability') },
          { label: 'Estimation', to: t('/planning/requirements/estimation') },
          { label: 'SRS Quality', to: t('/planning/requirements/srs-quality') },
          { label: 'Decomposition', to: t('/planning/requirements/decomposition') },
        ],
      },
      {
        label: 'Performance',
        icon: BarChart3,
        color: '#7c3aed',
        to: t('/performance/my-progress'),
      },
      {
        label: 'Project Security',
        icon: ShieldCheck,
        color: '#dc2626',
        children: [
          { label: 'Dashboard', to: t('/security/dashboard') },
          { label: 'Scan Report', to: t('/security/scan-report') },
          { label: 'Remediation', to: t('/security/remediation') },
        ],
      },
    ]
  }

  if (role === 'instructor') {
    return [
      { label: 'Overview', icon: LayoutDashboard, to: t('/app') },
      {
        label: 'Project Planning',
        icon: BookOpen,
        color: '#2563eb',
        children: [
          { label: 'Dashboard', to: t('/planning/dashboard') },
          { label: 'Projects', to: t('/planning/projects') },
          { label: 'Groups', to: t('/planning/groups') },
        ],
      },
      {
        label: 'Performance',
        icon: BarChart3,
        color: '#7c3aed',
        children: [
          { label: 'Dashboard', to: t('/performance/dashboard') },
          { label: 'Student Detail', to: t('/performance/students') },
          { label: 'Assessments', to: t('/performance/assessments') },
          { label: 'Reports', to: t('/performance/reports') },
        ],
      },
      {
        label: 'Security',
        icon: ShieldCheck,
        color: '#dc2626',
        children: [
          { label: 'Dashboard', to: t('/security/dashboard') },
          { label: 'Scan Report', to: t('/security/scan-report') },
          { label: 'Remediation', to: t('/security/remediation') },
        ],
      },
    ]
  }

  // admin
  return [
    { label: 'Overview', icon: LayoutDashboard, to: t('/app') },
    { label: 'Users', icon: Users, to: '/admin/users' },
    { label: 'Settings', icon: Settings, to: '/admin/settings' },
    {
      label: 'Project Planning',
      icon: BookOpen,
      color: '#2563eb',
      to: t('/planning/dashboard'),
    },
    {
      label: 'Performance',
      icon: BarChart3,
      color: '#7c3aed',
      to: t('/performance/dashboard'),
    },
    { label: 'Security', icon: ShieldCheck, color: '#dc2626', to: t('/security/dashboard') },
  ]
}
