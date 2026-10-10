import { BookOpen, BarChart3, Bot, ShieldCheck } from 'lucide-react'

// Registry of the four FYP components. TopNav, Home and each module's
// ModuleLayout all read from this so labels/colors stay in one place.
export const MODULES = [
  {
    key: 'planning',
    label: 'Project Planning',
    path: '/planning',
    icon: BookOpen,
    color: '#2563eb',
    owner: 'IT23152878 · Rajapaksha',
    tagline: 'Requirements, estimates, and the sprint board',
  },
  {
    key: 'performance',
    label: 'Performance Assessment',
    path: '/performance',
    icon: BarChart3,
    color: '#2563eb',
    owner: 'IT23155534 · Kumbukage',
    tagline: 'How the work is going, without a public ranking',
  },
  {
    key: 'tutor',
    label: 'AI Tutor',
    path: '/tutor',
    icon: Bot,
    color: '#2563eb',
    owner: 'IT23283930 · Ekanayake',
    tagline: 'Help that starts from the task you are doing',
  },
  {
    key: 'security',
    label: 'AEGIS Security',
    path: '/security',
    icon: ShieldCheck,
    color: '#2563eb',
    owner: 'IT23314238 · Croos',
    tagline: 'Findings in the project code, and how to fix them',
  },
]

export function getModule(key) {
  return MODULES.find((m) => m.key === key)
}
