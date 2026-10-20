import { useState } from 'react'
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Target,
  Compass,
  Lightbulb,
  Sparkles,
  ShieldCheck,
  Lock,
  ArrowRight,
  Brain,
  Info,
} from 'lucide-react'
import Card from '../../../shared/components/Card.jsx'
import Badge from '../../../shared/components/Badge.jsx'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'

const STAGE_META = {
  srs_quality: {
    title: 'Stage 1 Gate Pass Criteria: What to Achieve',
    subtitle: 'IEEE 830 Quality Standard — Minimum 75% required to unlock Decomposition',
    targetScoreLabel: 'Target Score: ≥ 75%',
    gateName: 'SRS Requirement Quality Gate',
  },
  decomposition: {
    title: 'Stage 2 Gate Pass Criteria: What to Achieve',
    subtitle: 'Decomposition Completeness & INVEST — Required to unlock Effort Estimation',
    targetScoreLabel: 'Target Coverage: ≥ 75% + 0 Critical Missing',
    gateName: 'Decomposition Completeness Gate',
  },
  estimation: {
    title: 'Stage 3 Pass Criteria: What to Achieve',
    subtitle: 'Student Direct Effort Sizing — Required for Backlog Readiness & Jira Sync',
    targetScoreLabel: 'Story Points Assigned (Fibonacci Scale)',
    gateName: 'Ready Backlog Passport Gate',
  },
}

