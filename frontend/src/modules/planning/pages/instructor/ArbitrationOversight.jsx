import { useState } from 'react'
import { ChevronDown, Gavel, CheckCircle2, Search, Tag, MessageCircleQuestion, MessageCircleReply, Scale } from 'lucide-react'
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
import DartButton from '../../components/DartButton.jsx'
import { GROUPS } from '../../data/mockData.js'
import { ARBITRATION_CATEGORY_TONE } from '../../utils.js'
import { useAuth } from '../../../../shared/auth/useAuth.js'
import { showToast } from '@/shared/utils/toast.jsx'
import { useDartCases, useResolveCase } from '../../hooks/useDart.js'
import { mapDartCases } from '../../adapters/dart.js'

const CATEGORIES = ['compound', 'ambiguous', 'structural', 'novel', 'insufficient_evidence']
const CATEGORY_LABELS = {
  compound: 'COMPOUND',
  ambiguous: 'AMBIGUOUS',
  structural: 'STRUCTURAL',
  novel: 'NOVEL',
  insufficient_evidence: 'INSUFFICIENT',
}

const PROTOCOL_STEPS = [
  { key: 'gather', label: 'Gather', icon: Search },
  { key: 'categorize', label: 'Categorize', icon: Tag },
  { key: 'consult', label: 'Consult', icon: MessageCircleQuestion },
  { key: 'respond', label: 'Respond', icon: MessageCircleReply },
  { key: 'resolve', label: 'Resolve', icon: Scale },
]

function groupForRequirement(reqId) {
  return GROUPS.find((g) => g.requirementIds.includes(reqId))
}

function isEscalated(c) {
  return c.category === 'novel' || c.confidenceAgreement < 40
}

