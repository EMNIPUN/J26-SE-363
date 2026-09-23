import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  UploadCloud,
  FileText,
  Plus,
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Lock,
  ArrowRight,
  History,
  Gavel,
} from 'lucide-react'
import PageHeader from '../../../../../shared/components/PageHeader.jsx'
import Card from '../../../../../shared/components/Card.jsx'
import Badge from '../../../../../shared/components/Badge.jsx'
import LoadingState from '../../../../../shared/components/LoadingState.jsx'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import WorkflowStepper from '../../../components/WorkflowStepper.jsx'
import DartButton from '../../../components/DartButton.jsx'
import RequirementListPanel from '../../../components/RequirementListPanel.jsx'
import QualityRadarChart from '../../../components/QualityRadarChart.jsx'
import HighlightedRequirementText from '../../../components/HighlightedRequirementText.jsx'
import { usePlanningData } from '../../../context/usePlanningData.js'
import { QUALITY_DIMENSIONS, getArbitrationForRequirement } from '../../../data/mockData.js'
import { GATE_STATUS_TONE, QUALITY_GATE_THRESHOLD, DIMENSION_ISSUE, formatRelativeTime } from '../../../utils.js'
import { showToast } from '@/shared/utils/toast.jsx'

function dimTier(score) {
  if (score >= 80) return 'pass'
  if (score >= 60) return 'warn'
  return 'fail'
}

const DIM_ICON = {
  pass: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />,
  warn: <AlertTriangle className="h-3.5 w-3.5 text-amber-500 shrink-0" />,
  fail: <XCircle className="h-3.5 w-3.5 text-destructive shrink-0" />,
}

let manualIdCounter = 200

