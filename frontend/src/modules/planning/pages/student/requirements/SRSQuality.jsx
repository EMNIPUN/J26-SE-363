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
  GraduationCap,
  BookOpen,
  Sparkles,
  UserCheck,
  ShieldCheck,
  Check,
} from 'lucide-react'
import Card from '../../../../../shared/components/Card.jsx'
import Badge from '../../../../../shared/components/Badge.jsx'
import LoadingState from '../../../../../shared/components/LoadingState.jsx'
import AvatarComp from '../../../../../shared/components/Avatar.jsx'
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
import SupervisorConsultationModal from '../../../components/SupervisorConsultationModal.jsx'
import { usePlanningData } from '../../../context/usePlanningData.js'
import { QUALITY_DIMENSIONS, getArbitrationForRequirement } from '../../../data/mockData.js'
import { COURSE_INFO } from '../../../data/lmsAcademicData.js'
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

const IEEE_STANDARDS_INFO = [
  {
    key: 'clarity',
    title: 'Clarity (Unambiguity)',
    standard: 'IEEE 830 § 4.3.2',
    description: 'Each requirement must have only one semantic interpretation. Avoid fuzzy adjectives such as "user-friendly", "fast", or "flexible".',
    rule: 'Use precise operational language with verifiable verbs (The system shall [action] when [condition]).',
  },
  {
    key: 'completeness',
    title: 'Completeness',
    standard: 'IEEE 830 § 4.3.3',
    description: 'All significant requirements relating to functionality, performance, design constraints, and external interfaces must be specified.',
    rule: 'Specify all inputs, valid ranges, output states, and standard exception handling behaviors.',
  },
  {
    key: 'consistency',
    title: 'Consistency (Atomicity)',
    standard: 'IEEE 830 § 4.3.4',
    description: 'Requirements cannot contradict other functional specifications or architectural constraints within the SRS.',
    rule: 'Each requirement must specify a single atomic obligation. Avoid compound requirements joined by "while also" or "and simultaneously".',
  },
  {
    key: 'testability',
    title: 'Testability (Verifiability)',
    standard: 'IEEE 830 § 4.3.5',
    description: 'A cost-effective automated or manual test case must be able to prove whether the delivered software meets the specification.',
    rule: 'Define exact numeric criteria: latency thresholds, throughput numbers, or concrete boolean conditions.',
  },
  {
    key: 'feasibility',
    title: 'Feasibility',
    standard: 'IEEE 830 § 4.3.6',
    description: 'The requirement must be technically achievable within project scope, chosen tech stack, and semester timeline constraints.',
    rule: 'Assess dependencies on third-party APIs, hardware requirements, and model inference constraints.',
  },
  {
    key: 'scope',
    title: 'Scope Alignment',
    standard: 'Capstone SE4010 Rubric LO-1',
    description: 'The obligation must fall strictly within the group research domain and allocated student specialization boundaries.',
    rule: 'Ensure traceability to approved project charter and supervisor-approved research themes.',
  },
]

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
  const [newReq, setNewReq] = useState({ title: '', description: '', priority: 'High' })
  const [historyOpen, setHistoryOpen] = useState(false)
  const [guideOpen, setGuideOpen] = useState(false)
  const [consultOpen, setConsultOpen] = useState(false)
  const fileInputRef = useRef(null)

  const selected = requirements.find((r) => r.id === selectedId) || null
  const currentDraft =
    draft && draft.id === selectedId
      ? draft
      : { id: selectedId, title: selected?.title || '', description: selected?.description || '' }

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
      showToast.success('AI Analysis Complete', {
        description: `${reqId} re-evaluated across all 6 IEEE dimensions.`,
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
        description:
          'The system shall generate a downloadable PDF snapshot of all requirements and their quality scores within 3 seconds of request.',
        priority: 'Medium',
        status: 'Needs Review',
        overallScore: 68,
        dimensionScores: { clarity: 75, completeness: 65, consistency: 70, testability: 64, feasibility: 76, scope: 68 },
        suggestedRewrite:
          'Specify explicit document layout parameters and error handling if rendering pipeline exceeds timeout.',
        lastChecked: new Date().toISOString(),
      })
      setDocName(`SRS_NexaPlan_v4.docx`)
      setUploading(false)
      showToast.success('Document Processed & Indexed', {
        description: '1 new specification extracted and evaluated by the automated Quality Gatekeeper.',
      })
    }, 1400)
  }

  function submitManualRequirement() {
    if (!newReq.title.trim()) return
    const id = `REQ-1${manualIdCounter++}`
    const desc = newReq.description || newReq.title
    const wordCount = desc.trim().split(/\s+/).length

    const clarity = Math.min(95, Math.max(60, 68 + (wordCount > 10 ? 12 : 0)))
    const completeness = Math.min(95, Math.max(55, 62 + (desc.toLowerCase().includes('shall') ? 18 : 5)))
    const consistency = 80
    const testability = Math.min(95, Math.max(50, 65 + (desc.toLowerCase().includes('within') ? 20 : 5)))
    const feasibility = 88
    const scope = 85

    const overallScore = Math.round((clarity + completeness + consistency + testability + feasibility + scope) / 6)
    const status = overallScore >= 70 ? 'Passing' : overallScore >= 50 ? 'Needs Review' : 'Failing'

    addRequirement({
      id,
      title: newReq.title.trim(),
      description: desc.trim(),
      priority: newReq.priority,
      status,
      overallScore,
      dimensionScores: {
        clarity,
        completeness,
        consistency,
        testability,
        feasibility,
        scope,
      },
      suggestedRewrite: status !== 'Passing' ? 'Add quantifiable acceptance limits to fulfill IEEE 830 testability.' : null,
      lastChecked: new Date().toISOString(),
    })
    setNewReq({ title: '', description: '', priority: 'High' })
    setAddOpen(false)
    setSelectedId(id)
    showToast.success('Requirement added and scored', {
      description: `${id} scored at ${overallScore}% (${status}). Review dimension breakdown on the right.`,
    })
  }

  const openCases = selected ? getArbitrationForRequirement(selected.id).filter((c) => c.status === 'Open') : []
  const history = selected ? getRequirementHistory(selected.id) : []
  const scoreTrend = history.length >= 2 ? history[history.length - 1].score - history[history.length - 2].score : null

  return (
    <div className="space-y-6 pb-12">
      {/* Top Academic Breadcrumb Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-border">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <GraduationCap className="h-3.5 w-3.5 text-primary" />
            <span>{COURSE_INFO.courseCode} · {COURSE_INFO.courseName}</span>
            <span className="text-border">/</span>
            <span className="text-foreground">Milestone M2</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            SRS Quality Gate &amp; IEEE 830 Verification
            <Badge
              tone={avgScore >= QUALITY_GATE_THRESHOLD ? 'success' : 'warning'}
              className="text-xs font-medium"
            >
              Gate: &gt;= {QUALITY_GATE_THRESHOLD}% Pass
            </Badge>
          </h1>
        </div>

        {/* Action Toolbar */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setGuideOpen(true)}
            className="text-xs cursor-pointer gap-1.5"
          >
            <BookOpen className="h-3.5 w-3.5 text-primary" /> IEEE Rubric Guide
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setConsultOpen(true)}
            className="text-xs cursor-pointer gap-1.5"
          >
            <UserCheck className="h-3.5 w-3.5 text-primary" /> Supervisor Advisory
          </Button>
          <Button
            size="sm"
            onClick={() => setAddOpen(true)}
            className="text-xs cursor-pointer gap-1.5"
          >
            <Plus className="h-3.5 w-3.5" /> Add Requirement
          </Button>
        </div>
      </div>

      {/* LMS Project Banner Card with Round Progress Bar (no left border) */}
      <Card className="p-5 relative overflow-hidden bg-card/90">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-5">
          <div className="space-y-2 min-w-0 max-w-2xl">
            <div className="flex items-center gap-2 flex-wrap text-xs text-muted-foreground">
              <span className="px-2 py-0.5 rounded-full bg-primary/10 text-primary font-bold">
                {COURSE_INFO.group.number} ({COURSE_INFO.group.code})
              </span>
              <span>·</span>
              <span className="font-semibold text-foreground">{COURSE_INFO.department}</span>
              <span>·</span>
              <span>Standard: <strong className="text-foreground">IEEE 830 / ISO 29148</strong></span>
            </div>

            <h2 className="text-lg sm:text-xl font-semibold text-foreground tracking-tight">
              Automated Requirements Quality Gatekeeper
            </h2>

            <p className="text-xs text-muted-foreground leading-relaxed">
              Every functional requirement is evaluated against 6 rigorous dimensions. Specifications must satisfy the 70% threshold to pass the quality gate and unlock backlog decomposition for sprint planning.
            </p>

            <div className="flex items-center gap-4 flex-wrap pt-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5 font-medium text-foreground">
                <FileText className="h-3.5 w-3.5 text-primary" />
                Dossier: <span className="underline decoration-dotted">{docName}</span>
              </span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span className="flex items-center gap-1.5">
                <AvatarComp name={COURSE_INFO.supervisor.name} size={20} className="ring-1 ring-border" />
                Supervisor: {COURSE_INFO.supervisor.name}
              </span>
              <span className="h-1 w-1 rounded-full bg-border" />
              <span className="flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                {passingCount} of {requirements.length} Requirements Passing
              </span>
            </div>
          </div>

          {/* Round Progress Bar with Percentage in Middle */}
          <div className="flex flex-col items-center justify-center shrink-0 self-center sm:self-center px-3 py-1">
            <div className="relative flex items-center justify-center" style={{ width: 92, height: 92 }}>
              <svg className="w-full h-full -rotate-90 transform" viewBox="0 0 92 92">
                {/* Background track */}
                <circle
                  cx="46"
                  cy="46"
                  r="38"
                  className="stroke-muted"
                  strokeWidth="7"
                  fill="transparent"
                />
                {/* Progress ring */}
                <circle
                  cx="46"
                  cy="46"
                  r="38"
                  className={`transition-all duration-700 ease-out ${
                    avgScore >= QUALITY_GATE_THRESHOLD ? 'stroke-emerald-500' : 'stroke-amber-500'
                  }`}
                  strokeWidth={7}
                  strokeDasharray={2 * Math.PI * 38}
                  strokeDashoffset={(2 * Math.PI * 38) * (1 - avgScore / 100)}
                  strokeLinecap="round"
                  fill="transparent"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-xl font-bold tracking-tight text-foreground">{avgScore}%</span>
              </div>
            </div>
            <span className="text-xs font-semibold text-muted-foreground mt-1.5">Quality Gate Pass</span>
          </div>
        </div>
      </Card>

      {/* 4-Stage Workflow Stepper */}
      <WorkflowStepper current="quality" />

      {/* Document Ingestion & Quick Action Bar */}
      <Card className="p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-muted/20 border-border">
        <div className="flex items-center gap-3 min-w-0">
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center text-primary shrink-0">
            <FileText className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <p className="text-sm font-bold text-foreground truncate">{docName}</p>
              <Badge tone="success" className="text-[10px] px-1.5 py-0">Active Baseline</Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              {requirements.length} specifications extracted · {passingCount} passing · {attentionCount} need revision
              {failingCount > 0 ? ` · ${failingCount} blocked` : ''}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0 flex-wrap">
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
            className="text-xs cursor-pointer gap-1.5"
          >
            <UploadCloud className={`h-3.5 w-3.5 ${uploading ? 'animate-pulse' : ''}`} />
            {uploading ? 'Extracting SRS…' : 'Upload SRS (.docx / .pdf)'}
          </Button>
          <Button
            size="sm"
            onClick={() => setAddOpen(true)}
            className="text-xs cursor-pointer gap-1.5"
          >
            <Plus className="h-3.5 w-3.5" /> Add Requirement
          </Button>
        </div>
      </Card>

      {/* Main 3-Column Studio */}
      <LoadingState loading={uploading} variant="card" className="h-24">
        <div className="grid grid-cols-1 xl:grid-cols-[290px_1fr_310px] gap-5 items-start">
          {/* Column 1 — Requirements Directory */}
          <div className="space-y-3">
            <div className="flex items-center justify-between px-1">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Requirements Catalog
              </span>
              <span className="text-xs text-muted-foreground font-medium">
                {passingCount}/{requirements.length} Ready
              </span>
            </div>

            <RequirementListPanel
              requirements={requirements}
              selectedId={selectedId}
              onSelect={selectRequirement}
              maxHeight={620}
              getItemMeta={(r) => ({
                percent: r.overallScore,
                tone: r.status === 'Passing' ? 'success' : r.status === 'Needs Review' ? 'warning' : 'danger',
              })}
            />
          </div>

          {/* Column 2 — Requirement Revision Studio */}
          {selected ? (
            <div className="space-y-4">
              <Card className="p-5">
                <div className="flex items-start justify-between gap-3 mb-3 flex-wrap">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-primary/10 text-primary">
                      {selected.id}
                    </span>
                    <Badge tone={selected.priority === 'High' ? 'danger' : selected.priority === 'Medium' ? 'warning' : 'neutral'}>
                      {selected.priority} Priority
                    </Badge>
                  </div>

                  <div className="flex items-center gap-2 shrink-0">
                    {scoreTrend !== null && scoreTrend !== 0 && (
                      <span
                        className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                          scoreTrend > 0
                            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                            : 'bg-destructive/10 text-destructive'
                        }`}
                      >
                        {scoreTrend > 0 ? '↑ +' : '↓ '}{scoreTrend}% Delta
                      </span>
                    )}
                    <Badge tone={GATE_STATUS_TONE[selected.status]} className="text-xs font-semibold px-2.5 py-0.5">
                      {selected.overallScore}% · {selected.status}
                    </Badge>
                  </div>
                </div>

                <div className="mb-4">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-1">
                    IEEE 830 Original Specification Text
                  </p>
                  <HighlightedRequirementText
                    text={selected.description}
                    className="text-xs text-foreground leading-relaxed p-3.5 rounded-xl bg-muted/30 border border-border/80 font-sans"
                  />
                </div>

                <div className="space-y-2 mb-3">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-1">
                    Student Revision &amp; Refinement Editor
                  </p>
                  <Input
                    value={currentDraft.title}
                    onChange={(e) => setDraft({ ...currentDraft, title: e.target.value })}
                    placeholder="Requirement short title..."
                    className="text-xs font-semibold h-9"
                  />
                  <Textarea
                    value={currentDraft.description}
                    onChange={(e) => setDraft({ ...currentDraft, description: e.target.value })}
                    placeholder="Enter IEEE compliant requirement specification..."
                    rows={4}
                    className="text-xs leading-relaxed"
                  />
                </div>

                <div className="flex items-center justify-between flex-wrap gap-2 pt-2 border-t border-border/60">
                  {selected.suggestedRewrite ? (
                    <button
                      type="button"
                      className="text-xs font-semibold text-primary hover:underline cursor-pointer inline-flex items-center gap-1"
                      onClick={() =>
                        setDraft({
                          id: selected.id,
                          title: currentDraft.title,
                          description: selected.suggestedRewrite,
                        })
                      }
                    >
                      <Sparkles className="h-3.5 w-3.5 text-primary" /> Apply AI Rewrite Suggestion
                    </button>
                  ) : (
                    <span className="text-[11px] text-muted-foreground">Editor in sync with baseline</span>
                  )}

                  <div className="flex items-center gap-2 ml-auto">
                    {draft && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setDraft(null)}
                        className="text-xs cursor-pointer"
                      >
                        Reset
                      </Button>
                    )}
                    <Button
                      size="sm"
                      className="text-xs cursor-pointer gap-1.5"
                      disabled={checkingId === selected.id}
                      onClick={() =>
                        runQualityCheck(selected.id, {
                          title: currentDraft.title,
                          description: currentDraft.description,
                        })
                      }
                    >
                      <RefreshCw className={`h-3.5 w-3.5 ${checkingId === selected.id ? 'animate-spin' : ''}`} />
                      {checkingId === selected.id ? 'Evaluating Multi-Agent Gate...' : 'Save & Run Quality Check'}
                    </Button>
                  </div>
                </div>
              </Card>

              {/* Requirement-Level Quality Gate Verdict Card */}
              <Card
                className={`p-4 border transition-all ${
                  selected.status === 'Passing'
                    ? 'border-emerald-500/30 bg-emerald-500/5'
                    : 'border-amber-500/30 bg-amber-500/5'
                }`}
              >
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <div className="flex items-center gap-2.5">
                    {selected.status === 'Passing' ? (
                      <div className="h-8 w-8 rounded-full bg-emerald-500/15 flex items-center justify-center text-emerald-600 dark:text-emerald-400 shrink-0">
                        <CheckCircle2 className="h-5 w-5" />
                      </div>
                    ) : (
                      <div className="h-8 w-8 rounded-full bg-amber-500/15 flex items-center justify-center text-amber-600 dark:text-amber-400 shrink-0">
                        <Lock className="h-4 w-4" />
                      </div>
                    )}
                    <div>
                      <p className="text-sm font-bold text-foreground">
                        Quality Gate — {selected.status === 'Passing' ? 'PASSED (UNLOCKED)' : 'BLOCKED (NEEDS REVISION)'}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {selected.status === 'Passing'
                          ? `All required IEEE dimensions satisfy the ${QUALITY_GATE_THRESHOLD}% gate threshold.`
                          : `${
                              QUALITY_DIMENSIONS.filter((d) => (selected.dimensionScores?.[d.key] ?? 0) < QUALITY_GATE_THRESHOLD).length
                            } dimension(s) score below ${QUALITY_GATE_THRESHOLD}%. Refine specification text to unlock decomposition.`}
                      </p>
                    </div>
                  </div>

                  {selected.status === 'Passing' ? (
                    <Link
                      to="/planning/requirements/decomposition"
                      className="inline-flex items-center gap-1.5 text-xs font-bold text-primary hover:underline shrink-0 bg-primary/10 px-3 py-1.5 rounded-lg"
                    >
                      Proceed to Decomposition <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setConsultOpen(true)}
                      className="inline-flex items-center gap-1 text-xs font-semibold text-amber-700 dark:text-amber-300 hover:underline shrink-0 cursor-pointer"
                    >
                      Consult Supervisor <ArrowRight className="h-3 w-3" />
                    </button>
                  )}
                </div>
              </Card>

              {/* DART Reasoning Flag Callout */}
              {openCases.length > 0 && (
                <Card className="p-4 border-amber-500/30 bg-amber-500/5">
                  <div className="flex items-center gap-2 mb-1.5">
                    <Gavel className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                    <span className="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-300">
                      DART Diagnostic Conflict Flag
                    </span>
                  </div>
                  {openCases.map((c) => (
                    <div key={c.id} className="text-xs text-foreground/90 space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge tone="warning">{c.category}</Badge>
                        <span className="font-semibold text-foreground">{c.title}</span>
                      </div>
                      <p className="text-muted-foreground text-[11px] leading-relaxed">
                        Reasoning agent consensus: <strong>{c.confidenceAgreement}%</strong> agreement. {c.resolution}
                      </p>
                    </div>
                  ))}
                </Card>
              )}

              {/* Version History Drawer */}
              <Card className="p-0 overflow-hidden">
                <button
                  type="button"
                  onClick={() => setHistoryOpen((v) => !v)}
                  className="w-full flex items-center justify-between p-3.5 cursor-pointer hover:bg-muted/30 transition-colors"
                >
                  <span className="flex items-center gap-2 text-xs font-bold text-foreground">
                    <History className="h-3.5 w-3.5 text-primary" />
                    Specification Revision History ({history.length} iterations)
                  </span>
                  <span className="text-xs text-primary font-medium">{historyOpen ? 'Collapse' : 'Expand'}</span>
                </button>
                {historyOpen && (
                  <div className="px-3.5 pb-3.5 space-y-2 border-t border-border/60 bg-muted/10 animate-fade-rise">
                    {history.map((h) => (
                      <div key={h.version} className="flex items-center gap-3 text-xs p-2 rounded-lg bg-card border border-border/60">
                        <span className="h-5 w-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[10px] font-bold shrink-0">
                          v{h.version}
                        </span>
                        <span className="font-bold text-foreground">{h.score}%</span>
                        <Badge tone={GATE_STATUS_TONE[h.status]} className="text-[10px] px-1.5 py-0">{h.status}</Badge>
                        <span className="text-muted-foreground text-[11px] ml-auto">{formatRelativeTime(h.timestamp)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          ) : (
            <Card className="p-8 text-center text-xs text-muted-foreground">
              Select a requirement from the catalog on the left to review its IEEE 830 quality profile.
            </Card>
          )}

          {/* Column 3 — Multi-Agent AI Reasoning Studio */}
          {selected && (
            <div className="space-y-4">
              <Card className="p-4">
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-border">
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                      IEEE 830 Radar Studio
                    </h3>
                    <p className="text-[11px] text-muted-foreground">Six-dimension reasoning profile</p>
                  </div>
                  <Badge tone={selected.status === 'Passing' ? 'success' : 'warning'}>
                    {selected.status}
                  </Badge>
                </div>

                <QualityRadarChart scores={selected.dimensionScores} height={170} />

                <div className="space-y-2.5 mt-3">
                  {QUALITY_DIMENSIONS.map((dim) => {
                    const score = selected.dimensionScores?.[dim.key] ?? 0
                    const tier = dimTier(score)
                    const info = DIMENSION_ISSUE[dim.key]

                    return (
                      <div
                        key={dim.key}
                        className={`p-2.5 rounded-xl border transition-all ${
                          tier === 'pass'
                            ? 'border-border/60 bg-card'
                            : tier === 'warn'
                              ? 'border-amber-500/25 bg-amber-500/5'
                              : 'border-destructive/25 bg-destructive/5'
                        }`}
                      >
                        <div className="flex items-center justify-between text-xs mb-1">
                          <span className="flex items-center gap-1.5 font-bold text-foreground text-[11px]">
                            {DIM_ICON[tier]}
                            {dim.label}
                          </span>
                          <span className="font-bold text-foreground text-xs">{score}%</span>
                        </div>

                        {tier !== 'pass' && info && (
                          <div className="mt-1 pt-1 border-t border-border/40 space-y-1 text-[11px] text-muted-foreground">
                            <p className="text-foreground font-medium">
                              <span className="text-destructive font-semibold">Issue: </span>
                              {info.issue}
                            </p>
                            <p>
                              <span className="font-semibold text-foreground">Remedy: </span>
                              {info.suggestion}
                            </p>
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>

                <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-xs">
                  <span className="text-[11px] text-muted-foreground">Unsure how to fix?</span>
                  <button
                    type="button"
                    onClick={() => setConsultOpen(true)}
                    className="text-xs font-semibold text-primary hover:underline inline-flex items-center gap-1 cursor-pointer"
                  >
                    <UserCheck className="h-3 w-3" /> Book Advisory
                  </button>
                </div>
              </Card>
            </div>
          )}
        </div>
      </LoadingState>

      <DartButton context="quality" />

      {/* Manual Add Requirement Dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <div className="flex items-center gap-2 mb-1">
              <span className="p-1 rounded bg-primary/10 text-primary">
                <Plus className="h-4 w-4" />
              </span>
              <DialogTitle className="text-lg font-bold">Add Requirement to SRS Baseline</DialogTitle>
            </div>
            <DialogDescription className="text-xs">
              Directly submit a new specification. The automated Quality Gatekeeper will score all 6 IEEE dimensions immediately.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3.5 text-xs">
            <div>
              <label className="font-semibold text-foreground block mb-1">Requirement Title</label>
              <Input
                value={newReq.title}
                onChange={(e) => setNewReq((f) => ({ ...f, title: e.target.value }))}
                placeholder="e.g. Student can view automated burndown charts"
                className="text-xs h-9"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="font-semibold text-foreground block mb-1">Priority</label>
                <select
                  value={newReq.priority}
                  onChange={(e) => setNewReq((f) => ({ ...f, priority: e.target.value }))}
                  className="w-full h-9 rounded-md border border-input bg-transparent px-3 py-1 text-xs"
                >
                  <option value="High">High (Must Have)</option>
                  <option value="Medium">Medium (Should Have)</option>
                  <option value="Low">Low (Nice to Have)</option>
                </select>
              </div>
              <div>
                <label className="font-semibold text-foreground block mb-1">Standard</label>
                <Input value="IEEE 830 / ISO 29148" disabled className="text-xs h-9 bg-muted/40" />
              </div>
            </div>

            <div>
              <label className="font-semibold text-foreground block mb-1">
                Specification Description (<span className="font-mono text-primary font-normal">The system shall...</span>)
              </label>
              <Textarea
                value={newReq.description}
                onChange={(e) => setNewReq((f) => ({ ...f, description: e.target.value }))}
                placeholder="The system shall calculate sprint burndown points every 24 hours and render an interactive curve..."
                rows={4}
                className="text-xs leading-relaxed"
              />
            </div>
          </div>

          <DialogFooter className="pt-2 gap-2">
            <Button variant="outline" size="sm" onClick={() => setAddOpen(false)} className="text-xs cursor-pointer">
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={submitManualRequirement}
              disabled={!newReq.title.trim()}
              className="text-xs cursor-pointer gap-1.5"
            >
              <Plus className="h-3.5 w-3.5" /> Submit &amp; Score
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* IEEE 830 Rubric & Dimension Guide Dialog */}
      <Dialog open={guideOpen} onOpenChange={setGuideOpen}>
        <DialogContent className="sm:max-w-[620px] max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <div className="flex items-center gap-2 mb-1">
              <span className="p-1 rounded bg-primary/10 text-primary">
                <BookOpen className="h-4 w-4" />
              </span>
              <DialogTitle className="text-lg font-bold">IEEE 830 Quality Gate Evaluation Rubric</DialogTitle>
            </div>
            <DialogDescription className="text-xs">
              Academic guidelines used by the automated Quality Gatekeeper to assess software specifications.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3.5 text-xs">
            {IEEE_STANDARDS_INFO.map((std) => (
              <div key={std.key} className="p-3.5 rounded-xl border border-border bg-card space-y-1.5">
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-foreground text-xs flex items-center gap-1.5">
                    <Check className="h-3.5 w-3.5 text-primary" /> {std.title}
                  </h4>
                  <Badge tone="neutral" className="text-[10px] px-1.5 py-0">{std.standard}</Badge>
                </div>
                <p className="text-muted-foreground text-[11px] leading-relaxed">{std.description}</p>
                <div className="p-2 rounded bg-muted/40 text-[11px] text-foreground font-medium border border-border/50">
                  <span className="text-primary font-bold">Rule: </span>{std.rule}
                </div>
              </div>
            ))}
          </div>

          <DialogFooter className="pt-2">
            <Button size="sm" onClick={() => setGuideOpen(false)} className="text-xs cursor-pointer">
              Understood
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Supervisor Consultation Modal */}
      <SupervisorConsultationModal
        open={consultOpen}
        onOpenChange={setConsultOpen}
        requirements={requirements}
      />
    </div>
  )
}
