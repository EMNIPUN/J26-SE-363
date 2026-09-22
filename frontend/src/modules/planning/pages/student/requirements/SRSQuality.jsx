import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  UploadCloud,
  FileText,
  Plus,
  RefreshCw,
  Sparkles,
  CheckCircle2,
  Lock,
  AlertTriangle,
  ArrowRight,
  Gavel,
} from 'lucide-react'
import PageHeader from '../../../../../shared/components/PageHeader.jsx'
import Card from '../../../../../shared/components/Card.jsx'
import Badge from '../../../../../shared/components/Badge.jsx'
import LoadingState from '../../../../../shared/components/LoadingState.jsx'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
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
import QualityRadarChart from '../../../components/QualityRadarChart.jsx'
import { usePlanningData } from '../../../context/usePlanningData.js'
import { QUALITY_DIMENSIONS, QUALITY_GATE_THRESHOLD, getArbitrationForRequirement } from '../../../data/mockData.js'
import { GATE_STATUS_TONE } from '../../../utils.js'
import { showToast } from '@/shared/utils/toast.jsx'

const DIMENSION_FIX_HINTS = {
  clarity: 'Use concrete, unambiguous nouns and verbs — avoid vague words like "should", "fast" or "easy".',
  completeness: 'State every pre-condition, post-condition and edge case this requirement must cover.',
  consistency: "Check this doesn't contradict another requirement or bundle two obligations into one sentence.",
  testability: 'Add a measurable, verifiable threshold — a number, a time limit, an exact behavior.',
  feasibility: 'Confirm the current architecture can actually support this within project constraints.',
  scope: 'Keep this requirement inside the agreed project scope — split out anything tangential.',
}

let manualIdCounter = 200

