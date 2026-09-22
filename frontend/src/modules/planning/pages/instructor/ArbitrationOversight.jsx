import { useState } from 'react'
import { ChevronDown, Gavel, CheckCircle2 } from 'lucide-react'
import PageHeader from '../../../../shared/components/PageHeader.jsx'
import Card from '../../../../shared/components/Card.jsx'
import Badge from '../../../../shared/components/Badge.jsx'
import EmptyState from '../../../../shared/components/EmptyState.jsx'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import AgentBadge from '../../components/AgentBadge.jsx'
import { ARBITRATION_CASES, GROUPS } from '../../data/mockData.js'
import { ARBITRATION_CATEGORY_TONE } from '../../utils.js'
import { useAuth } from '../../../../shared/auth/useAuth.js'
import { showToast } from '@/shared/utils/toast.jsx'

const CATEGORIES = ['COMPOUND', 'AMBIGUOUS', 'STRUCTURAL', 'NOVEL']

function groupForRequirement(reqId) {
  return GROUPS.find((g) => g.requirementIds.includes(reqId))
}

function CaseRow({ item, onResolve }) {
  const [expanded, setExpanded] = useState(false)
  const [note, setNote] = useState('')
  const group = groupForRequirement(item.requirementId)

  return (
    <Card className="p-0 overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between gap-3 p-4 text-left cursor-pointer hover:bg-muted/30 transition-colors"
      >
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-xs font-semibold text-muted-foreground">{item.id}</span>
            <Badge tone={ARBITRATION_CATEGORY_TONE[item.category]}>{item.category}</Badge>
            <Badge tone={item.status === 'Open' ? 'warning' : 'success'}>{item.status}</Badge>
            {group && <span className="text-xs text-muted-foreground">{group.name}</span>}
          </div>
          <p className="text-sm font-medium text-foreground truncate">{item.title}</p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <div className="text-right hidden sm:block">
            <p className="text-xs text-muted-foreground">Agreement</p>
            <p className="text-sm font-semibold text-foreground">{item.confidenceAgreement}%</p>
          </div>
          <ChevronDown className={`h-4 w-4 text-muted-foreground transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`} />
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 space-y-4 animate-fade-rise">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {Object.entries(item.agentRationale).map(([agentKey, r]) => (
              <div key={agentKey} className="p-3 rounded-lg border border-border bg-muted/20">
                <div className="flex items-center justify-between mb-2">
                  <AgentBadge agent={agentKey} />
                  <span className="text-xs font-medium text-muted-foreground">{r.confidence}% conf.</span>
                </div>
                <p className="text-xs font-semibold text-foreground mb-1">{r.verdict}</p>
                <p className="text-xs text-muted-foreground leading-relaxed">{r.rationale}</p>
              </div>
            ))}
          </div>

          <div className="p-3 rounded-lg border border-primary/20 bg-primary/5">
            <div className="flex items-center gap-2 mb-1">
              <Gavel className="h-3.5 w-3.5 text-primary" />
              <span className="text-xs font-semibold uppercase tracking-wider text-primary">DART resolution</span>
            </div>
            <p className="text-sm text-foreground leading-relaxed">{item.resolution}</p>
            {item.resolvedBy && (
              <p className="text-xs text-muted-foreground mt-1.5">Confirmed by {item.resolvedBy}</p>
            )}
          </div>

          {item.status === 'Open' && (
            <div className="space-y-2">
              <Textarea
                placeholder="Optional justification for confirming or overriding this resolution…"
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
              <div className="flex justify-end">
                <Button size="sm" onClick={() => onResolve(item.id, note)} className="active:scale-[0.98]">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  Confirm resolution
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  )
}

export default function ArbitrationOversight() {
  const { user } = useAuth()
  const [cases, setCases] = useState(ARBITRATION_CASES)
  const [category, setCategory] = useState('all')
  const [status, setStatus] = useState('all')

  const filtered = cases.filter((c) => {
    if (category !== 'all' && c.category !== category) return false
    if (status !== 'all' && c.status !== status) return false
    return true
  })

  function resolveCase(id, note) {
    setCases((prev) =>
      prev.map((c) =>
        c.id === id
          ? {
              ...c,
              status: 'Resolved',
              resolvedBy: user.name,
              resolution: note ? `${c.resolution}\n\nInstructor note: ${note}` : c.resolution,
            }
          : c,
      ),
    )
    showToast.success('Arbitration confirmed', { description: `${id} marked resolved.` })
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Arbitration Oversight"
        breadcrumb={['Planning', 'Instructor', 'Arbitration Oversight']}
        description="Cross-group DART queue — review structured diagnostic rationales and confirm or override a resolution."
        actions={
          <>
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {CATEGORIES.map((c) => (
                  <SelectItem key={c} value={c}>
                    {c}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="w-[130px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                <SelectItem value="Open">Open</SelectItem>
                <SelectItem value="Resolved">Resolved</SelectItem>
              </SelectContent>
            </Select>
          </>
        }
      />

      {filtered.length === 0 ? (
        <EmptyState title="No matching cases" description="Try a different category or status filter." />
      ) : (
        <div className="space-y-3">
          {filtered.map((item) => (
            <CaseRow key={item.id} item={item} onResolve={resolveCase} />
          ))}
        </div>
      )}
    </div>
  )
}
