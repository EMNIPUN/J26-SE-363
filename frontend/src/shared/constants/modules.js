// Registry of the four FYP components. TopNav, Home and each module's
// ModuleLayout all read from this so labels/colors stay in one place.
export const MODULES = [
  {
    key: 'planning',
    label: 'Project Planning',
    path: '/planning',
    color: '#2563eb',
    owner: 'IT23152878 · Rajapaksha',
    tagline: 'Requirements analysis, quality gates & intelligent project planning',
  },
  {
    key: 'performance',
    label: 'Performance Assessment',
    path: '/performance',
    color: '#7c3aed',
    owner: 'IT23155534 · Kumbukage',
    tagline: 'Individual student contribution scoring & at-risk prediction',
  },
  {
    key: 'tutor',
    label: 'Adaptive AI Tutor',
    path: '/tutor',
    color: '#16a34a',
    owner: 'IT23283930 · Ekanayake',
    tagline: 'Project learning, sprint guidance & learning momentum agents',
  },
  {
    key: 'security',
    label: 'AEGIS Security',
    path: '/security',
    color: '#dc2626',
    owner: 'IT23314238 · Croos',
    tagline: 'Security vulnerability detection & remediation reporting',
  },
]

export function getModule(key) {
  return MODULES.find((m) => m.key === key)
}
