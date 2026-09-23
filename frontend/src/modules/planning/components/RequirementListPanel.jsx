import { useState } from 'react'
import { Search, CheckCircle2, AlertTriangle, XCircle, Circle, Lock } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import Card from '../../../shared/components/Card.jsx'

const FILTER_TABS = [
  { key: 'all', label: 'All' },
  { key: 'attention', label: 'Needs Attention' },
  { key: 'passed', label: 'Passed' },
]

function StatusIcon({ tone, locked }) {
  if (locked) return <Lock className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
  if (tone === 'success') return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
  if (tone === 'warning') return <AlertTriangle className="h-3.5 w-3.5 text-amber-500 shrink-0" />
  if (tone === 'danger') return <XCircle className="h-3.5 w-3.5 text-destructive shrink-0" />
  return <Circle className="h-3.5 w-3.5 text-muted-foreground/40 shrink-0" />
}

// Shared requirement list — used identically by SRS Quality, Decomposition and
// Effort Estimation so the "pick a requirement" interaction always looks and
// behaves the same. Each page supplies getItemMeta() to say what "done" and
// "%" mean on that page (quality score, decomposition %, estimation %).
export default function RequirementListPanel({ requirements, selectedId, onSelect, getItemMeta, maxHeight = 600 }) {
  const [search, setSearch] = useState('')
  const [filterTab, setFilterTab] = useState('all')

  const withMeta = requirements.map((r) => ({ req: r, meta: getItemMeta(r) }))

  const filtered = withMeta
    .filter(({ meta }) => {
      if (filterTab === 'attention') return meta.tone !== 'success'
      if (filterTab === 'passed') return meta.tone === 'success'
      return true
    })
    .filter(
      ({ req }) =>
        !search.trim() ||
        req.title.toLowerCase().includes(search.toLowerCase()) ||
        req.id.toLowerCase().includes(search.toLowerCase()),
    )

  return (
    <Card className="p-0 overflow-hidden">
      <div className="p-3 border-b border-border space-y-2">
        <div className="relative">
          <Search className="h-3.5 w-3.5 text-muted-foreground absolute left-2.5 top-1/2 -translate-y-1/2" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search requirements…"
            className="pl-8 h-8 text-xs"
          />
        </div>
        <div className="flex items-center gap-1 flex-wrap">
          {FILTER_TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setFilterTab(t.key)}
              className={`text-[11px] font-medium px-2 py-1 rounded-md cursor-pointer transition-colors ${
                filterTab === t.key ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-muted'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
      <ul className="divide-y divide-border/60 overflow-y-auto column-scroll-contain" style={{ maxHeight }}>
        {filtered.length === 0 && <li className="p-4 text-xs text-muted-foreground text-center">No requirements match.</li>}
        {filtered.map(({ req, meta }) => (
          <li key={req.id}>
            <button
              type="button"
              onClick={() => onSelect(req.id)}
              className={`w-full text-left p-3 cursor-pointer transition-colors hover:bg-muted/40 ${
                selectedId === req.id ? 'bg-muted/60' : ''
              }`}
            >
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="text-xs font-medium text-muted-foreground">{req.id}</span>
                <StatusIcon tone={meta.tone} locked={meta.locked} />
              </div>
              <p className="text-sm text-foreground line-clamp-2 leading-snug">{req.title}</p>
              <div className="flex items-center gap-2 mt-2">
                <Progress value={meta.percent} className="h-1 flex-1" />
                <span className="text-xs font-medium text-muted-foreground w-9 text-right">{meta.percent}%</span>
              </div>
            </button>
          </li>
        ))}
      </ul>
    </Card>
  )
}