export default function StagePassCriteriaCard({
  stage = 'srs_quality',
  requirement,
  evaluation,
  stories = [],
  estimations = {},
  passports = [],
  onActionClick,
  actionLoading = false,
  className = '',
  defaultExpanded = true,
}) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const meta = STAGE_META[stage] || STAGE_META.srs_quality

  // ─────────────────────────────────────────────────────────────
  // Build Checklist Items Based on Stage
  // ─────────────────────────────────────────────────────────────

  let criteriaList = []

  if (stage === 'srs_quality') {
    const overallScore = Math.round(requirement?.overallScore ?? 0)
    const isPassing = overallScore >= 75
    const dims = requirement?.dimensionScores || {}
    const dimDetails = requirement?.dimensionDetails || {}

    // Dimension helper
    const getDim = (key, fallbackName) => {
      const score = Math.round(dims[key] ?? (overallScore > 0 ? overallScore : 0))
      const pass = score >= 75
      const remedy = dimDetails[key]?.remedy || ''
      const issues = dimDetails[key]?.issues || []
      return { score, pass, remedy, issues, name: fallbackName }
    }

    const unambiguity = getDim('unambiguity', 'Unambiguity & Concrete Wording')
    const completeness = getDim('completeness', 'Completeness & Preconditions')
    const verifiability = getDim('verifiability', 'Verifiability & Testability')
    const consistency = getDim('consistency', 'Consistency & Atomic Modifiability')

    criteriaList = [
      {
        id: 'overall_score',
        title: 'Minimum Overall IEEE 830 Score ≥ 75%',
        current: `${overallScore}%`,
        target: '≥ 75%',
        passed: isPassing,
        severity: isPassing ? 'success' : 'danger',
        feedback: isPassing
          ? 'Requirement satisfies the minimum IEEE 830 quality threshold for decomposition.'
          : `Requirement scored ${overallScore}%. It needs +${75 - overallScore}% more to pass the gate.`,
        action: isPassing
          ? 'Ready to proceed to Stage 2.'
          : 'Review flagged ambiguities, missing error handling, and test criteria in the editor below, then re-check.',
      },
      {
        id: 'unambiguity',
        title: 'Unambiguity & Exact Metrics (Target: ≥ 75%)',
        current: `${unambiguity.score}%`,
        target: '≥ 75%',
        passed: unambiguity.pass,
        severity: unambiguity.pass ? 'success' : 'warning',
        feedback: unambiguity.pass
          ? 'No subjective, ambiguous, or vague qualifiers detected.'
          : (unambiguity.issues[0] || 'Vague adjectives or weak modal verbs detected (e.g. "fast", "user-friendly", "flexible").'),
        action: unambiguity.remedy || 'Replace subjective qualifiers with exact quantitative metrics (e.g. response < 500ms).',
      },
      {
        id: 'completeness',
        title: 'Operational Completeness & Error Scenarios (Target: ≥ 75%)',
        current: `${completeness.score}%`,
        target: '≥ 75%',
        passed: completeness.pass,
        severity: completeness.pass ? 'success' : 'warning',
        feedback: completeness.pass
          ? 'Inputs, state transitions, and expected outputs are clearly outlined.'
          : (completeness.issues[0] || 'Missing edge-case, validation, or error recovery behavior.'),
        action: completeness.remedy || 'Specify what the system must do if an invalid input or system error occurs.',
      },
      {
        id: 'verifiability',
        title: 'Verifiability / Testable Assertions (Target: ≥ 75%)',
        current: `${verifiability.score}%`,
        target: '≥ 75%',
        passed: verifiability.pass,
        severity: verifiability.pass ? 'success' : 'warning',
        feedback: verifiability.pass
          ? 'Requirement has clear, observable pass/fail verification conditions.'
          : (verifiability.issues[0] || 'Difficult for automated tests or QA engineers to objectively verify.'),
        action: verifiability.remedy || 'Define precise observable behaviors or state changes that can be asserted in a test.',
      },
      {
        id: 'consistency',
        title: 'Cross-Requirement Consistency & Modifiability (Target: ≥ 75%)',
        current: `${consistency.score}%`,
        target: '≥ 75%',
        passed: consistency.pass,
        severity: consistency.pass ? 'success' : 'neutral',
        feedback: consistency.pass
          ? 'Consistent terminology with no contradictory constraints.'
          : (consistency.issues[0] || 'Potential terminology overlap or conflicting business logic.'),
        action: consistency.remedy || 'Ensure terms match throughout the SRS and requirement is focused on a single concern.',
      },
    ]
  } else if (stage === 'decomposition') {
    const coveragePct = Math.round(evaluation?.coverage?.percentage ?? 0)
    const covElements = evaluation?.coverage?.elements || []
    const missingElements = covElements.filter((el) => {
      const res = (el.coverage_result || el.result || '').toUpperCase()
      return res === 'MISSING' || res === 'UNCOVERED'
    })
    const criticalMissing = missingElements.filter((el) => {
      const t = (el.element_type || '').toLowerCase()
      return ['exception_behavior', 'error_handling', 'recovery_retry', 'business_rule'].some((k) =>
        t.includes(k),
      )
    })

    const totalStories = stories.length
    const passingInvestCount = stories.filter(
      (s) => s.investResult && s.investResult.overallPass,
    ).length
    const storiesWithAC = stories.filter((s) => {
      const ac = s.acceptanceCriteria || s.acceptance_criteria || []
      return Array.isArray(ac) ? ac.length > 0 : Boolean(ac && String(ac).trim())
    }).length
    const storiesWithTasks = stories.filter(
      (s) => Array.isArray(s.tasks) && s.tasks.length > 0,
    ).length
    const storiesWithoutTasks = stories.filter(
      (s) => !Array.isArray(s.tasks) || s.tasks.length === 0,
    )

    const isCoveragePassed = coveragePct >= 75
    const isZeroCritical = criticalMissing.length === 0
    const isInvestPassed = totalStories > 0 && passingInvestCount === totalStories
    const isACPresent = totalStories > 0 && storiesWithAC === totalStories
    const isReady = evaluation?.readiness === 'Ready'

    criteriaList = [
      {
        id: 'coverage_pct',
        title: 'Parent Requirement Coverage ≥ 75%',
        current: `${coveragePct}%`,
        target: '≥ 75%',
        passed: isCoveragePassed,
        severity: isCoveragePassed ? 'success' : 'danger',
        feedback: isCoveragePassed
          ? 'Child user stories cover the required operational scope of the parent specification.'
          : `Decomposition coverage is ${coveragePct}%. You need +${75 - coveragePct}% to unlock Effort Estimation.`,
        action: isCoveragePassed
          ? 'Coverage threshold cleared.'
          : 'Add user stories or acceptance criteria representing missing capabilities.',
      },
      {
        id: 'zero_critical',
        title: 'Zero Critical Missing Parent Capabilities (0 Missing)',
        current: `${criticalMissing.length} critical missing`,
        target: '0 Missing',
        passed: isZeroCritical,
        severity: isZeroCritical ? 'success' : 'danger',
        feedback: isZeroCritical
          ? 'All parent business rules, constraints, and exception behaviors are addressed.'
          : `Gated: ${criticalMissing.length} critical parent requirement capability is unrepresented in your stories.`,
        missingPills: criticalMissing.map((el) => el.description),
        action: isZeroCritical
          ? 'No critical gaps.'
          : `Add explicit acceptance criteria covering: ${criticalMissing.map((el) => `"${el.description}"`).join(', ')}.`,
      },
      {
        id: 'invest_compliance',
        title: 'INVEST Compliance on All Stories (≥ 4/6 criteria)',
        current: `${passingInvestCount}/${totalStories} stories passing`,
        target: `${totalStories}/${totalStories} passed`,
        passed: isInvestPassed,
        severity: isInvestPassed ? 'success' : 'warning',
        feedback: isInvestPassed
          ? 'All decomposed user stories pass the 6 INVEST agile criteria.'
          : `${totalStories - passingInvestCount} stor${totalStories - passingInvestCount === 1 ? 'y needs' : 'ies need'} revision (failed valuable, estimable, or testable).`,
        action: isInvestPassed
          ? 'Stories are well-formed.'
          : 'Refine the story statement to follow: "As a [persona], I want [capability] so that [benefit]".',
      },
      {
        id: 'acceptance_criteria',
        title: 'Verifiable Acceptance Criteria Attached to Each Story',
        current: `${storiesWithAC}/${totalStories} stories ready`,
        target: 'All stories',
        passed: isACPresent,
        severity: isACPresent ? 'success' : 'warning',
        feedback: isACPresent
          ? 'Every user story has clear, observable acceptance criteria.'
          : 'One or more user stories are missing acceptance criteria.',
        action: isACPresent
          ? 'Acceptance criteria defined.'
          : 'Add bulleted or Given-When-Then criteria defining how to test each story.',
      },
      {
        id: 'implementation_tasks',
        title: 'At Least One Implementation Task Attached to Each Story',
        current: `${storiesWithTasks}/${totalStories} stories with tasks`,
        target: 'All stories',
        passed: totalStories > 0 && storiesWithTasks === totalStories,
        severity: storiesWithTasks === totalStories && totalStories > 0 ? 'success' : 'danger',
        feedback: storiesWithTasks === totalStories && totalStories > 0
          ? 'Every user story has at least one concrete implementation task.'
          : `${storiesWithoutTasks.length} stor${storiesWithoutTasks.length === 1 ? 'y is' : 'ies are'} missing an implementation task.`,
        missingPills: storiesWithoutTasks.map((story) => story.id || story.story_ref || story.title),
        action: storiesWithTasks === totalStories && totalStories > 0
          ? 'Task breakdown complete.'
          : 'Open each listed story and add at least one concrete development task before proceeding to effort estimation.',
      },
      {
        id: 'quality_band',
        title: 'Decomposition Quality Band: Ready (Score ≥ 3.0/4.0)',
        current: `${evaluation?.score ?? 0}/4 · ${evaluation?.readiness || 'Needs Attention'}`,
        target: 'Ready (≥ 3.0/4)',
        passed: isReady,
        severity: isReady ? 'success' : 'danger',
        feedback: isReady
          ? 'Decomposition has passed all automated quality gates and is approved for Effort Estimation.'
          : 'Gate is blocked until coverage gaps and story revisions are resolved.',
        action: isReady
          ? 'Proceed to Effort Estimation.'
          : 'Make the improvements outlined above, then click Re-run Analysis.',
      },
    ]
  } else if (stage === 'estimation') {
    const totalStories = stories.length
    let estimatedCount = 0
    let withBasisCount = 0

    stories.forEach((s) => {
      const pts =
        estimations[s.id]?.finalPoints ??
        estimations[s.id]?.studentPoints ??
        s.student_story_points ??
        null
      if (pts != null) estimatedCount += 1
      if (estimations[s.id]?.reason || s.estimation_basis) withBasisCount += 1
    })

    const allEstimated = totalStories > 0 && estimatedCount === totalStories
    const hasBasis = withBasisCount > 0

    criteriaList = [
      {
        id: 'points_assigned',
        title: 'Fibonacci Story Points Assigned (All Stories)',
        current: `${estimatedCount}/${totalStories} estimated`,
        target: '100% estimated',
        passed: allEstimated,
        severity: allEstimated ? 'success' : 'danger',
        feedback: allEstimated
          ? 'All stories have received human effort estimates from the agile team.'
          : `${totalStories - estimatedCount} stor${totalStories - estimatedCount === 1 ? 'y is' : 'ies are'} missing story points.`,
        action: allEstimated
          ? 'Sizing complete.'
          : 'Assign 1, 2, 3, 5, 8, or 13 story points to unestimated stories (no AI check required).',
      },
      {
        id: 'estimation_basis',
        title: 'Estimation Rationale / Basis Recorded',
        current: `${withBasisCount}/${totalStories} with rationale`,
        target: 'Recommended',
        passed: hasBasis,
        severity: hasBasis ? 'success' : 'neutral',
        feedback: hasBasis
          ? 'Engineering rationale has been documented for the team.'
          : 'Optional: noting reasoning helps your team defend estimates during sprint planning.',
        action: 'Add a brief note explaining complexity, external dependencies, or testing needs.',
      },
      {
        id: 'passport_certified',
        title: 'Backlog Readiness Passport Qualified (🟢 Ready)',
        current: allEstimated ? 'Ready for Backlog' : 'Pending Points',
        target: '🟢 Ready',
        passed: allEstimated,
        severity: allEstimated ? 'success' : 'warning',
        feedback: allEstimated
          ? 'Stories satisfy all 5 dimensions and are certified for Sprint Planning and Jira sync.'
          : 'Stories cannot enter the Jira Product Backlog until story points are assigned.',
        action: 'Review the Backlog Readiness Passport to verify gate clearance.',
      },
    ]
  }

  // Calculate overall progress percentage
  const totalCriteria = criteriaList.length
  const passedCriteria = criteriaList.filter((c) => c.passed).length
  const progressPercent = totalCriteria > 0 ? Math.round((passedCriteria / totalCriteria) * 100) : 0
  const allAchieved = passedCriteria === totalCriteria

  return (
    <Card className={`p-4 border-border/80 bg-card/60 backdrop-blur-xs transition-all ${className}`}>
      {/* Top Header / Progress Summary */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span
              className={`p-1 rounded-md text-xs font-bold border ${
                allAchieved
                  ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
                  : 'bg-primary/10 text-primary border-primary/20'
              }`}
            >
              <Target className="h-4 w-4" />
            </span>
            <h4 className="text-sm font-bold text-foreground tracking-tight">{meta.title}</h4>
            <Badge
              tone={allAchieved ? 'success' : passedCriteria > 0 ? 'warning' : 'danger'}
              className="text-[11px] font-bold px-2 py-0.5"
            >
              {allAchieved
                ? 'All Gate Criteria Achieved'
                : `${passedCriteria}/${totalCriteria} Criteria Achieved (${progressPercent}%)`}
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground">{meta.subtitle}</p>
        </div>

        {/* Action Toggle & Button */}
        <div className="flex items-center gap-2 shrink-0">
          {onActionClick && (
            <Button
              size="sm"
              variant="outline"
              disabled={actionLoading}
              onClick={onActionClick}
              className="text-xs h-7 gap-1 font-semibold cursor-pointer border-border/80"
            >
              <Brain className={`h-3 w-3 ${actionLoading ? 'animate-spin' : ''}`} />
              <span>{actionLoading ? 'Evaluating...' : 'Re-check Gate'}</span>
            </Button>
          )}
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-md border border-border/60 hover:bg-muted/50 text-muted-foreground hover:text-foreground transition-all cursor-pointer"
          >
            <span>{expanded ? 'Collapse' : 'View Checklist'}</span>
            {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Mini Progress Bar */}
      <div className="mt-3 space-y-1">
        <div className="flex items-center justify-between text-[11px]">
          <span className="text-muted-foreground font-medium">Gate Qualification Progress</span>
          <span className="font-mono font-bold text-foreground">
            {passedCriteria} of {totalCriteria} items satisfied ({progressPercent}%)
          </span>
        </div>
        <Progress
          value={progressPercent}
          className="h-1.5"
          indicatorClassName={
            allAchieved ? 'bg-emerald-500' : progressPercent >= 60 ? 'bg-amber-500' : 'bg-rose-500'
          }
        />
      </div>

      {/* Expandable Criteria List */}
      {expanded && (
        <div className="mt-4 pt-3 border-t border-border/60 space-y-2.5 animate-fade-rise">
          {criteriaList.map((item) => (
            <div
              key={item.id}
              className={`p-3 rounded-xl border transition-all text-xs ${
                item.passed
                  ? 'bg-emerald-500/5 border-emerald-500/20 text-foreground'
                  : item.severity === 'danger'
                    ? 'bg-rose-500/5 border-rose-500/25 text-foreground'
                    : 'bg-amber-500/5 border-amber-500/25 text-foreground'
              }`}
            >
              <div className="flex items-start justify-between gap-2.5 flex-wrap">
                <div className="flex items-start gap-2 min-w-0 flex-1">
                  {item.passed ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0 mt-0.5" />
                  ) : item.severity === 'danger' ? (
                    <XCircle className="h-4 w-4 text-rose-600 dark:text-rose-400 shrink-0 mt-0.5" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap mb-0.5">
                      <span className="font-bold text-foreground text-xs">{item.title}</span>
                      <span
                        className={`text-[10px] font-mono px-1.5 py-0.2 rounded font-semibold ${
                          item.passed
                            ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
                            : 'bg-muted text-muted-foreground'
                        }`}
                      >
                        Current: {item.current} (Target: {item.target})
                      </span>
                    </div>

                    <p className="text-muted-foreground text-[11px] leading-relaxed mb-1.5">
                      {item.feedback}
                    </p>

                    {/* Missing pills if present */}
                    {item.missingPills && item.missingPills.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 mb-2">
                        {item.missingPills.map((pill, idx) => (
                          <span
                            key={idx}
                            className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded bg-rose-500/15 border border-rose-500/30 text-rose-800 dark:text-rose-300 font-semibold"
                          >
                            ⚠️ {pill}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Actionable Student Improvement Step */}
                    <div className="p-2 rounded-lg bg-background/80 border border-border/60 flex items-start gap-1.5 text-[11px]">
                      <Lightbulb className="h-3.5 w-3.5 text-amber-500 shrink-0 mt-0.5" />
                      <div>
                        <span className="font-semibold text-foreground">Action to Improve: </span>
                        <span className="text-muted-foreground">{item.action}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="shrink-0 text-right">
                  <span
                    className={`inline-block text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                      item.passed
                        ? 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-300'
                        : 'bg-rose-500/20 text-rose-700 dark:text-rose-300'
                    }`}
                  >
                    {item.passed ? 'Achieved ✓' : 'Needs Action ✗'}
                  </span>
                </div>
              </div>
            </div>
          ))}

          {/* Educational Bottom Tip */}
          <div className="p-2.5 rounded-xl bg-muted/30 border border-border/60 text-xs text-muted-foreground flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Compass className="h-4 w-4 text-primary shrink-0" />
              <span>
                <strong>Academic Tip:</strong> Satisfying all criteria above clears this requirement’s gate and marks its stories eligible for the <strong>Backlog Readiness Passport</strong>.
              </span>
            </div>
          </div>
        </div>
      )}
    </Card>
  )
}
