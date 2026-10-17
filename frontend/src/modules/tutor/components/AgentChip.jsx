import { AGENTS } from '../data/mockTutorData.js'

export default function AgentChip({ agent, className = '' }) {
  const meta = AGENTS[agent] || AGENTS.learning
  const Icon = meta.icon
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 text-[10px] font-semibold ${meta.tone} ${className}`}
    >
      <Icon className="h-3 w-3" />
      {meta.label}
    </span>
  )
}
