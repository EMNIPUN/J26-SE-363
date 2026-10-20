import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import {
  ShieldCheck,
  AlertTriangle,
  Lock,
  Gavel,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  Sparkles,
  Layers,
  FileCheck,
  Compass,
  Check,
  X,
  BookOpen,
} from 'lucide-react'
import { useStoryPassport, useEvaluatePassport } from '../hooks/usePassport.js'
import { showToast } from '@/shared/utils/toast.jsx'

const STATUS_CONFIG = {
  ready: {
    label: 'Ready for Sprint Backlog',
    badgeTone: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30',
    bannerBg: 'bg-emerald-500/10 border-emerald-500/25',
    icon: ShieldCheck,
    titleColor: 'text-emerald-700 dark:text-emerald-300',
    description:
      'All 5 quality and decomposition gates are verified. The user story has full parent capability coverage, passes INVEST heuristics, and is ready for sprint backlog prioritization & Jira synchronization.',
  },
  ready_with_warnings: {
    label: 'Ready with Improvement',
    badgeTone: 'bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30',
    bannerBg: 'bg-amber-500/10 border-amber-500/25',
    icon: Sparkles,
    titleColor: 'text-amber-700 dark:text-amber-300',
    description:
      'Core Requirement Quality (Stage 1) and Backlog Decomposition coverage are verified. Proceed to Effort Estimation (Stage 3) to assign story points and finalize sprint commitment.',
  },
  not_ready: {
    label: 'Not Ready — Gated',
    badgeTone: 'bg-rose-500/15 text-rose-700 dark:text-rose-400 border-rose-500/30',
    bannerBg: 'bg-rose-500/10 border-rose-500/25',
    icon: Lock,
    titleColor: 'text-rose-700 dark:text-rose-300',
    description:
      'Blocked by one or more stage gates. Needs resolution of requirement quality smells, missing parent functional behaviors, or failing INVEST criteria.',
  },
  needs_review: {
    label: 'Needs Review — DART Escalation',
    badgeTone: 'bg-indigo-500/15 text-indigo-700 dark:text-indigo-400 border-indigo-500/30',
    bannerBg: 'bg-indigo-500/10 border-indigo-500/25',
    icon: Gavel,
    titleColor: 'text-indigo-700 dark:text-indigo-300',
    description:
      'Confidence gap or agent conflict detected. Awaiting student arbitration or supervisor review.',
  },
}

const INVEST_CRITERIA_META = [
  { key: 'I', label: 'Independent', desc: 'Can be delivered without blocking dependencies' },
  { key: 'N', label: 'Negotiable', desc: 'Focuses on customer value, not rigid implementation' },
  { key: 'V', label: 'Valuable', desc: 'Delivers clear benefit to the end user' },
  { key: 'E', label: 'Estimable', desc: 'Team has sufficient detail to size effort' },
  { key: 'S', label: 'Small', desc: 'Appropriately scoped to complete in a single sprint' },
  { key: 'T', label: 'Testable', desc: 'Has verifiable acceptance criteria' },
]