export default function SRSQuality() {
  const { requirements, addRequirement, updateRequirementText, rescoreRequirement, getRequirementHistory } =
    usePlanningData()
  const [selectedId, setSelectedId] = useState(requirements[0]?.id ?? null)
  const [checkingId, setCheckingId] = useState(null)
  const [draft, setDraft] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [docName, setDocName] = useState('SRS_NexaPlan_v3.docx')
  const [addOpen, setAddOpen] = useState(false)
  const [newReq, setNewReq] = useState({ title: '', description: '' })
  const [historyOpen, setHistoryOpen] = useState(false)
  const fileInputRef = useRef(null)

  const selected = requirements.find((r) => r.id === selectedId) || null
  const currentDraft =
    draft && draft.id === selectedId ? draft : { id: selectedId, title: selected?.title || '', description: selected?.description || '' }

  const avgScore = requirements.length
    ? Math.round(requirements.reduce((sum, r) => sum + r.overallScore, 0) / requirements.length)
    : 0
  const passingCount = requirements.filter((r) => r.status === 'Passing').length
  const attentionCount = requirements.filter((r) => r.status !== 'Passing').length
  const failingCount = requirements.filter((r) => r.status === 'Failing').length

  function selectRequirement(id) {
    setSelectedId(id)
    setDraft(null)
    setHistoryOpen(false)
  }

  function runQualityCheck(reqId, patch) {
    setCheckingId(reqId)
    if (patch) updateRequirementText(reqId, patch)
    setTimeout(() => {
      const req = requirements.find((r) => r.id === reqId)
      const delta = req?.status === 'Passing' ? Math.floor(Math.random() * 3) : 6 + Math.floor(Math.random() * 8)
      rescoreRequirement(reqId, delta)
      setCheckingId(null)
      setDraft(null)
      showToast.success('AI analysis complete', {
        description: `${reqId} has been re-scored against all six dimensions.`,
      })
    }, 900)
  }

  function simulateUpload() {
    setUploading(true)
    setTimeout(() => {
      const id1 = `REQ-1${manualIdCounter++}`
      addRequirement({
        id: id1,
        title: 'System shall let a student export their requirement set as a PDF',
        description: 'The system shall generate a downloadable PDF snapshot of all requirements and their quality scores.',
        priority: 'Low',
        status: 'Needs Review',
        overallScore: 62,
        dimensionScores: { clarity: 70, completeness: 60, consistency: 65, testability: 55, feasibility: 72, scope: 60 },
        suggestedRewrite: 'Specify what "export" must include: which fields, and whether historical versions are included.',
        lastChecked: new Date().toISOString(),
      })
      setDocName(`SRS_NexaPlan_v4.docx`)
      setUploading(false)
      showToast.success('Document processed', {
        description: '1 new requirement extracted and scored by the Quality Analysis agent.',
      })
    }, 1400)
  }

  function submitManualRequirement() {
    if (!newReq.title.trim()) return
    const id = `REQ-1${manualIdCounter++}`
    addRequirement({
      id,
      title: newReq.title,
      description: newReq.description || newReq.title,
      priority: 'Medium',
      status: 'Needs Review',
      overallScore: 58,
      dimensionScores: { clarity: 55, completeness: 55, consistency: 60, testability: 55, feasibility: 65, scope: 58 },
      suggestedRewrite: null,
      lastChecked: new Date().toISOString(),
    })
    setNewReq({ title: '', description: '' })
    setAddOpen(false)
    setSelectedId(id)
    showToast.success('Requirement added and scored', {
      description: `${id} was analyzed automatically — review the AI analysis on the right.`,
    })
  }

  const openCases = selected ? getArbitrationForRequirement(selected.id).filter((c) => c.status === 'Open') : []
  const history = selected ? getRequirementHistory(selected.id) : []
  const scoreTrend = history.length >= 2 ? history[history.length - 1].score - history[history.length - 2].score : null

  return (
    <div className="space-y-6">
      <PageHeader
        title="SRS Quality Gate"
        breadcrumb={['Planning', 'Requirements', 'SRS Quality']}
        description="Upload your SRS or add requirements manually. Every requirement is scored against six quality dimensions and must pass before it can be decomposed."
        actions={
          <Badge tone={avgScore >= QUALITY_GATE_THRESHOLD ? 'success' : 'warning'} className="text-sm px-3 py-1">
            {avgScore >= QUALITY_GATE_THRESHOLD ? '🔓' : '🔒'} Quality {avgScore}% · {passingCount}/{requirements.length} passed
          </Badge>
        }
      />

      <WorkflowStepper current="quality" />

      <Card className="p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary shrink-0">
            <FileText className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground truncate">{docName}</p>
            <p className="text-xs text-muted-foreground">
              {requirements.length} requirements extracted · {passingCount} passed · {attentionCount} need attention
              {failingCount > 0 ? ` (${failingCount} failing)` : ''}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <input
            ref={fileInputRef}
            type="file"
            accept=".doc,.docx,.pdf,.txt"
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.[0]) simulateUpload()
              e.target.value = ''
            }}
          />
          <Button size="sm" variant="outline" disabled={uploading} onClick={() => fileInputRef.current?.click()} className="active:scale-[0.98]">
            <UploadCloud className={`h-3.5 w-3.5 ${uploading ? 'animate-pulse' : ''}`} />
            {uploading ? 'Extracting…' : 'Upload / re-upload SRS'}
          </Button>
          <Button size="sm" onClick={() => setAddOpen(true)} className="active:scale-[0.98]">
            <Plus className="h-3.5 w-3.5" />
            Add manually
          </Button>
        </div>
      </Card>

      <LoadingState loading={uploading} variant="card" className="h-24">
        <div className="grid grid-cols-1 xl:grid-cols-[280px_1fr_300px] gap-5 items-start">
          {/* Column 1 — Requirements list */}
          <RequirementListPanel
            requirements={requirements}
            selectedId={selectedId}
            onSelect={selectRequirement}
            getItemMeta={(r) => ({
              percent: r.overallScore,
              tone: r.status === 'Passing' ? 'success' : r.status === 'Needs Review' ? 'warning' : 'danger',
            })}
          />

          {/* Column 2 — Requirement editor */}
          {selected && (
            <div className="space-y-4">
              <Card>
                <div className="flex items-start justify-between gap-3 mb-3 flex-wrap">
                  <p className="text-xs font-semibold text-muted-foreground">{selected.id}</p>
                  <div className="flex items-center gap-2 shrink-0">
                    {scoreTrend !== null && scoreTrend !== 0 && (
                      <span className={`text-xs font-medium ${scoreTrend > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-destructive'}`}>
                        {scoreTrend > 0 ? '↑' : '↓'} {Math.abs(scoreTrend)}%
                      </span>
                    )}
                    <Badge tone={GATE_STATUS_TONE[selected.status]} className="text-sm px-2.5 py-1">
                      {selected.overallScore}% — {selected.status}
                    </Badge>
                  </div>
                </div>

                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Original requirement</p>
                <HighlightedRequirementText
                  text={selected.description}
                  className="text-sm text-foreground leading-relaxed p-3 rounded-lg bg-muted/30 border border-border mb-4"
                />

                <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Your revision</p>
                <div className="space-y-2 mb-3">
                  <Input value={currentDraft.title} onChange={(e) => setDraft({ ...currentDraft, title: e.target.value })} className="text-sm font-medium" />
                  <Textarea
                    value={currentDraft.description}
                    onChange={(e) => setDraft({ ...currentDraft, description: e.target.value })}
                    className="min-h-20 text-sm"
                  />
                </div>

                <div className="flex items-center justify-between flex-wrap gap-2">
                  {selected.suggestedRewrite && (
                    <button
                      type="button"
                      className="text-xs text-primary hover:underline cursor-pointer"
                      onClick={() => setDraft({ id: selected.id, title: currentDraft.title, description: selected.suggestedRewrite })}
                    >
                      Apply AI suggestion to editor
                    </button>
                  )}
                  <Button
                    size="sm"
                    className="ml-auto active:scale-[0.98]"
                    disabled={checkingId === selected.id}
                    onClick={() => runQualityCheck(selected.id, { title: currentDraft.title, description: currentDraft.description })}
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${checkingId === selected.id ? 'animate-spin' : ''}`} />
                    {checkingId === selected.id ? 'Analyzing…' : 'Save & run quality check'}
                  </Button>
                </div>
              </Card>

              {/* Requirement-level quality gate */}
              <Card className={selected.status === 'Passing' ? 'border-emerald-500/30' : 'border-amber-500/30'}>
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div className="flex items-center gap-2">
                    {selected.status === 'Passing' ? (
                      <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0" />
                    ) : (
                      <Lock className="h-5 w-5 text-amber-500 shrink-0" />
                    )}
                    <div>
                      <p className="text-sm font-semibold text-foreground">
                        Quality Gate — {selected.status === 'Passing' ? 'PASSED' : 'BLOCKED'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {selected.status === 'Passing'
                          ? `${QUALITY_DIMENSIONS.filter((d) => selected.dimensionScores[d.key] >= QUALITY_GATE_THRESHOLD).length}/${QUALITY_DIMENSIONS.length} dimensions satisfied`
                          : `${QUALITY_DIMENSIONS.filter((d) => selected.dimensionScores[d.key] < QUALITY_GATE_THRESHOLD).length} dimension(s) below the ${QUALITY_GATE_THRESHOLD}% gate — revise and re-run`}
                      </p>
                    </div>
                  </div>
                  {selected.status === 'Passing' && (
                    <Link to="/planning/requirements/decomposition" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline shrink-0">
                      Continue to Decomposition <ArrowRight className="h-3 w-3" />
                    </Link>
                  )}
                </div>
              </Card>

              {openCases.length > 0 && (
                <Card className="border-primary/20">
                  <div className="flex items-center gap-2 mb-1">
                    <Gavel className="h-3.5 w-3.5 text-primary" />
                    <span className="text-xs font-semibold uppercase tracking-wider text-primary">DART flag on this requirement</span>
                  </div>
                  {openCases.map((c) => (
                    <p key={c.id} className="text-xs text-muted-foreground leading-relaxed">
                      <Badge tone="warning" className="mr-1.5">{c.category}</Badge>
                      {c.title} — agents agree {c.confidenceAgreement}% of the time.
                    </p>
                  ))}
                </Card>
              )}

              <Card className="p-0 overflow-hidden">
                <button
                  type="button"
                  onClick={() => setHistoryOpen((v) => !v)}
                  className="w-full flex items-center justify-between p-3.5 cursor-pointer hover:bg-muted/30 transition-colors"
                >
                  <span className="flex items-center gap-2 text-sm font-medium text-foreground">
                    <History className="h-3.5 w-3.5 text-muted-foreground" />
                    Analysis history ({history.length})
                  </span>
                  <span className="text-xs text-muted-foreground">{historyOpen ? 'Hide' : 'Show'}</span>
                </button>
                {historyOpen && (
                  <div className="px-3.5 pb-3.5 space-y-2 animate-fade-rise">
                    {history.map((h) => (
                      <div key={h.version} className="flex items-center gap-3 text-xs">
                        <span className="h-5 w-5 rounded-full bg-muted flex items-center justify-center text-[10px] font-semibold text-muted-foreground shrink-0">
                          v{h.version}
                        </span>
                        <span className="text-foreground font-medium">{h.score}%</span>
                        <Badge tone={GATE_STATUS_TONE[h.status]}>{h.status}</Badge>
                        <span className="text-muted-foreground ml-auto">{formatRelativeTime(h.timestamp)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          )}

          {/* Column 3 — AI analysis */}
          {selected && (
            <Card>
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">AI Analysis</p>
              <div className="flex items-center gap-2 mb-4">
                {selected.status === 'Passing' ? (
                  <>
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                    <span className="text-sm font-semibold text-foreground">Looks good</span>
                  </>
                ) : (
                  <>
                    <AlertTriangle className="h-4 w-4 text-amber-500" />
                    <span className="text-sm font-semibold text-foreground">Needs improvement</span>
                  </>
                )}
              </div>

              <QualityRadarChart scores={selected.dimensionScores} height={160} />

              <div className="space-y-3 mt-3">
                {QUALITY_DIMENSIONS.map((dim) => {
                  const score = selected.dimensionScores[dim.key]
                  const tier = dimTier(score)
                  const info = DIMENSION_ISSUE[dim.key]
                  return (
                    <div key={dim.key} className={tier !== 'pass' ? 'p-2.5 rounded-lg bg-muted/30 border border-border' : ''}>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="flex items-center gap-1.5 font-medium text-foreground">
                          {DIM_ICON[tier]}
                          {dim.label}
                        </span>
                        <span className="text-muted-foreground">{score}%</span>
                      </div>
                      {tier !== 'pass' && (
                        <div className="mt-1.5 space-y-1">
                          <p className="text-[11px] text-foreground">
                            <span className="font-semibold">Issue: </span>
                            {info.issue}
                          </p>
                          <p className="text-[11px] text-muted-foreground">
                            <span className="font-semibold text-foreground">Why this matters: </span>
                            {info.whyItMatters}
                          </p>
                          <p className="text-[11px] text-muted-foreground">
                            <span className="font-semibold text-foreground">Suggestion: </span>
                            {info.suggestion}
                          </p>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </Card>
          )}
        </div>
      </LoadingState>

      <DartButton context="quality" />

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add requirement manually</DialogTitle>
            <DialogDescription>No SRS document needed — type a requirement and the Quality Analysis agent scores it automatically.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Title</label>
              <Input value={newReq.title} onChange={(e) => setNewReq((f) => ({ ...f, title: e.target.value }))} placeholder="The system shall…" />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1 block">Description</label>
              <Textarea
                value={newReq.description}
                onChange={(e) => setNewReq((f) => ({ ...f, description: e.target.value }))}
                placeholder="Add any extra detail the agent should consider…"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddOpen(false)}>
              Cancel
            </Button>
            <Button onClick={submitManualRequirement} disabled={!newReq.title.trim()}>
              Add & analyze
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