export default function SRSQuality() {
  const { requirements, addRequirement, updateRequirementText, rescoreRequirement } = usePlanningData()
  const [selectedId, setSelectedId] = useState(requirements[0]?.id ?? null)
  const [checkingId, setCheckingId] = useState(null)
  const [draft, setDraft] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [docName, setDocName] = useState('SRS_NexaPlan_v3.docx')
  const [addOpen, setAddOpen] = useState(false)
  const [newReq, setNewReq] = useState({ title: '', description: '' })
  const fileInputRef = useRef(null)

  const selected = requirements.find((r) => r.id === selectedId) || null
  const currentDraft = draft && draft.id === selectedId ? draft : { id: selectedId, title: selected?.title || '', description: selected?.description || '' }

  const avgScore = requirements.length
    ? Math.round(requirements.reduce((sum, r) => sum + r.overallScore, 0) / requirements.length)
    : 0
  const passingCount = requirements.filter((r) => r.status === 'Passing').length

  function selectRequirement(id) {
    setSelectedId(id)
    setDraft(null)
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
      showToast.ai('Quality Analysis Agent finished', {
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
      setDocName(`SRS_NexaPlan_v${4}.docx`)
      setUploading(false)
      showToast.success('Document processed', {
        description: '1 new requirement extracted and scored by the Quality Analysis Agent.',
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
    showToast.ai('Quality Analysis Agent scored your new requirement', {
      description: `${id} was scored automatically — review the feedback on the right.`,
    })
  }

  const openCases = selected ? getArbitrationForRequirement(selected.id).filter((c) => c.status === 'Open') : []

  return (
    <div className="space-y-6">
      <PageHeader
        title="SRS Quality Gate"
        breadcrumb={['Planning', 'Requirements', 'SRS Quality']}
        description="Upload your SRS (or add requirements manually) — every requirement is scored against six quality dimensions and must pass before it can be decomposed."
        actions={
          <Badge tone={avgScore >= QUALITY_GATE_THRESHOLD ? 'success' : 'warning'} className="text-sm px-3 py-1">
            Overall quality {avgScore}% · {passingCount}/{requirements.length} passing
          </Badge>
        }
      />

      <Card className="p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary shrink-0">
            <FileText className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground truncate">{docName}</p>
            <p className="text-xs text-muted-foreground">{requirements.length} requirements extracted</p>
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
          <Button
            size="sm"
            variant="outline"
            disabled={uploading}
            onClick={() => fileInputRef.current?.click()}
            className="active:scale-[0.98]"
          >
            <UploadCloud className={`h-3.5 w-3.5 ${uploading ? 'animate-pulse' : ''}`} />
            {uploading ? 'Extracting…' : 'Upload / re-upload SRS'}
          </Button>
          <Button size="sm" onClick={() => setAddOpen(true)} className="active:scale-[0.98]">
            <Plus className="h-3.5 w-3.5" />
            Add requirement manually
          </Button>
        </div>
      </Card>

      <LoadingState loading={uploading} variant="card" className="h-24">
        <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6 items-start">
          <Card className="p-0 overflow-hidden">
            <div className="p-3 border-b border-border">
              <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Requirements</p>
            </div>
            <ul className="divide-y divide-border/60 max-h-[640px] overflow-y-auto column-scroll-contain">
              {requirements.map((r) => (
                <li key={r.id}>
                  <button
                    type="button"
                    onClick={() => selectRequirement(r.id)}
                    className={`w-full text-left p-3 cursor-pointer transition-colors hover:bg-muted/40 ${
                      selectedId === r.id ? 'bg-muted/60' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2 mb-1">
                      <span className="text-xs font-medium text-muted-foreground">{r.id}</span>
                      {r.status === 'Passing' ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                      ) : (
                        <Lock className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                      )}
                    </div>
                    <p className="text-sm text-foreground line-clamp-2 leading-snug">{r.title}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <Progress value={r.overallScore} className="h-1 flex-1" />
                      <span className="text-xs font-medium text-muted-foreground w-9 text-right">{r.overallScore}%</span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          </Card>

          {selected && (
            <div className="space-y-4">
              <Card>
                <div className="flex items-start justify-between gap-3 mb-4 flex-wrap">
                  <div>
                    <p className="text-xs font-semibold text-muted-foreground">{selected.id}</p>
                    <h3 className="text-base font-semibold text-foreground">{selected.title}</h3>
                  </div>
                  <Badge tone={GATE_STATUS_TONE[selected.status]} className="text-sm px-2.5 py-1 shrink-0">
                    {selected.overallScore}% — {selected.status}
                  </Badge>
                </div>

                {selected.status === 'Passing' ? (
                  <div className="flex items-center justify-between gap-3 p-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 mb-4">
                    <div className="flex items-center gap-2 text-sm text-emerald-700 dark:text-emerald-400">
                      <CheckCircle2 className="h-4 w-4" />
                      Eligible for decomposition
                    </div>
                    <Link
                      to="/planning/requirements/decomposition"
                      className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline"
                    >
                      Go to Decomposition <ArrowRight className="h-3 w-3" />
                    </Link>
                  </div>
                ) : (
                  <div className="flex items-center gap-2 p-3 rounded-lg border border-amber-500/20 bg-amber-500/5 mb-4 text-sm text-amber-700 dark:text-amber-400">
                    <Lock className="h-4 w-4 shrink-0" />
                    Blocked from decomposition — needs {QUALITY_GATE_THRESHOLD}% overall to unlock.
                  </div>
                )}

                {openCases.length > 0 && (
                  <div className="p-3 rounded-lg border border-primary/20 bg-primary/5 mb-4">
                    <div className="flex items-center gap-2 mb-1">
                      <Gavel className="h-3.5 w-3.5 text-primary" />
                      <span className="text-xs font-semibold uppercase tracking-wider text-primary">
                        DART arbitration open on this requirement
                      </span>
                    </div>
                    {openCases.map((c) => (
                      <p key={c.id} className="text-xs text-muted-foreground leading-relaxed">
                        <Badge tone="warning" className="mr-1.5">{c.category}</Badge>
                        {c.title} — agents agree {c.confidenceAgreement}% of the time.
                      </p>
                    ))}
                  </div>
                )}

                <div className="space-y-3 mb-4">
                  <div>
                    <label className="text-xs font-medium text-muted-foreground mb-1 block">Title</label>
                    <Input
                      value={currentDraft.title}
                      onChange={(e) => setDraft({ ...currentDraft, title: e.target.value })}
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-muted-foreground mb-1 block">Description</label>
                    <Textarea
                      value={currentDraft.description}
                      onChange={(e) => setDraft({ ...currentDraft, description: e.target.value })}
                      className="min-h-20"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between flex-wrap gap-2">
                  {selected.suggestedRewrite && (
                    <button
                      type="button"
                      className="text-xs text-primary hover:underline cursor-pointer"
                      onClick={() => setDraft({ id: selected.id, title: currentDraft.title, description: selected.suggestedRewrite })}
                    >
                      Use agent-suggested rewrite
                    </button>
                  )}
                  <Button
                    size="sm"
                    className="ml-auto active:scale-[0.98]"
                    disabled={checkingId === selected.id}
                    onClick={() =>
                      runQualityCheck(selected.id, {
                        title: currentDraft.title,
                        description: currentDraft.description,
                      })
                    }
                  >
                    <RefreshCw className={`h-3.5 w-3.5 ${checkingId === selected.id ? 'animate-spin' : ''}`} />
                    {checkingId === selected.id ? 'Checking…' : 'Save & re-run quality check'}
                  </Button>
                </div>
              </Card>

              <Card>
                <h3 className="text-sm font-semibold text-foreground mb-1">Agent feedback — six-dimension breakdown</h3>
                <p className="text-xs text-muted-foreground mb-4">
                  Any dimension below {QUALITY_GATE_THRESHOLD}% is flagged as an issue, with a fix suggestion.
                </p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <QualityRadarChart scores={selected.dimensionScores} height={220} />
                  <div className="space-y-3">
                    {QUALITY_DIMENSIONS.map((dim) => {
                      const score = selected.dimensionScores[dim.key]
                      const isIssue = score < QUALITY_GATE_THRESHOLD
                      return (
                        <div key={dim.key}>
                          <div className="flex items-center justify-between text-xs mb-1">
                            <span className={isIssue ? 'text-amber-600 dark:text-amber-400 font-medium flex items-center gap-1' : 'text-muted-foreground'}>
                              {isIssue && <AlertTriangle className="h-3 w-3" />}
                              {dim.label}
                            </span>
                            <span className="font-medium text-foreground">{score}%</span>
                          </div>
                          <Progress value={score} className="h-1.5" />
                          {isIssue && (
                            <p className="text-xs text-muted-foreground mt-1 leading-snug">{DIMENSION_FIX_HINTS[dim.key]}</p>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>

                {selected.suggestedRewrite && (
                  <div className="mt-4 p-4 rounded-xl border border-primary/20 bg-primary/5">
                    <div className="flex items-center gap-2 mb-1.5">
                      <Sparkles className="h-4 w-4 text-primary" />
                      <span className="text-xs font-semibold uppercase tracking-wider text-primary">
                        Agent-suggested rewrite
                      </span>
                    </div>
                    <p className="text-sm text-foreground leading-relaxed">{selected.suggestedRewrite}</p>
                  </div>
                )}
              </Card>
            </div>
          )}
        </div>
      </LoadingState>

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
              Add & score
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