function ProtocolStepper({ item }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-1.5 overflow-x-auto py-1">
        {PROTOCOL_STEPS.map((step, i) => {
          const Icon = step.icon
          return (
            <div key={step.key} className="flex items-center gap-1.5">
              <div className="flex items-center gap-1 px-2 py-1 rounded-md bg-primary/10 text-primary">
                <Icon className="h-3.5 w-3.5" />
                <span className="text-[11px] font-medium whitespace-nowrap">{step.label}</span>
              </div>
              {i < PROTOCOL_STEPS.length - 1 && <span className="text-muted-foreground text-xs">→</span>}
            </div>
          )
        })}
      </div>

      {item.traces.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Reasoning Traces</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {item.traces.map((t, i) => (
              <div key={i} className="p-2.5 rounded-lg border border-border bg-muted/20">
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold text-foreground">{t.agentName}</span>
                  <span className="text-[10px] text-muted-foreground">{Math.round(t.confidence * 100)}% conf.</span>
                </div>
                <p className="text-xs text-foreground mb-0.5">{t.diagnosis}</p>
                {t.uncertaintyType && (
                  <p className="text-[10px] text-muted-foreground">Uncertainty: {t.uncertaintyType}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {item.hypothesis?.rationale && (
        <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
          <p className="text-[10px] font-semibold text-amber-700 dark:text-amber-400 uppercase tracking-wider mb-1">Diagnostic Hypothesis</p>
          <p className="text-sm text-foreground">{item.hypothesis.rationale}</p>
          {item.hypothesis.supportingEvidence?.length > 0 && (
            <ul className="mt-1.5 space-y-0.5">
              {item.hypothesis.supportingEvidence.map((e, i) => (
                <li key={i} className="text-xs text-muted-foreground">• {e}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {item.consultation?.question && (
        <div className="p-3 rounded-lg bg-blue-500/10 border border-blue-500/20">
          <p className="text-[10px] font-semibold text-blue-700 dark:text-blue-400 uppercase tracking-wider mb-1">
            Targeted Consultation Question
          </p>
          <p className="text-sm text-foreground italic">"{item.consultation.question}"</p>
        </div>
      )}

      {item.response?.answer && (
        <div className="p-3 rounded-lg border border-border bg-muted/20">
          <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">Consultation Response</p>
          <p className="text-sm text-foreground">{item.response.answer}</p>
          {item.response.evidence?.length > 0 && (
            <ul className="mt-1.5 space-y-0.5">
              {item.response.evidence.map((e, i) => (
                <li key={i} className="text-xs text-muted-foreground">• {e}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {item.resolution?.actionableFeedback && (
        <div className="p-3 rounded-lg border border-primary/20 bg-primary/5">
          <div className="flex items-center gap-2 mb-1">
            <Gavel className="h-3.5 w-3.5 text-primary" />
            <span className="text-xs font-semibold uppercase tracking-wider text-primary">DART Resolution</span>
            <Badge tone={item.resolution.action === 'escalate' ? 'danger' : 'success'}>
              {(item.resolution.action || '').toUpperCase()}
            </Badge>
            <span className="text-[10px] text-muted-foreground ml-auto">{item.resolution.confidenceAgreement}% agreement</span>
          </div>
          <p className="text-sm text-foreground leading-relaxed">{item.resolution.actionableFeedback}</p>
        </div>
      )}
    </div>
  )
}

function CaseRow({ item, onResolve }) {
  const [expanded, setExpanded] = useState(false)
  const [note, setNote] = useState('')
  const group = groupForRequirement(item.requirementId)
  const tone = ARBITRATION_CATEGORY_TONE[item.category?.toUpperCase?.()] || ARBITRATION_CATEGORY_TONE[item.category] || 'muted'

  return (
    <Card className="p-0 overflow-hidden">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between gap-3 p-4 text-left cursor-pointer hover:bg-muted/30 transition-colors"
      >
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-xs font-semibold text-muted-foreground">{item.caseRef || item.id}</span>
            <Badge tone={tone}>{item.categoryLabel || item.category}</Badge>
            <Badge tone={item.status === 'open' ? 'warning' : item.status === 'escalated' ? 'danger' : 'success'}>{item.statusLabel}</Badge>
            {item.status === 'open' && isEscalated(item) && <Badge tone="danger">Escalated</Badge>}
            {group && <span className="text-xs text-muted-foreground">{group.name}</span>}
          </div>
          <p className="text-sm font-medium text-foreground truncate">{item.title}</p>
          <p className="text-xs text-muted-foreground">{item.requirementId} · {item.stage}</p>
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
          <ProtocolStepper item={item} />

          {item.resolvedBy && (
            <p className="text-xs text-muted-foreground">Resolved by {item.resolvedBy}</p>
          )}

          {item.status === 'open' && (
            <div className="space-y-2">
              <Textarea
                placeholder="Optional justification for confirming or overriding this resolution..."
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
              <div className="flex justify-end">
                <Button size="sm" onClick={() => onResolve(item.caseRef || item.id, note)} className="active:scale-[0.98]">
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
  const { data: dartData, isLoading } = useDartCases()
  const resolveMutation = useResolveCase()
  const cases = mapDartCases(dartData?.cases || [])

  const [category, setCategory] = useState('all')
  const [status, setStatus] = useState('all')
  const [escalatedOnly, setEscalatedOnly] = useState(false)

  const escalatedCount = cases.filter((c) => c.status === 'open' && isEscalated(c)).length

  const filtered = cases
    .filter((c) => {
      if (category !== 'all' && c.category !== category) return false
      if (status !== 'all' && c.status !== status) return false
      if (escalatedOnly && !(c.status === 'open' && isEscalated(c))) return false
      return true
    })
    .sort((a, b) => Number(isEscalated(b) && b.status === 'open') - Number(isEscalated(a) && a.status === 'open'))

  function resolveCase(caseRef, note) {
    resolveMutation.mutate(
      { caseRef, body: { status: 'resolved', note } },
      {
        onSuccess: () => showToast.success('Arbitration confirmed', { description: `${caseRef} marked resolved.` }),
        onError: () => showToast.error('Failed to resolve', { description: 'Could not reach the server.' }),
      },
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Arbitration Oversight"
        breadcrumb={['Planning', 'Lecturer', 'Arbitration Oversight']}
        description="Cross-group DART queue — review the five-step diagnostic protocol and confirm or override resolutions."
        actions={
          <>
            <Button
              size="sm"
              variant={escalatedOnly ? 'default' : 'outline'}
              onClick={() => setEscalatedOnly((v) => !v)}
              className="active:scale-[0.98]"
            >
              Escalated only
            </Button>
            <Select value={category} onValueChange={setCategory}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {CATEGORIES.map((c) => (
                  <SelectItem key={c} value={c}>
                    {CATEGORY_LABELS[c] || c}
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
                <SelectItem value="open">Open</SelectItem>
                <SelectItem value="resolved">Resolved</SelectItem>
                <SelectItem value="escalated">Escalated</SelectItem>
              </SelectContent>
            </Select>
          </>
        }
      />

      {escalatedCount > 0 && (
        <Card className="border-destructive/30 flex items-center justify-between gap-3 flex-wrap">
          <p className="text-sm text-foreground">
            <strong>{escalatedCount}</strong> case{escalatedCount === 1 ? '' : 's'} need lecturer review — the agents couldn't resolve {escalatedCount === 1 ? 'it' : 'them'} on their own.
          </p>
          {!escalatedOnly && (
            <Button size="sm" variant="outline" onClick={() => setEscalatedOnly(true)} className="active:scale-[0.98]">
              Show escalated
            </Button>
          )}
        </Card>
      )}

      {isLoading ? (
        <Card className="flex items-center justify-center py-12">
          <p className="text-sm text-muted-foreground animate-pulse">Loading DART cases...</p>
        </Card>
      ) : filtered.length === 0 ? (
        <EmptyState title="No matching cases" description="No DART arbitration cases match the current filters." />
      ) : (
        <div className="space-y-3">
          {filtered.map((item) => (
            <CaseRow key={item.id} item={item} onResolve={resolveCase} />
          ))}
        </div>
      )}

      <DartButton context="cohort" />
    </div>
  )
}
