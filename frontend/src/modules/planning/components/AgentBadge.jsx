import { ShieldCheck, GitBranch, Gauge } from 'lucide-react'
import { AGENTS } from '../data/mockData.js'

const AGENT_ICON = {
  quality: ShieldCheck,
  decomposition: GitBranch,
  estimation: Gauge,
}

export default function AgentBadge({ agent, className = '' }) {
  const meta = AGENTS[agent]
  const Icon = AGENT_ICON[agent]
  if (!meta) return null

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-xs font-medium border ${className}`}
      style={{
        color: meta.color,
        borderColor: `${meta.color}33`,
        backgroundColor: `${meta.color}14`,
      }}
    >
      <Icon className="h-3 w-3" strokeWidth={2.25} />
      {meta.short}
    </span>
  )
}
