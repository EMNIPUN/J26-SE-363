import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  UploadCloud,
  Download,
  FileText,
  Plus,
  RefreshCw,
  AlertTriangle,
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
  Layers,
  FileEdit,
} from 'lucide-react'
import { useTeamPath } from '@/shared/hooks/useTeamPath.js'
import Card from '../../../../../shared/components/Card.jsx'
import Badge from '../../../../../shared/components/Badge.jsx'
import LoadingState from '../../../../../shared/components/LoadingState.jsx'
import AvatarComp from '../../../../../shared/components/Avatar.jsx'
import { Button } from '@/components/ui/button'
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
import HighlightedRequirementText from '../../../components/HighlightedRequirementText.jsx'
import SupervisorConsultationModal from '../../../components/SupervisorConsultationModal.jsx'
import EmptyState from '../../../../../shared/components/EmptyState.jsx'
import { usePlanningData } from '../../../context/usePlanningData.js'
import { srsTemplateUrl } from '../../../services/qualityService.js'
import { useUploadSrs, useAnalyzeQuality, useQualityResults, useRequirementHistory } from '../../../hooks/useQuality.js'
import { mapExtractResult, mapAnalyzeResult, mapPersistedRows, mapQualityResult } from '../../../adapters/quality.js'
import QualityEvidencePanel from '../../../components/QualityEvidencePanel.jsx'
import NewRequirementModal from '../../../components/NewRequirementModal.jsx'
import { useDartCases } from '../../../hooks/useDart.js'
import { mapDartCases, getDartCasesForRequirement } from '../../../adapters/dart.js'
import { COURSE_INFO } from '../../../data/lmsAcademicData.js'
import { GATE_STATUS_TONE, QUALITY_GATE_THRESHOLD, formatRelativeTime } from '../../../utils.js'
import { showToast } from '@/shared/utils/toast.jsx'

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
    key: 'correctness',
    title: 'Correctness',
    standard: 'IEEE 830 § 4.3.1',
    description: 'Every requirement stated must be one the software shall actually meet — it must reflect a genuine, accurate need with no erroneous behaviour.',
    rule: 'Confirm the stated behaviour is the intended one and is technically sound for the goal.',
  },
  {
    key: 'traceability',
    title: 'Traceability',
    standard: 'IEEE 830 § 4.3.8',
    description: 'Each requirement must be uniquely identifiable and linkable backward to its source and forward to design and test artifacts.',
    rule: 'Give each requirement a unique ID and keep it self-contained so it can be traced to a goal.',
  },
]