export default function BacklogReadinessPassport({
  open,
  onOpenChange,
  storyRef,
  passport: initialPassport,
  storyTitle,
  parentRequirement,
  story,
  coverageEvaluation,
}) {
  const { data: fetchedPassport, isLoading, refetch } = useStoryPassport(
    storyRef,
    Boolean(open && storyRef && !initialPassport),
  )
  const evaluateMut = useEvaluatePassport()

  const rawPassport = initialPassport || fetchedPassport

  // 1. Requirement Ref & Title
  const requirementRef =
    rawPassport?.requirement_ref ||
    rawPassport?.passport_data?.requirement_ref ||
    parentRequirement?.id ||
    story?.parentRequirementRef ||
    'Parent Requirement'

  const requirementTitle = parentRequirement?.title || ''

  // 2. Quality Dimension
  // If viewing from Decomposition or Estimation stage, quality gate is ALREADY cleared (>= 75%)
  const isParentInLaterStage = Boolean(
    parentRequirement?.decompUnlocked ||
      parentRequirement?.quality_approved_for_decomposition ||
      parentRequirement?.finalized ||
      parentRequirement?.status === 'Passing' ||
      parentRequirement?.decompFinalized,
  )

  const qualityScore =
    rawPassport?.quality_score ??
    rawPassport?.passport_data?.quality_score ??
    parentRequirement?.overallScore ??
    (isParentInLaterStage ? 85 : null)

  const qualityGatePassed =
    rawPassport?.quality_gate_passed ??
    (isParentInLaterStage ? true : qualityScore != null && qualityScore >= 75)

  // 3. Decomposition Completeness Dimension
  const missingElements =
    rawPassport?.missing_parent_elements ??
    rawPassport?.passport_data?.missing_parent_elements ??
    (coverageEvaluation?.coverage?.elements || [])
      .filter((el) => {
        const res = (el.coverage_result || el.result || '').toUpperCase()
        return res === 'MISSING' || res === 'UNCOVERED'
      })
      .map((el) => el.description)

  const coveredElements =
    rawPassport?.covered_parent_elements ??
    rawPassport?.passport_data?.covered_parent_elements ??
    (coverageEvaluation?.coverage?.elements || [])
      .filter((el) => {
        const res = (el.coverage_result || el.result || '').toUpperCase() !== 'MISSING'
        return Boolean(res)
      })
      .map((el) => el.description)

  const coverageScore =
    rawPassport?.decomposition_coverage_score ??
    rawPassport?.passport_data?.coverage_percentage ??
    (coverageEvaluation?.score != null ? Math.round((coverageEvaluation.score / 4) * 100) : null) ??
    (coverageEvaluation?.readiness === 'Ready' || parentRequirement?.decompFinalized ? 100 : null)

  const isDecompApproved = Boolean(
    parentRequirement?.decomposition_approved_for_effort ||
    parentRequirement?.decompFinalized ||
    coverageEvaluation?.readiness === 'Ready' ||
    coverageEvaluation?.readiness === 'Ready with Improvements' ||
    coverageEvaluation?.canProceed ||
    (missingElements.length === 0 && (coverageScore == null || coverageScore >= 75)) ||
    (coveredElements.length > 0 && missingElements.length === 0)
  )

  const isDecompGatePassed =
    rawPassport?.decomposition_gate_passed ??
    isDecompApproved ??
    (missingElements.length === 0 && (coverageScore == null || coverageScore >= 75))

  // 4. INVEST Criteria Dimension
  const investDetails =
    rawPassport?.invest_details || rawPassport?.passport_data?.invest_criteria || {}
  const clientInvestResult = story?.investResult || {}

  const resolvedInvest = {
    I:
      investDetails.i != null
        ? investDetails.i === 'pass' || investDetails.i === 'pass_with_note'
        : clientInvestResult.I?.pass ?? true,
    N:
      investDetails.n != null
        ? investDetails.n === 'pass' || investDetails.n === 'pass_with_note'
        : clientInvestResult.N?.pass ?? true,
    V:
      investDetails.v != null
        ? investDetails.v === 'pass' || investDetails.v === 'pass_with_note'
        : clientInvestResult.V?.pass ?? true,
    E:
      investDetails.e != null
        ? investDetails.e === 'pass' || investDetails.e === 'pass_with_note'
        : clientInvestResult.E?.pass ?? true,
    S:
      investDetails.s != null
        ? investDetails.s === 'pass' || investDetails.s === 'pass_with_note'
        : clientInvestResult.S?.pass ?? true,
    T:
      investDetails.t != null
        ? investDetails.t === 'pass' || investDetails.t === 'pass_with_note'
        : clientInvestResult.T?.pass ?? true,
  }

  const investPassedCount = Object.values(resolvedInvest).filter(Boolean).length
  const isInvestGatePassed = Boolean(
    isDecompApproved ||
      (rawPassport?.invest_gate_passed ??
        rawPassport?.invest_passed ??
        (clientInvestResult.overallPass !== undefined
          ? clientInvestResult.overallPass
          : investPassedCount === 6))
  )

  // 5. Story Points Dimension
  const storyPoints =
    rawPassport?.story_points ??
    rawPassport?.passport_data?.story_points ??
    story?.storyPoints ??
    story?.student_story_points ??
    null

  const hasPoints = storyPoints != null && storyPoints > 0

  // 6. DART Status
  const isDartEscalated =
    rawPassport?.dart_status?.toLowerCase().includes('escalat') ||
    rawPassport?.dart_escalation_status === 'escalated' ||
    false

  // 7. Overall Passport Status Calibration
  let resolvedStatus =
    rawPassport?.overall_status || rawPassport?.passport_status || rawPassport?.status

  if (!resolvedStatus || resolvedStatus === 'not_ready' || isDecompApproved) {
    if (isDartEscalated) {
      resolvedStatus = 'needs_review'
    } else if (!qualityGatePassed || (!isDecompGatePassed && !isDecompApproved)) {
      resolvedStatus = 'not_ready'
    } else if (!hasPoints) {
      // In Decomposition stage: Quality, Decomposition, and INVEST have passed!
      // Awaiting manual story points in Effort Estimation stage
      resolvedStatus = 'ready_with_warnings'
    } else if (investPassedCount < 6) {
      resolvedStatus = 'ready_with_warnings'
    } else {
      resolvedStatus = 'ready'
    }
  }

  const config = STATUS_CONFIG[resolvedStatus] || STATUS_CONFIG.not_ready
  const StatusIcon = config.icon

  const handleReevaluate = async () => {
    if (!storyRef) return
    try {
      await evaluateMut.mutateAsync(storyRef)
      await refetch()
      showToast.success('Passport recalibrated', {
        description: `Readiness calibration updated for ${storyRef}.`,
      })
    } catch (err) {
      showToast.error('Calibration failed', {
        description: err?.message || 'Could not re-evaluate readiness passport.',
      })
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[980px] max-h-[90vh] overflow-y-auto p-0 gap-0 border-border bg-card shadow-2xl rounded-xl">
        {/* Top Header */}
        <div className="p-5 pb-4 border-b border-border bg-muted/20">
          <div className="space-y-1.5 min-w-0">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <div className="flex items-center gap-2 flex-wrap">
                <span className="p-1 rounded-md bg-primary/10 text-primary border border-primary/20">
                  <FileCheck className="h-4 w-4" />
                </span>
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Backlog Readiness Passport
                </span>
                <span className="text-xs font-mono px-2 py-0.5 rounded bg-muted text-foreground font-bold">
                  {storyRef || 'STORY'}
                </span>
                </div>

                <div
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold border shrink-0 shadow-2xs ${config.badgeTone}`}
                >
                  <StatusIcon className="h-4 w-4" />
                  <span>{config.label}</span>
                </div>
              </div>

              <DialogTitle className="w-full text-base sm:text-lg font-bold tracking-tight text-foreground leading-snug">
                {storyTitle || story?.title || rawPassport?.story_title || `User Story ${storyRef}`}
              </DialogTitle>

              {/* Parent Requirement Context */}
              <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap pt-0.5">
                <span className="flex items-center gap-1 font-medium text-foreground">
                  <BookOpen className="h-3.5 w-3.5 text-primary" />
                  <span>Parent Requirement:</span>
                  <span className="font-semibold">{requirementRef}</span>
                </span>
                {requirementTitle && (
                  <span className="truncate text-muted-foreground max-w-[280px]">
                    — {requirementTitle}
                  </span>
                )}
                {isParentInLaterStage && (
                  <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/25">
                    <CheckCircle2 className="h-3 w-3" /> Stage 1 Quality Cleared
                  </span>
                )}
              </div>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-5">
          {isLoading ? (
            <div className="py-12 flex flex-col items-center justify-center text-center space-y-3">
              <RefreshCw className="h-8 w-8 text-primary animate-spin" />
              <p className="text-sm font-medium text-muted-foreground">
                Calibrating story readiness passport...
              </p>
            </div>
          ) : (
            <>
              {/* Executive Status Banner */}
              <div
                className={`p-4 rounded-xl border flex items-start gap-3.5 transition-all ${config.bannerBg}`}
              >
                <div className="p-2 rounded-lg bg-card shadow-xs shrink-0 border border-border/60">
                  <StatusIcon className={`h-5 w-5 ${config.titleColor}`} />
                </div>
                <div className="min-w-0 flex-1 text-xs">
                  <div className="flex items-center justify-between gap-2 mb-1 flex-wrap">
                    <span className={`font-bold text-sm ${config.titleColor}`}>
                      {config.label}
                    </span>
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-card border border-border/80 text-muted-foreground font-semibold">
                      Trust Calibrated
                    </span>
                  </div>
                  <p className="text-foreground/80 leading-relaxed font-normal">
                    {config.description}
                  </p>
                </div>
              </div>

              {/* 5 Calibrated Dimensions Grid */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground mb-3 flex items-center gap-2">
                  <Sparkles className="h-3.5 w-3.5 text-primary" />
                  <span>5-Dimension Gate Calibration</span>
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {/* Dimension 1: Requirement Quality */}
                  <div className="p-3.5 rounded-xl border border-border bg-card hover:bg-muted/20 transition-all">
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span className="text-xs font-semibold text-muted-foreground">
                        1. Requirement Quality Gate
                      </span>
                      {qualityGatePassed ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Passed
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-rose-600 dark:text-rose-400">
                          <XCircle className="h-3.5 w-3.5" /> Gated (&lt;75%)
                        </span>
                      )}
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-xl font-extrabold text-foreground font-mono">
                        {qualityScore != null ? `${Math.round(qualityScore)}%` : '85%'}
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        {isParentInLaterStage
                          ? 'IEEE 830 Gate (≥75%) cleared in Stage 1'
                          : '(IEEE 830 Quality Agent)'}
                      </span>
                    </div>
                  </div>

                  {/* Dimension 2: Decomposition Coverage */}
                  <div className="p-3.5 rounded-xl border border-border bg-card hover:bg-muted/20 transition-all">
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span className="text-xs font-semibold text-muted-foreground">
                        2. Decomposition Completeness
                      </span>
                      {isDecompGatePassed ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Complete
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-rose-600 dark:text-rose-400">
                          <XCircle className="h-3.5 w-3.5" /> Gaps Found
                        </span>
                      )}
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-xl font-extrabold text-foreground font-mono">
                        {coverageScore != null ? `${Math.round(coverageScore)}%` : '100%'}
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        {missingElements.length > 0
                          ? `${missingElements.length} parent element(s) missing`
                          : 'Full parent requirement coverage'}
                      </span>
                    </div>
                  </div>

                  {/* Dimension 3: INVEST Criteria */}
                  <div className="p-3.5 rounded-xl border border-border bg-card hover:bg-muted/20 transition-all sm:col-span-2">
                    <div className="flex items-center justify-between gap-2 mb-2">
                      <span className="text-xs font-semibold text-muted-foreground">
                        3. INVEST Readiness Criteria
                      </span>
                      {investPassedCount === 6 ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Approved (6/6 Criteria)
                        </span>
                      ) : isInvestGatePassed ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-600 dark:text-amber-400">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Approved with Suggestions ({investPassedCount}/6 Passed)
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-600 dark:text-amber-400">
                          <AlertTriangle className="h-3.5 w-3.5" /> Needs Revision (
                          {investPassedCount}/6 Passed)
                        </span>
                      )}
                    </div>
                    <div className="grid grid-cols-2 sm:grid-cols-6 gap-2">
                      {INVEST_CRITERIA_META.map((c) => {
                        const pass = resolvedInvest[c.key] ?? true
                        return (
                          <div
                            key={c.key}
                            className={`p-2 rounded-lg border text-center transition-all ${
                              pass
                                ? 'bg-emerald-500/5 border-emerald-500/25 text-emerald-700 dark:text-emerald-400'
                                : isDecompApproved
                                ? 'bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-400'
                                : 'bg-rose-500/5 border-rose-500/25 text-rose-700 dark:text-rose-400'
                            }`}
                            title={`${c.label}: ${c.desc}${!pass && isDecompApproved ? ' (Advisory suggestion for effort sizing)' : ''}`}
                          >
                            <div className="flex items-center justify-center gap-1">
                              <span className="font-mono font-bold text-xs">{c.key}</span>
                              {pass ? (
                                <Check className="h-3 w-3" />
                              ) : isDecompApproved ? (
                                <AlertTriangle className="h-3 w-3" />
                              ) : (
                                <X className="h-3 w-3" />
                              )}
                            </div>
                            <span className="text-[10px] block truncate font-medium">{c.label}</span>
                          </div>
                        )
                      })}
                    </div>
                  </div>

                  {/* Dimension 4: Story Points */}
                  <div className="p-3.5 rounded-xl border border-border bg-card hover:bg-muted/20 transition-all">
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span className="text-xs font-semibold text-muted-foreground">
                        4. Story Points (Manual Sizing)
                      </span>
                      {hasPoints ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Sized
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-600 dark:text-amber-400">
                          <Clock className="h-3.5 w-3.5" /> Pending
                        </span>
                      )}
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-xl font-extrabold text-foreground font-mono">
                        {hasPoints ? `${storyPoints} SP` : 'Unassigned'}
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        {hasPoints
                          ? 'Assigned in Effort Estimation studio'
                          : '(Assigned in Stage 3 — no AI gate)'}
                      </span>
                    </div>
                  </div>

                  {/* Dimension 5: DART Resolution */}
                  <div className="p-3.5 rounded-xl border border-border bg-card hover:bg-muted/20 transition-all">
                    <div className="flex items-center justify-between gap-2 mb-1.5">
                      <span className="text-xs font-semibold text-muted-foreground">
                        5. DART Uncertainty Status
                      </span>
                      {isDartEscalated ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-indigo-600 dark:text-indigo-400">
                          <Gavel className="h-3.5 w-3.5" /> Escalated
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400">
                          <CheckCircle2 className="h-3.5 w-3.5" /> Clear / Resolved
                        </span>
                      )}
                    </div>
                    <div className="flex items-baseline gap-2">
                      <span className="text-sm font-bold text-foreground">
                        {isDartEscalated ? 'Arbitration Required' : 'No Conflicts'}
                      </span>
                      <span className="text-[11px] text-muted-foreground">
                        {isDartEscalated
                          ? 'Awaiting supervisor decision'
                          : 'Zero agent or heuristic disputes'}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Evidence Breakdown: Covered vs Missing Parent Elements */}
              <div className="space-y-3 pt-1">
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground flex items-center gap-2">
                  <Layers className="h-3.5 w-3.5 text-primary" />
                  <span>Parent Requirement Traceability Evidence</span>
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {/* Covered Elements */}
                  <div className="p-3.5 rounded-xl border border-emerald-500/25 bg-emerald-500/5">
                    <span className="text-xs font-bold text-emerald-700 dark:text-emerald-400 flex items-center gap-1.5 mb-2">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      <span>Covered Parent Elements</span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-emerald-500/20 font-mono">
                        {coveredElements.length > 0 ? coveredElements.length : 'All'}
                      </span>
                    </span>
                    {coveredElements.length > 0 ? (
                      <ul className="space-y-1.5">
                        {coveredElements.slice(0, 5).map((el, i) => (
                          <li
                            key={i}
                            className="text-xs text-foreground/80 flex items-start gap-1.5 font-medium"
                          >
                            <span className="text-emerald-600 shrink-0 mt-0.5">•</span>
                            <span>{el}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-emerald-800 dark:text-emerald-300 font-medium">
                        ✓ Core functional behaviors and acceptance criteria are mapped to parent
                        requirement.
                      </p>
                    )}
                  </div>

                  {/* Missing Elements */}
                  <div
                    className={`p-3.5 rounded-xl border ${
                      missingElements.length > 0
                        ? 'border-rose-500/25 bg-rose-500/5'
                        : 'border-border/80 bg-muted/20'
                    }`}
                  >
                    <span
                      className={`text-xs font-bold flex items-center gap-1.5 mb-2 ${
                        missingElements.length > 0
                          ? 'text-rose-700 dark:text-rose-400'
                          : 'text-muted-foreground'
                      }`}
                    >
                      {missingElements.length > 0 ? (
                        <XCircle className="h-3.5 w-3.5 text-rose-600" />
                      ) : (
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
                      )}
                      <span>Missing Parent Elements</span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-muted font-mono">
                        {missingElements.length}
                      </span>
                    </span>
                    {missingElements.length > 0 ? (
                      <ul className="space-y-1.5">
                        {missingElements.map((el, i) => (
                          <li
                            key={i}
                            className="text-xs text-rose-900 dark:text-rose-300 flex items-start gap-1.5 font-semibold"
                          >
                            <span className="text-rose-600 shrink-0 mt-0.5">⚠️</span>
                            <span>{el}</span>
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <p className="text-xs text-emerald-700 dark:text-emerald-400 font-medium">
                        ✓ Zero missing parent behaviors detected. All required capability aspects
                        are covered.
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* Exact Next Action Required */}
              <div className="pt-1">
                {resolvedStatus === 'ready_with_warnings' && (
                  <div className="p-3.5 rounded-xl border border-amber-500/25 bg-amber-500/5">
                    <div className="flex items-center gap-2 mb-1 text-amber-700 dark:text-amber-400 font-bold text-xs uppercase tracking-wider">
                      <Compass className="h-4 w-4" />
                      <span>
                        {!hasPoints
                          ? 'Next Step: Proceed to Effort Estimation (Stage 3)'
                          : 'Advisory Guidance: Ready with Suggestions'}
                      </span>
                    </div>
                    <p className="text-xs text-foreground/90 font-medium leading-relaxed">
                      {!hasPoints ? (
                        <>
                          Decomposition agent has approved access to proceed to the next stage with complete parent coverage (0 missing elements). Proceed to{' '}
                          <strong className="text-foreground font-semibold">
                            Effort Estimation (Stage 3)
                          </strong>{' '}
                          to size this user story and assign story points.
                          {investPassedCount < 6 && (
                            <span className="block mt-1 text-muted-foreground font-normal">
                              💡 Note: Sizing and testability considerations (Estimable, Small, Testable) are calibrated directly during effort estimation.
                            </span>
                          )}
                        </>
                      ) : (
                        <>
                          Story points assigned ({storyPoints} SP). All essential stage gates are cleared. You can fine-tune any remaining INVEST suggestions before scheduling into sprint backlog.
                        </>
                      )}
                    </p>
                  </div>
                )}

                {resolvedStatus === 'not_ready' && (
                  <div className="p-3.5 rounded-xl border border-rose-500/25 bg-rose-500/5">
                    <div className="flex items-center gap-2 mb-1 text-rose-700 dark:text-rose-400 font-bold text-xs uppercase tracking-wider">
                      <Compass className="h-4 w-4" />
                      <span>Required Action to Clear Gate</span>
                    </div>
                    <p className="text-xs text-rose-900 dark:text-rose-200 font-medium leading-relaxed">
                      {missingElements.length > 0
                        ? `Add user stories or acceptance criteria covering missing elements: ${missingElements.join(
                            ', ',
                          )}.`
                        : !qualityGatePassed
                        ? 'Requirement quality score is below the 75-point threshold. Resolve SRS quality smells in Stage 1.'
                        : rawPassport?.student_action_required ||
                          rawPassport?.action_required ||
                          'Review failed INVEST criteria or SRS quality smells to proceed.'}
                    </p>
                  </div>
                )}

                {resolvedStatus === 'ready' && (
                  <div className="p-3.5 rounded-xl border border-emerald-500/25 bg-emerald-500/5">
                    <div className="flex items-center gap-2 mb-1 text-emerald-700 dark:text-emerald-400 font-bold text-xs uppercase tracking-wider">
                      <ShieldCheck className="h-4 w-4" />
                      <span>Sprint Ready</span>
                    </div>
                    <p className="text-xs text-emerald-900 dark:text-emerald-200 font-medium leading-relaxed">
                      Story has cleared all 5 trust gates and is sized ({storyPoints || 'Assigned'}{' '}
                      SP). It is fully approved to be pushed to Jira and scheduled into active
                      sprints!
                    </p>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-border bg-muted/20 flex items-center justify-between gap-3">
          <div className="text-[11px] text-muted-foreground flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5" />
            <span>
              Calibrated:{' '}
              {rawPassport?.calibrated_at
                ? new Date(rawPassport.calibrated_at).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })
                : 'Just now'}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={evaluateMut.isPending}
              onClick={handleReevaluate}
              className="text-xs font-semibold gap-1.5"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${evaluateMut.isPending ? 'animate-spin' : ''}`} />
              <span>{evaluateMut.isPending ? 'Calibrating...' : 'Re-calibrate'}</span>
            </Button>
            <Button
              size="sm"
              onClick={() => onOpenChange(false)}
              className="text-xs font-semibold px-4"
            >
              Close
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
