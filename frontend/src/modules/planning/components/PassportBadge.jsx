import { useState } from 'react'
import { ShieldCheck, AlertTriangle, Lock, Gavel } from 'lucide-react'
import BacklogReadinessPassport from './BacklogReadinessPassport.jsx'

const BADGE_CONFIG = {
  ready: {
    label: 'Ready Backlog',
    shortLabel: 'Ready',
    classes: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/25',
    icon: ShieldCheck,
  },
  ready_with_warnings: {
    label: 'Ready (Warnings)',
    shortLabel: 'Ready*',
    classes: 'bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30 hover:bg-amber-500/25',
    icon: AlertTriangle,
  },
  not_ready: {
    label: 'Not Ready',
    shortLabel: 'Gated',
    classes: 'bg-rose-500/15 text-rose-700 dark:text-rose-400 border-rose-500/30 hover:bg-rose-500/25',
    icon: Lock,
  },
  needs_review: {
    label: 'Needs Review',
    shortLabel: 'DART',
    classes: 'bg-indigo-500/15 text-indigo-700 dark:text-indigo-400 border-indigo-500/30 hover:bg-indigo-500/25',
    icon: Gavel,
  },
}

const SIZE_CLASSES = {
  xs: 'px-1.5 py-0.5 text-[10px] gap-1',
  sm: 'px-2 py-0.5 text-xs gap-1.5',
  default: 'px-2.5 py-1 text-xs gap-1.5',
}

const ICON_SIZES = {
  xs: 'h-2.5 w-2.5',
  sm: 'h-3 w-3',
  default: 'h-3.5 w-3.5',
}

export default function PassportBadge({
  status,
  storyRef,
  storyTitle,
  passport,
  parentRequirement,
  story,
  coverageEvaluation,
  openOnClick = true,
  onClick,
  className = '',
  size = 'sm',
  showIcon = true,
  short = false,
}) {
  const [modalOpen, setModalOpen] = useState(false)

  // Resolve status key
  let computedStatus =
    passport?.passport_status || passport?.status || passport?.overall_status || status

  const isDecompApproved = Boolean(
    parentRequirement?.decomposition_approved_for_effort ||
    parentRequirement?.decompFinalized ||
    coverageEvaluation?.readiness === 'Ready' ||
    coverageEvaluation?.readiness === 'Ready with Improvements' ||
    coverageEvaluation?.canProceed ||
    (coverageEvaluation?.coverage?.elements &&
      coverageEvaluation.coverage.elements.filter(
        (el) => {
          const res = (el.coverage_result || el.result || '').toUpperCase()
          return res === 'MISSING' || res === 'UNCOVERED'
        }
      ).length === 0)
  )

  if ((!computedStatus || computedStatus === 'not_ready') && isDecompApproved) {
    const hasPoints = (story?.storyPoints ?? story?.student_story_points) > 0
    if (hasPoints) {
      computedStatus = 'ready'
    } else {
      computedStatus = 'ready_with_warnings'
    }
  } else if (!computedStatus && story) {
    const hasPoints = (story.storyPoints ?? story.student_story_points) > 0
    const investPass = story.investResult ? story.investResult.overallPass !== false : true
    const decompReady =
      coverageEvaluation?.readiness === 'Ready' || Boolean(parentRequirement?.decompFinalized)

    if (decompReady && investPass && hasPoints) {
      computedStatus = 'ready'
    } else if (decompReady && investPass) {
      computedStatus = 'ready_with_warnings'
    } else {
      computedStatus = 'not_ready'
    }
  }

  const resolvedStatus = computedStatus || 'not_ready'
  const config = BADGE_CONFIG[resolvedStatus] || BADGE_CONFIG.not_ready
  const Icon = config.icon

  const handleClick = (e) => {
    e.stopPropagation()
    if (onClick) {
      onClick(e)
    } else if (openOnClick) {
      setModalOpen(true)
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={handleClick}
        title={`Backlog Readiness Passport: ${config.label}. Click to inspect gate calibration.`}
        className={`inline-flex items-center font-bold rounded-md border transition-all cursor-pointer shadow-2xs select-none ${
          config.classes
        } ${SIZE_CLASSES[size] || SIZE_CLASSES.sm} ${className}`}
      >
        {showIcon && <Icon className={ICON_SIZES[size] || ICON_SIZES.sm} strokeWidth={2.25} />}
        <span>{short ? config.shortLabel : config.label}</span>
      </button>

      {openOnClick && (
        <BacklogReadinessPassport
          open={modalOpen}
          onOpenChange={setModalOpen}
          storyRef={storyRef}
          storyTitle={storyTitle}
          passport={passport}
          parentRequirement={parentRequirement}
          story={story}
          coverageEvaluation={coverageEvaluation}
        />
      )}
    </>
  )
}
