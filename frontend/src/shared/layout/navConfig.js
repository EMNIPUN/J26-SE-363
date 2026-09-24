import {
  LayoutDashboard,
  BookOpen,
  BarChart3,
  Bot,
  ShieldCheck,
  Users,
  Settings,
} from 'lucide-react'

// One nav tree per role. `to` on a parent makes the whole group a link too
// (used for single-page sections); `children` renders an expandable list.
export function getNavForRole(role) {
  if (role === 'student') {
    return [
      { label: 'Overview', icon: LayoutDashboard, to: '/app' },
      {
        label: 'Project Planning',
        icon: BookOpen,
        color: '#2563eb',
        children: [
          { label: 'Dashboard', to: '/planning/dashboard' },
          { label: 'Blackboard', to: '/planning/blackboard' },
          { label: 'Traceability', to: '/planning/requirements/traceability' },
          { label: 'Estimation', to: '/planning/requirements/estimation' },
          { label: 'SRS Quality', to: '/planning/requirements/srs-quality' },
          { label: 'Decomposition', to: '/planning/requirements/decomposition' },
        ],
      },
      {
        label: 'Performance',
        icon: BarChart3,
        color: '#7c3aed',
        to: '/performance/my-progress',
      },
      {
        label: 'AI Tutor',
        icon: Bot,
        color: '#16a34a',
        children: [
          { label: 'Landing', to: '/tutor/landing' },
          { label: 'Chat', to: '/tutor/chat' },
          { label: 'Nudges', to: '/tutor/nudges' },
        ],
      },
      {
        label: 'Project Security',
        icon: ShieldCheck,
        color: '#dc2626',
        children: [
          { label: 'Dashboard', to: '/security/dashboard' },
          { label: 'Scan Report', to: '/security/scan-report' },
          { label: 'Remediation', to: '/security/remediation' },
        ],
      },
    ]
  }

  if (role === 'instructor') {
    return [
      { label: 'Overview', icon: LayoutDashboard, to: '/app' },
      {
        label: 'Project Planning',
        icon: BookOpen,
        color: '#2563eb',
        children: [
          { label: 'Dashboard', to: '/planning/dashboard' },
          { label: 'Projects', to: '/planning/projects' },
          { label: 'Groups', to: '/planning/groups' },
        ],
      },
      {
        label: 'Performance',
        icon: BarChart3,
        color: '#7c3aed',
        children: [
          { label: 'Dashboard', to: '/performance/dashboard' },
          { label: 'Student Detail', to: '/performance/students' },
          { label: 'Assessments', to: '/performance/assessments' },
          { label: 'Reports', to: '/performance/reports' },
        ],
      },
      {
        label: 'AI Tutor',
        icon: Bot,
        color: '#16a34a',
        children: [
          { label: 'Landing', to: '/tutor/landing' },
          { label: 'Chat', to: '/tutor/chat' },
          { label: 'Nudges', to: '/tutor/nudges' },
        ],
      },
      {
        label: 'Security',
        icon: ShieldCheck,
        color: '#dc2626',
        children: [
          { label: 'Dashboard', to: '/security/dashboard' },
          { label: 'Scan Report', to: '/security/scan-report' },
          { label: 'Remediation', to: '/security/remediation' },
        ],
      },
    ]
  }

  // admin
  return [
    { label: 'Overview', icon: LayoutDashboard, to: '/app' },
    { label: 'Users', icon: Users, to: '/admin/users' },
    { label: 'Settings', icon: Settings, to: '/admin/settings' },
    {
      label: 'Project Planning',
      icon: BookOpen,
      color: '#2563eb',
      to: '/planning/dashboard',
    },
    {
      label: 'Performance',
      icon: BarChart3,
      color: '#7c3aed',
      to: '/performance/dashboard',
    },
    { label: 'AI Tutor', icon: Bot, color: '#16a34a', to: '/tutor/landing' },
    { label: 'Security', icon: ShieldCheck, color: '#dc2626', to: '/security/dashboard' },
  ]
}
