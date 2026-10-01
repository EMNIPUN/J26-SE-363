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
    tagline: 'Requirements analysis, quality gates & intelligent project planning',
  },
  {
    key: 'performance',
    label: 'Performance Assessment',
    path: '/performance',
    icon: BarChart3,
    color: '#2563eb',
    owner: 'IT23155534 · Kumbukage',
    tagline: 'Individual student contribution scoring & at-risk prediction',
  },
  {
    key: 'tutor',
    label: 'Tutor Agent',
    path: '/tutor',
    icon: Bot,
    color: '#2563eb',
    owner: 'IT23283930 · Ekanayake',
    tagline: 'Adaptive project learning, sprint guidance & learning momentum nudges',
  },
  {
    key: 'security',
    label: 'AEGIS Security',
    path: '/security',
    icon: ShieldCheck,
    color: '#2563eb',
    owner: 'IT23314238 · Croos',
    tagline: 'Security vulnerability detection & remediation reporting',
  },
]

export function getModule(key) {
  return MODULES.find((m) => m.key === key)
}
