import { useState } from 'react'
import { Search, CheckCircle2, AlertTriangle, XCircle, Circle, Lock, ShieldCheck, Check } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Progress } from '@/components/ui/progress'
import Card from '../../../shared/components/Card.jsx'

const FILTER_TABS = [
  { key: 'all', label: 'All' },
  { key: 'attention', label: 'Needs Attention' },
  { key: 'passed', label: 'Passed' },
]

function StatusIcon({ tone, locked, finalized, passed }) {
  if (locked) return <Lock className="h-3.5 w-3.5 text-muted-foreground shrink-0" title="Locked" />
  if (finalized) return <ShieldCheck className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" title="Finalized" />
  if (passed || tone === 'success') return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" title="Stage Passed" />
  if (tone === 'warning') return <AlertTriangle className="h-3.5 w-3.5 text-amber-500 shrink-0" title="Needs Attention" />
  if (tone === 'danger') return <XCircle className="h-3.5 w-3.5 text-destructive shrink-0" title="Failing Gate" />
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
      const isPassed = Boolean(meta.passed || meta.tone === 'success' || meta.finalized)
      if (filterTab === 'attention') return !isPassed
      if (filterTab === 'passed') return isPassed
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
        {filtered.map(({ req, meta }) => {
          const isSelected = Boolean(
            selectedId &&
              req.id &&
              String(selectedId).trim().toLowerCase() === String(req.id).trim().toLowerCase(),
          )
          const isPassed = Boolean(meta.passed || meta.tone === 'success' || meta.finalized)

          return (
            <li key={req.id}>
              <button
                type="button"
                disabled={meta.locked}
                aria-current={isSelected ? 'true' : undefined}
                onClick={() => !meta.locked && onSelect(req.id)}
                className={`w-full text-left p-3 cursor-pointer transition-all outline-none focus-visible:bg-muted relative ${
                  meta.locked
                    ? 'opacity-55 bg-muted/20 cursor-not-allowed border-l-4 border-l-transparent'
                    : isSelected
                    ? isPassed
                      ? 'bg-accent/80 dark:bg-accent/45 border-l-4 border-l-emerald-500 shadow-2xs'
                      : 'bg-accent/80 dark:bg-accent/45 border-l-4 border-l-primary shadow-2xs'
                    : isPassed
                    ? 'hover:bg-muted/40 border-l-4 border-l-emerald-500/70 bg-emerald-500/[0.03]'
                    : 'hover:bg-muted/40 border-l-4 border-l-transparent'
                }`}
              >
                <div className="flex items-center justify-between gap-2 mb-1">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span
                      className={`font-mono text-xs ${
                        meta.locked
                          ? 'text-muted-foreground/60'
                          : isSelected
                          ? 'font-bold text-primary'
                          : 'font-medium text-muted-foreground'
                      }`}
                    >
                      {req.id}
                    </span>
                    {isSelected && (
                      <span className="text-[10px] font-semibold text-primary/90 bg-primary/10 px-1.5 py-0.2 rounded">
                        Active
                      </span>
                    )}
                    {isPassed && (
                      <span className="inline-flex items-center gap-1 text-[10px] font-bold text-emerald-700 dark:text-emerald-400 bg-emerald-500/15 border border-emerald-500/30 px-1.5 py-0.2 rounded-full shadow-2xs">
                        <Check className="h-2.5 w-2.5 stroke-[2.5]" />
                        <span>{meta.stageLabel || 'Passed'}</span>
                      </span>
                    )}
                  </div>
                  <StatusIcon tone={meta.tone} locked={meta.locked} finalized={meta.finalized} passed={isPassed} />
                </div>

                <p
                  className={`text-sm line-clamp-2 leading-snug transition-colors ${
                    meta.locked
                      ? 'text-muted-foreground font-normal'
                      : isSelected
                      ? 'text-foreground font-semibold'
                      : 'text-muted-foreground font-normal'
                  }`}
                >
                  {req.title}
                </p>

                <div className="flex items-center gap-2 mt-2">
                  <Progress
                    value={meta.percent}
                    className={`h-1 flex-1 ${meta.locked ? 'opacity-30' : isPassed ? '[&>div]:bg-emerald-500' : ''}`}
                  />
                  <span
                    className={`text-xs font-mono w-9 text-right ${
                      isPassed
                        ? 'text-emerald-600 dark:text-emerald-400 font-bold'
                        : isSelected
                        ? 'text-foreground font-semibold'
                        : 'text-muted-foreground'
                    }`}
                  >
                    {meta.percent}%
                  </span>
                </div>
              </button>
            </li>
          )
        })}
      </ul>
    </Card>
  )
}