export default function SRSQuality() {
  const navigate = useNavigate()
  const team = useTeamPath()
  const {
    requirements,
    updateRequirementText,
    applyRequirementResult,
    finalizeRequirement,
    getRequirementHistory,
    loadRequirements,
  } = usePlanningData()
  const uploadMut = useUploadSrs()
  const analyzeMut = useAnalyzeQuality()
  const resultsQuery = useQualityResults()
  const { data: dartData } = useDartCases()
  const allDartCases = mapDartCases(dartData?.cases || [])
  const [selectedId, setSelectedId] = useState(null)
  const [checkingId, setCheckingId] = useState(null)
  const [draft, setDraft] = useState(null)
  const [docName, setDocName] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [historyOpen, setHistoryOpen] = useState(true)
  const [guideOpen, setGuideOpen] = useState(false)
  const [consultOpen, setConsultOpen] = useState(false)
  const [reuploadWarningOpen, setReuploadWarningOpen] = useState(false)
  const [mainTab, setMainTab] = useState('all')
  const fileInputRef = useRef(null)
  const uploading = uploadMut.isPending

  // Hydrate from the DB once (an empty payload simply leaves the upload empty state).
  useEffect(() => {
    const rows = resultsQuery.data?.requirements
    if (rows && rows.length > 0 && requirements.length === 0) {
      loadRequirements(mapPersistedRows(rows))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resultsQuery.data])

  // Falls back to the first requirement until the student picks one.
  const selected = requirements.find((r) => r.id === selectedId) || requirements[0] || null
  const isFinalized = Boolean(selected?.finalized || selected?.decompUnlocked)
  const historyQuery = useRequirementHistory(selected?.id)
  const currentDraft =
    draft && draft.id === selectedId
      ? draft
      : { id: selectedId, title: selected?.title || '', description: selected?.description || '' }

  // Re-check button validation: needs description text and either a text change or stale flag.
  const draftText = currentDraft.description.trim()
  const textChanged = !!selected && draftText !== (selected.description || '').trim()
  const checking = !!selected && checkingId === selected.id
  const canRecheck = !!selected && !isFinalized && !!draftText && (textChanged || selected.stale) && !checking

  const avgScore = requirements.length
    ? Math.round(requirements.reduce((sum, r) => sum + r.overallScore, 0) / requirements.length)
    : 0
  const passingCount = requirements.filter((r) => r.status === 'Passing').length
  const attentionCount = requirements.filter((r) => r.status !== 'Passing').length
  const failingCount = requirements.filter((r) => r.status === 'Failing').length

  function selectRequirement(id) {
    setSelectedId(id)
    setDraft(null)
    setHistoryOpen(true)
  }

  function handleProceedToDecomposition(req) {
    const target = req || selected
    if (!target) return
    finalizeRequirement(target.id)
    showToast.success('Quality gate finalized', {
      description: `${target.id} approved and unlocked for Backlog Decomposition.`,
    })
    navigate(team(`/planning/requirements/decomposition?req=${target.id}`))
  }

  // Intercept upload click: if an SRS document is already present, prompt with warning dialog.
  function handleUploadButtonClick() {
    if (requirements.length > 0 || Boolean(docName)) {
      setReuploadWarningOpen(true)
    } else {
      fileInputRef.current?.click()
    }
  }

  // Re-check: calls the REAL backend and writes ABSOLUTE scores. Only runs on non-empty text.
  async function runQualityCheck(reqId, patch) {
    if (patch) updateRequirementText(reqId, patch)
    const text = (patch?.description ?? selected?.description ?? '').trim()
    if (!text) {
      showToast.error('Nothing to check', { description: 'Add requirement text before running a quality check.' })
      return
    }
    setCheckingId(reqId)
    try {
      const result = await analyzeMut.mutateAsync({
        requirements: [{ id: reqId, text, type: 'functional' }],
        threshold: QUALITY_GATE_THRESHOLD,
      })
      const mapped = mapAnalyzeResult(result, text, {
        title: patch?.title ?? selected?.title,
        priority: selected?.priority,
      })
      if (mapped) {
        applyRequirementResult(reqId, mapped)
        setDraft(null)
        showToast.success('Re-scored by the Quality agent', {
          description: `${reqId}: ${mapped.overallScore}% (${mapped.status}).`,
        })
      }
    } catch (err) {
      showToast.error('Quality check failed', {
        description: err?.message || 'Could not reach the Quality agent.',
      })
    } finally {
      setCheckingId(null)
    }
  }

  async function handleUpload(file) {
    if (!file) return
    try {
      const result = await uploadMut.mutateAsync({ file, threshold: QUALITY_GATE_THRESHOLD })
      const reqs = mapExtractResult(result)
      if (reqs.length === 0) {
        showToast.error('No requirements found', {
          description: 'Use the SRS template and keep requirements in the FR-/NFR- tables.',
        })
        return
      }
      loadRequirements(reqs)
      setDocName(file.name)
      setSelectedId(reqs[0].id)
      const passed = reqs.filter((r) => r.status === 'Passing').length
      showToast.success('SRS analyzed by the Quality agent', {
        description: `${reqs.length} requirement(s) scored · ${passed} passed the ≥${QUALITY_GATE_THRESHOLD} gate.`,
      })
    } catch (err) {
      showToast.error('Upload failed', {
        description: err?.message || 'Could not reach the Quality agent. Is the backend running?',
      })
    }
  }

  const openCases = selected ? getDartCasesForRequirement(allDartCases, selected.id).filter((c) => c.status === 'open') : []
  
  // History: sorted by time descending (latest one at top)
  const persistedHistory = historyQuery.data?.versions || []
  const rawHistory = persistedHistory.length
    ? persistedHistory.map((version) => {
        const mapped = mapQualityResult(
          version,
          version.requirement_text_snapshot,
          { lastChecked: version.assessed_at || version.created_at },
        )
        return {
          version: version.revision_number,
          score: mapped.overallScore,
          status: mapped.status,
          text: version.requirement_text_snapshot,
          timestamp: mapped.lastChecked || version.assessed_at || version.created_at,
        }
      })
    : selected
      ? getRequirementHistory(selected.id)
      : []

  // Ensure history is sorted latest on top
  const history = [...rawHistory].sort((a, b) => {
    const timeA = a.timestamp ? new Date(a.timestamp).getTime() : 0
    const timeB = b.timestamp ? new Date(b.timestamp).getTime() : 0
    if (timeA && timeB && timeA !== timeB) return timeB - timeA
    return (b.version || 0) - (a.version || 0)
  })

  // Delta score trend: latest iteration minus previous iteration
  const scoreTrend = history.length >= 2 ? history[0].score - history[1].score : null

  // Tab definitions for filtering sections in the main column
  const MAIN_TABS = [
    { id: 'all', label: 'All', icon: Layers },
    { id: 'editor', label: 'Specification & Editor', icon: FileEdit },
    { id: 'feedback', label: 'Radar & Agent Evidence', icon: Sparkles },
    { id: 'history', label: 'Revision History', icon: History, count: history.length },
  ]

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

      {/* LMS Project Banner Card with Round Progress Bar */}
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
              Every functional requirement is evaluated against 6 rigorous dimensions. Specifications must satisfy the {QUALITY_GATE_THRESHOLD}% threshold to pass the quality gate and unlock backlog decomposition for sprint planning.
            </p>

            <div className="flex items-center gap-4 flex-wrap pt-1 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5 font-medium text-foreground">
                <FileText className="h-3.5 w-3.5 text-primary" />
                Dossier: <span className="underline decoration-dotted">{docName || 'Active Baseline'}</span>
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
                <circle
                  cx="46"
                  cy="46"
                  r="38"
                  className="stroke-muted"
                  strokeWidth="7"
                  fill="transparent"
                />
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
              <p className="text-sm font-bold text-foreground truncate">{docName || 'No SRS uploaded yet'}</p>
              {docName && <Badge tone="success" className="text-[10px] px-1.5 py-0">Active Baseline</Badge>}
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              {requirements.length === 0
                ? 'Download the template, fill it in, and upload to get real IEEE 830 scores.'
                : `${requirements.length} specifications · ${passingCount} passing · ${attentionCount} need revision${
                    failingCount > 0 ? ` · ${failingCount} blocked` : ''
                  }`}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0 flex-wrap">
          <input
            ref={fileInputRef}
            type="file"
            accept=".docx"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) handleUpload(file)
              e.target.value = ''
            }}
          />
          <Button
            asChild
            size="sm"
            variant="outline"
            className="text-xs cursor-pointer gap-1.5"
          >
            <a href={srsTemplateUrl} download>
              <Download className="h-3.5 w-3.5" />
              Download Template
            </a>
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={uploading}
            onClick={handleUploadButtonClick}
            className="text-xs cursor-pointer gap-1.5"
          >
            <UploadCloud className={`h-3.5 w-3.5 ${uploading ? 'animate-pulse' : ''}`} />
            {uploading ? 'Analyzing SRS…' : 'Upload SRS (.docx)'}
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

      {/* Main 2-Column Studio */}
      <LoadingState loading={uploading || resultsQuery.isLoading} variant="card" className="h-24">
        {requirements.length === 0 ? (
          <EmptyState
            icon={UploadCloud}
            title="Upload your SRS to begin"
            description="Download the template, fill in your functional (FR) and non-functional (NFR) requirements, then upload it. The Quality agent scores each requirement against the six IEEE 830 dimensions and gates it at ≥75."
            actionLabel="Upload SRS (.docx)"
            onAction={handleUploadButtonClick}
          />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-[300px_1fr] xl:grid-cols-[320px_1fr] gap-6 items-start">
            {/* Column 1 — Requirements Directory (Sticky on scroll) */}
            <div className="space-y-3 lg:sticky lg:top-4 self-start">
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
                selectedId={selected?.id}
                onSelect={selectRequirement}
                maxHeight="calc(100vh - 12rem)"
                getItemMeta={(r) => ({
                  percent: r.overallScore,
                  tone: r.status === 'Passing' ? 'success' : r.status === 'Needs Review' ? 'warning' : 'danger',
                  locked: false,
                  finalized: Boolean(r.finalized || r.decompUnlocked),
                })}
              />
            </div>

            {/* Column 2 — Main Column */}
            {selected ? (
              <div className="space-y-4">
                {/* Top Filter Tabs + Top-Right "Go to Next Step" Button */}
                <div className="flex items-center justify-between gap-3 flex-wrap pb-1">
                  {/* Left: Tab Switcher to filter visible sections */}
                  <div className="flex items-center gap-1.5 p-1 bg-muted/40 rounded-xl border border-border/50 flex-wrap">
                    {MAIN_TABS.map((tab) => {
                      const Icon = tab.icon
                      const isActive = mainTab === tab.id
                      return (
                        <button
                          key={tab.id}
                          type="button"
                          onClick={() => setMainTab(tab.id)}
                          className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-all cursor-pointer ${
                            isActive
                              ? 'bg-background text-foreground shadow-xs border border-border/80'
                              : 'text-muted-foreground hover:text-foreground hover:bg-muted/60'
                          }`}
                        >
                          <Icon className={`h-3.5 w-3.5 ${isActive ? 'text-primary' : 'text-muted-foreground'}`} />
                          <span>{tab.label}</span>
                          {tab.count !== undefined && tab.count > 0 && (
                            <span
                              className={`text-[10px] font-bold px-1.5 py-0.2 rounded-full ${
                                isActive ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'
                              }`}
                            >
                              {tab.count}
                            </span>
                          )}
                        </button>
                      )
                    })}
                  </div>

                  {/* Right: Top-Right Corner "Go to Next Step" Button */}
                  <div className="flex items-center gap-2">
                    {isFinalized ? (
                      <Link
                        to={team(`/planning/requirements/decomposition?req=${selected.id}`)}
                        className="inline-flex items-center gap-1.5 text-xs font-bold px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition-all shrink-0 cursor-pointer"
                        title="Requirement quality is finalized. Go to Backlog Decomposition."
                      >
                        <ShieldCheck className="h-3.5 w-3.5" />
                        <span>View in Decomposition</span>
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Link>
                    ) : selected.status === 'Passing' ? (
                      <Button
                        size="sm"
                        onClick={() => handleProceedToDecomposition(selected)}
                        className="text-xs font-bold gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white cursor-pointer shadow-sm transition-all shrink-0"
                        title="Finalize IEEE 830 quality and proceed to Backlog Decomposition."
                      >
                        <span>Proceed to Decomposition</span>
                        <ArrowRight className="h-3.5 w-3.5" />
                      </Button>
                    ) : (
                      <div
                        className="flex items-center gap-1.5"
                        title={`Quality gate locked: requirement must score ≥${QUALITY_GATE_THRESHOLD}% to unlock next step.`}
                      >
                        <Button
                          disabled
                          size="sm"
                          variant="outline"
                          className="text-xs gap-1.5 opacity-60 cursor-not-allowed bg-muted text-muted-foreground"
                        >
                          <Lock className="h-3.5 w-3.5" />
                          Proceed to Decomposition (Locked)
                        </Button>
                      </div>
                    )}
                  </div>
                </div>

                {/* SECTION 1: Specification & Refinement Editor (shown on 'all' or 'editor') */}
                {(mainTab === 'all' || mainTab === 'editor') && (
                  <Card className="p-5">
                    <div className="flex items-start justify-between gap-3 mb-3 flex-wrap">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-primary/10 text-primary">
                          {selected.id}
                        </span>
                        <Badge tone={selected.priority === 'High' ? 'danger' : selected.priority === 'Medium' ? 'warning' : 'neutral'}>
                          {selected.priority} Priority
                        </Badge>
                        {isFinalized ? (
                          <Badge tone="success" className="text-xs font-semibold px-2 py-0.5 gap-1">
                            <ShieldCheck className="h-3 w-3" /> Finalized &amp; Locked
                          </Badge>
                        ) : selected.stale ? (
                          <Badge tone="warning" className="text-[10px] gap-1">
                            <AlertTriangle className="h-3 w-3" /> Edited — re-check needed
                          </Badge>
                        ) : null}
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

                    {/* Finalized Approved Banner */}
                    {isFinalized && (
                      <div className="mb-4 flex items-center justify-between gap-3 p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/25 text-emerald-800 dark:text-emerald-300">
                        <div className="flex items-center gap-2.5 min-w-0">
                          <div className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 shrink-0">
                            <ShieldCheck className="h-4 w-4" />
                          </div>
                          <div className="min-w-0">
                            <p className="text-xs font-bold truncate">Requirement Quality Finalized &amp; Locked</p>
                            <p className="text-[11px] opacity-90 leading-tight">
                              This specification passed IEEE 830 verification and was finalized for Backlog Decomposition. Direct editing is disabled.
                            </p>
                          </div>
                        </div>
                        <Link
                          to={team(`/planning/requirements/decomposition?req=${selected.id}`)}
                          className="text-xs font-semibold underline hover:no-underline shrink-0 flex items-center gap-1 text-emerald-700 dark:text-emerald-300"
                        >
                          View in Decomposition <ArrowRight className="h-3 w-3" />
                        </Link>
                      </div>
                    )}

                    {/* Original Specification Text (Read-Only Highlighted) */}
                    <div className="mb-4">
                      <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground mb-1">
                        IEEE 830 Original Specification Text
                      </p>
                      <HighlightedRequirementText
                        text={selected.description}
                        className="text-xs text-foreground leading-relaxed p-3.5 rounded-xl bg-muted/30 border border-border/80 font-sans"
                      />
                    </div>

                    {/* Single Textarea Input for Refinement */}
                    {isFinalized ? (
                      <div className="space-y-2 mb-3">
                        <div className="flex items-center justify-between">
                          <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
                            <Lock className="h-3 w-3 text-muted-foreground" />
                            Specification Text (Locked — View Only)
                          </p>
                          <span className="text-[10px] text-muted-foreground font-medium">
                            Approved Baseline
                          </span>
                        </div>
                        <Textarea
                          value={selected.description}
                          disabled
                          rows={5}
                          className="text-xs leading-relaxed font-sans bg-muted/40 text-muted-foreground cursor-not-allowed opacity-90 border-border/80 resize-none select-text"
                        />
                      </div>
                    ) : (
                      <div className="space-y-2 mb-3">
                        <div className="flex items-center justify-between">
                          <p className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
                            Student Revision &amp; Refinement Editor
                          </p>
                          <span className="text-[10px] text-muted-foreground">
                            Single specification input (IEEE 830 format)
                          </span>
                        </div>
                        <Textarea
                          value={currentDraft.description}
                          onChange={(e) =>
                            setDraft({
                              id: selected.id,
                              title: currentDraft.title || selected.title,
                              description: e.target.value,
                            })
                          }
                          placeholder="Enter IEEE compliant requirement specification (e.g. 'The system shall...')..."
                          rows={5}
                          className="text-xs leading-relaxed font-sans"
                        />
                      </div>
                    )}

                    {/* Editor Action Toolbar */}
                    {isFinalized ? (
                      <div className="flex items-center justify-between flex-wrap gap-2 pt-2 border-t border-border/60">
                        <span className="text-[11px] text-muted-foreground flex items-center gap-1.5">
                          <Lock className="h-3 w-3" /> Specification locked in read-only mode — quality gate verified.
                        </span>
                        <Link
                          to={team(`/planning/requirements/decomposition?req=${selected.id}`)}
                          className="inline-flex items-center gap-1 text-xs font-semibold text-primary hover:underline"
                        >
                          <span>Proceed to User Story Decomposition</span>
                          <ArrowRight className="h-3 w-3" />
                        </Link>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between flex-wrap gap-2 pt-2 border-t border-border/60">
                        {selected.suggestedRewrite ? (
                          <button
                            type="button"
                            className="text-xs font-semibold text-primary hover:underline cursor-pointer inline-flex items-center gap-1"
                            onClick={() =>
                              setDraft({
                                id: selected.id,
                                title: currentDraft.title || selected.title,
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
                            disabled={!canRecheck}
                            title={
                              !draftText
                                ? 'Add requirement text first'
                                : !textChanged && !selected.stale
                                  ? 'Edit the requirement to run a new check'
                                  : undefined
                            }
                            onClick={() =>
                              runQualityCheck(selected.id, {
                                title: currentDraft.title || selected.title,
                                description: currentDraft.description,
                              })
                            }
                          >
                            <RefreshCw className={`h-3.5 w-3.5 ${checking ? 'animate-spin' : ''}`} />
                            {checking ? 'Re-scoring…' : 'Save & Re-check Quality'}
                          </Button>
                        </div>
                      </div>
                    )}
                  </Card>
                )}

                {/* DART Reasoning Flag Callout (if active) */}
                {openCases.length > 0 && (mainTab === 'all' || mainTab === 'editor' || mainTab === 'feedback') && (
                  <Card className="p-4 border-amber-500/30 bg-amber-500/5 animate-pulse-slow">
                    <div className="flex items-center gap-2 mb-2">
                      <Gavel className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                      <span className="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-300">
                        DART Activated — Low Confidence ({selected ? `${Math.round((selected.confidence ?? 1) * 100)}%` : ''})
                      </span>
                    </div>
                    {openCases.map((c) => (
                      <div key={c.id} className="text-xs text-foreground/90 space-y-2 mb-2 last:mb-0">
                        <div className="flex items-center gap-2">
                          <Badge tone="warning">{c.categoryLabel}</Badge>
                          <span className="text-[10px] text-muted-foreground">{c.caseRef}</span>
                        </div>
                        {c.hypothesis?.rationale && (
                          <p className="text-[11px] text-muted-foreground leading-relaxed">
                            <strong>Diagnosis:</strong> {c.hypothesis.rationale}
                          </p>
                        )}
                        {c.consultation?.question && (
                          <p className="text-[11px] text-blue-700 dark:text-blue-400 italic leading-relaxed">
                            <strong>Targeted question:</strong> "{c.consultation.question}"
                          </p>
                        )}
                        {c.resolution?.actionableFeedback && (
                          <div className="p-2 rounded-md bg-primary/5 border border-primary/20">
                            <p className="text-xs text-foreground leading-snug">
                              <strong>Feedback:</strong> {c.resolution.actionableFeedback}
                            </p>
                            <p className="text-[10px] text-muted-foreground mt-0.5">
                              Confidence agreement: {c.resolution.confidenceAgreement}%
                            </p>
                          </div>
                        )}
                      </div>
                    ))}
                  </Card>
                )}

                {/* SECTION 2: Combined Radar Studio & Quality Evidence (shown on 'all' or 'feedback') */}
                {(mainTab === 'all' || mainTab === 'feedback') && (
                  <QualityEvidencePanel
                    requirement={selected}
                    onApplyRewrite={(rewrite) => {
                      setDraft({
                        id: selected.id,
                        title: currentDraft.title || selected.title,
                        description: rewrite,
                      })
                      setMainTab('editor')
                    }}
                    onConsult={() => setConsultOpen(true)}
                    defaultOpen={true}
                  />
                )}

                {/* SECTION 3: Version History (shown on 'all' or 'history') */}
                {(mainTab === 'all' || mainTab === 'history') && (
                  <Card className="p-0 overflow-hidden">
                    <button
                      type="button"
                      onClick={() => setHistoryOpen((v) => !v)}
                      className="w-full flex items-center justify-between p-3.5 cursor-pointer hover:bg-muted/30 transition-colors"
                    >
                      <span className="flex items-center gap-2 text-xs font-bold text-foreground">
                        <History className="h-3.5 w-3.5 text-primary" />
                        Specification Revision History ({history.length} iteration{history.length !== 1 ? 's' : ''})
                        <span className="text-[10px] text-muted-foreground font-normal">(sorted latest on top)</span>
                      </span>
                      <span className="text-xs text-primary font-medium">{historyOpen || mainTab === 'history' ? 'Collapse' : 'Expand'}</span>
                    </button>
                    {(historyOpen || mainTab === 'history') && (
                      <div className="px-3.5 pb-3.5 space-y-2 border-t border-border/60 bg-muted/10 animate-fade-rise">
                        {history.length === 0 ? (
                          <p className="text-xs text-muted-foreground py-3 text-center">No revision history recorded yet.</p>
                        ) : (
                          history.map((h, index) => (
                            <div
                              key={h.version || index}
                              className={`text-xs p-3 rounded-lg bg-card border ${
                                index === 0 ? 'border-primary/40 shadow-xs' : 'border-border/60'
                              }`}
                            >
                              <div className="flex items-center gap-3">
                                <span className="h-5 w-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-[10px] font-bold shrink-0">
                                  v{h.version}
                                </span>
                                <span className="font-bold text-foreground">{h.score}%</span>
                                <Badge tone={GATE_STATUS_TONE[h.status]} className="text-[10px] px-1.5 py-0">
                                  {h.status}
                                </Badge>
                                {index === 0 && (
                                  <Badge tone="success" className="text-[9px] px-1.5 py-0 font-bold">
                                    Latest
                                  </Badge>
                                )}
                                <span className="text-muted-foreground text-[11px] ml-auto">
                                  {h.timestamp ? formatRelativeTime(h.timestamp) : 'Baseline'}
                                </span>
                              </div>
                              {h.text && (
                                <p className="mt-2 text-[11px] leading-relaxed text-muted-foreground bg-muted/20 p-2 rounded border border-border/40 font-sans">
                                  {h.text}
                                </p>
                              )}
                            </div>
                          ))
                        )}
                      </div>
                    )}
                  </Card>
                )}
              </div>
            ) : (
              <Card className="p-8 text-center text-xs text-muted-foreground">
                Select a requirement from the catalog on the left to review its IEEE 830 quality profile.
              </Card>
            )}
          </div>
        )}
      </LoadingState>

      <DartButton context="quality" />

      {/* Re-upload SRS Warning Dialog */}
      <Dialog open={reuploadWarningOpen} onOpenChange={setReuploadWarningOpen}>
        <DialogContent className="sm:max-w-[480px]">
          <DialogHeader>
            <div className="flex items-center gap-2 mb-1">
              <span className="p-1.5 rounded-lg bg-amber-500/15 text-amber-600 dark:text-amber-400">
                <AlertTriangle className="h-4 w-4" />
              </span>
              <DialogTitle className="text-base font-bold">Replace Existing SRS Baseline?</DialogTitle>
            </div>
            <DialogDescription className="text-xs text-muted-foreground leading-relaxed pt-1">
              An SRS document is already active{' '}
              {docName ? (
                <strong className="text-foreground">({docName})</strong>
              ) : (
                <strong className="text-foreground">({requirements.length} requirements loaded)</strong>
              )}
              . Uploading a new file will overwrite your existing requirements catalog, manual revisions, and evaluation scores.
            </DialogDescription>
          </DialogHeader>

          <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/25 text-xs space-y-1">
            <p className="font-semibold text-amber-900 dark:text-amber-200">
              Warning: Session Progress Replacement
            </p>
            <p className="text-[11px] text-amber-800 dark:text-amber-300 leading-relaxed">
              Any revisions or score improvements you achieved in this session will be replaced by the extracted specifications from the new file.
            </p>
          </div>

          <DialogFooter className="pt-2 gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setReuploadWarningOpen(false)}
              className="text-xs cursor-pointer"
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => {
                setReuploadWarningOpen(false)
                fileInputRef.current?.click()
              }}
              className="text-xs cursor-pointer gap-1.5"
            >
              <UploadCloud className="h-3.5 w-3.5" />
              Proceed &amp; Upload New File
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add Single Requirement Modal (Category Enum & Database Persistence) */}
      <NewRequirementModal
        open={addOpen}
        onOpenChange={setAddOpen}
        existingRequirements={requirements}
        onCreated={(created) => {
          setSelectedId(created.id)
        }}
      />

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
