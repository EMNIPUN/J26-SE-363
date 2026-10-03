// Display metadata for enum values sent by the backend. Tones map to the
// shared Badge component (neutral | primary | success | warning | danger).
import {
  BookOpen,
  Briefcase,
  Bug,
  Circle,
  CircleCheck,
  CircleDot,
  CircleMinus,
  ClipboardCheck,
  Code2,
  Dumbbell,
  FileCheck,
  Gauge,
  Lightbulb,
  ListChecks,
  OctagonAlert,
  RefreshCw,
  TrendingUp,
  TriangleAlert,
} from 'lucide-react'

export const TASK_STATUS = {
  todo: { label: 'To Do', tone: 'neutral' },
  in_progress: { label: 'In Progress', tone: 'primary' },
  in_review: { label: 'In Review', tone: 'warning' },
  done: { label: 'Done', tone: 'success' },
  blocked: { label: 'Blocked', tone: 'danger' },
}

export const TASK_PRIORITY = {
  high: { label: 'High', tone: 'warning' },
  medium: { label: 'Medium', tone: 'neutral' },
  low: { label: 'Low', tone: 'neutral' },
}

export const PROJECT_RELEVANCE = {
  high: { label: 'High', tone: 'primary' },
  medium: { label: 'Medium', tone: 'neutral' },
  low: { label: 'Low', tone: 'neutral' },
}

// Key order is the display order (most severe first).
export const GAP_STATUS = {
  major_gap: {
    label: 'Major Gap',
    tone: 'danger',
    icon: OctagonAlert,
    barClass: 'bg-destructive',
    accentClass: 'border-l-destructive',
    textClass: 'text-destructive',
  },
  moderate_gap: {
    label: 'Moderate Gap',
    tone: 'warning',
    icon: TriangleAlert,
    barClass: 'bg-amber-500',
    accentClass: 'border-l-amber-500',
    textClass: 'text-amber-700 dark:text-amber-400',
  },
  sufficient: {
    label: 'Sufficient',
    tone: 'success',
    icon: CircleCheck,
    barClass: 'bg-emerald-500',
    accentClass: 'border-l-emerald-500',
    textClass: 'text-emerald-700 dark:text-emerald-400',
  },
}

// Activity kinds on the external learning platform. Also used as the
// recommendation type. `countLabel` describes an activity's `itemCount`.
export const ACTIVITY_KIND = {
  learning: {
    label: 'Learning Material',
    tone: 'primary',
    icon: BookOpen,
    startLabel: 'Start',
    continueLabel: 'Continue',
    doneLabel: 'Review',
  },
  exercise: {
    label: 'Coding Exercise',
    tone: 'primary',
    icon: Code2,
    countLabel: 'test cases',
    startLabel: 'Start Exercise',
    continueLabel: 'Continue',
    doneLabel: 'Try Again',
  },
  quiz: {
    label: 'Adaptive Quiz',
    tone: 'primary',
    icon: ClipboardCheck,
    countLabel: 'questions',
    startLabel: 'Start Quiz',
    continueLabel: 'Continue',
    doneLabel: 'Retake Quiz',
  },
}

export function getActivityActionLabel(kindMeta, { progress, done }) {
  if (done) return kindMeta.doneLabel
  return progress > 0 ? kindMeta.continueLabel : kindMeta.startLabel
}

// Used for both the student's level and an item's difficulty.
export const LEVEL = {
  beginner: { label: 'Beginner', tone: 'success' },
  intermediate: { label: 'Intermediate', tone: 'primary' },
  advanced: { label: 'Advanced', tone: 'warning' },
}

export const RESOURCE_FORMAT = {
  tutorial: { label: 'Tutorial' },
  article: { label: 'Article' },
  reference: { label: 'Reference' },
  specification: { label: 'Specification' },
  'cheat-sheet': { label: 'Cheat sheet' },
  guide: { label: 'Guide' },
}

// Backend label for a score (overall or per concept).
export const PERFORMANCE_BAND = {
  strong: { label: 'Strong', tone: 'success', barClass: 'bg-emerald-500', strokeClass: 'stroke-emerald-500' },
  developing: { label: 'Developing', tone: 'warning', barClass: 'bg-amber-500', strokeClass: 'stroke-amber-500' },
  needs_practice: { label: 'Needs practice', tone: 'danger', barClass: 'bg-destructive', strokeClass: 'stroke-destructive' },
}

// Status of a step in the adaptive learning loop.
export const LOOP_STEP_STATUS = {
  done: { label: 'Done', icon: CircleCheck, iconClass: 'text-emerald-600 dark:text-emerald-400' },
  current: { label: 'Current step', icon: CircleDot, iconClass: 'text-primary' },
  upcoming: { label: 'Upcoming', icon: Circle, iconClass: 'text-muted-foreground' },
  skipped: { label: 'Not needed', icon: CircleMinus, iconClass: 'text-muted-foreground' },
}

export const LOOP_STEP_ICONS = {
  task: Briefcase,
  required: ListChecks,
  competency: Gauge,
  gaps: TriangleAlert,
  recommendation: Lightbulb,
  learning: BookOpen,
  exercise: Code2,
  quiz: ClipboardCheck,
  evidence: FileCheck,
  updated: TrendingUp,
  next: RefreshCw,
}

export const QUICK_ACTION_ICONS = {
  explain_concept: Lightbulb,
  help_with_task: ListChecks,
  give_practice: Dumbbell,
  generate_quiz: ClipboardCheck,
  debug_code: Bug,
}

export function getMeta(map, key) {
  return map[key] ?? { label: key ?? 'Unknown', tone: 'neutral' }
}
