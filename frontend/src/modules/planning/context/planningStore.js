// Plain external store (not React state) for the student pipeline.
// DashboardShell keys its <Outlet/> wrapper by location.pathname for the
// route-entrance animation, which remounts every route element — including
// this module's routes — on each navigation. A React Context/useState would
// therefore reset on every click between SRS Quality / Decomposition /
// Estimation / Sprint Management. Living outside the component tree, this
// store survives navigation and only resets on a full page reload.
import {
  PROJECT_INFO,
} from '../data/mockData.js'

// Spreads newly-created Kanban tasks across the sprint window so they show up
// on the instructor's Gantt timeline without asking the student to pick a date.
function nextDueDate(existingCount) {
  const start = new Date(PROJECT_INFO.sprintStartDate).getTime()
  const end = new Date(PROJECT_INFO.sprintEndDate).getTime()
  const span = Math.max(end - start, 1)
  const slot = ((existingCount % 6) + 1) / 7
  return new Date(start + span * slot).toISOString().slice(0, 10)
}

let idCounter = 2000
function nextId(prefix) {
  idCounter += 1
  return `${prefix}-${idCounter}`
}

// Content signature for a task list (recursive over subtasks), deliberately
// excluding the embedded `validation` field so a validation run itself never
// looks like a task edit — used by loadStories to detect real task changes.
function tasksSignature(tasks) {
  return JSON.stringify(
    (tasks || []).map((t) => [
      t.id, t.title, t.description || '', t.status, tasksSignature(t.subtasks),
    ]),
  )
}

const FINALIZED_STORAGE_KEY = 'selvia_finalized_requirements'
const FINALIZED_DECOMP_STORAGE_KEY = 'selvia_finalized_decompositions'
const CACHED_REQUIREMENTS_KEY = 'selvia_cached_requirements'
const CACHED_USER_STORIES_KEY = 'selvia_cached_user_stories'
const CACHED_DECOMP_EVALUATIONS_KEY = 'selvia_cached_decomp_evaluations'
const CACHED_DECOMP_HISTORY_KEY = 'selvia_cached_decomp_history'
const CACHED_TASK_VALIDATIONS_KEY = 'selvia_cached_task_validations'

function readFinalizedIds() {
  try {
    const raw = localStorage.getItem(FINALIZED_STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveFinalizedIds(ids) {
  try {
    localStorage.setItem(FINALIZED_STORAGE_KEY, JSON.stringify(ids))
  } catch {
    // ignore
  }
}

function readFinalizedDecompIds() {
  try {
    const raw = localStorage.getItem(FINALIZED_DECOMP_STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

function saveFinalizedDecompIds(ids) {
  try {
    localStorage.setItem(FINALIZED_DECOMP_STORAGE_KEY, JSON.stringify(ids))
  } catch {
    // ignore
  }
}

function readCachedRequirements() {
  try {
    const raw = localStorage.getItem(CACHED_REQUIREMENTS_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed) || parsed.length === 0) return []
    const finalizedSet = new Set(readFinalizedIds())
    const finalizedDecompSet = new Set(readFinalizedDecompIds())
    return parsed.map((r) => ({
      ...r,
      finalized: finalizedSet.has(r.id),
      decompUnlocked: finalizedSet.has(r.id),
      decompFinalized: finalizedDecompSet.has(r.id),
    }))
  } catch {
    return []
  }
}

function saveCachedRequirements(reqs) {
  try {
    if (Array.isArray(reqs)) {
      localStorage.setItem(CACHED_REQUIREMENTS_KEY, JSON.stringify(reqs))
    }
  } catch {
    // ignore
  }
}

function readCachedUserStories() {
  try {
    const raw = localStorage.getItem(CACHED_USER_STORIES_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveCachedUserStories(stories) {
  try {
    if (stories && typeof stories === 'object') {
      localStorage.setItem(CACHED_USER_STORIES_KEY, JSON.stringify(stories))
    }
  } catch {
    // ignore
  }
}

function readCachedDecompEvaluations() {
  try {
    const raw = localStorage.getItem(CACHED_DECOMP_EVALUATIONS_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveCachedDecompEvaluations(evaluations) {
  try {
    if (evaluations && typeof evaluations === 'object') {
      localStorage.setItem(CACHED_DECOMP_EVALUATIONS_KEY, JSON.stringify(evaluations))
    }
  } catch {
    // ignore
  }
}

function readCachedDecompHistory() {
  try {
    const raw = localStorage.getItem(CACHED_DECOMP_HISTORY_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveCachedDecompHistory(history) {
  try {
    if (history && typeof history === 'object') {
      localStorage.setItem(CACHED_DECOMP_HISTORY_KEY, JSON.stringify(history))
    }
  } catch {
    // ignore
  }
}

function readCachedTaskValidations() {
  try {
    const raw = localStorage.getItem(CACHED_TASK_VALIDATIONS_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveCachedTaskValidations(evaluations) {
  try {
    if (evaluations && typeof evaluations === 'object') {
      localStorage.setItem(CACHED_TASK_VALIDATIONS_KEY, JSON.stringify(evaluations))
    }
  } catch {
    // ignore
  }
}

const initialRequirements = readCachedRequirements()
const initialStories = readCachedUserStories()
const initialDecompEvaluations = readCachedDecompEvaluations()
const initialDecompHistory = readCachedDecompHistory()
const initialTaskValidations = readCachedTaskValidations()

// Synchronously hydrated from local cache on initial load/reload so the UI never
// flashes 0% or empty state before background network queries resolve.
let state = {
  requirements: initialRequirements,
  userStories: initialStories,
  estimations: {},
  kanbanTasks: [],
  requirementHistory: Object.fromEntries(
    initialRequirements.map((r) => [
      r.id,
      [{ version: 1, score: r.overallScore, status: r.status, timestamp: r.lastChecked }],
    ]),
  ),
  decompositionHistory: initialDecompHistory,
  activityLog: [],
  decompositionEvaluations: initialDecompEvaluations,
  taskValidationEvaluations: initialTaskValidations,
}

const listeners = new Set()

function setState(patch) {
  state = { ...state, ...patch }
  if (patch.requirements) {
    saveCachedRequirements(state.requirements)
  }
  if (patch.userStories) {
    saveCachedUserStories(state.userStories)
  }
  if (patch.decompositionEvaluations) {
    saveCachedDecompEvaluations(state.decompositionEvaluations)
  }
  if (patch.decompositionHistory) {
    saveCachedDecompHistory(state.decompositionHistory)
  }
  if (patch.taskValidationEvaluations) {
    saveCachedTaskValidations(state.taskValidationEvaluations)
  }
  listeners.forEach((listener) => listener())
}

function withActivity(text, tone = 'primary', category = 'ai') {
  return [{ id: nextId('ACT'), text, tone, category, timestamp: new Date().toISOString() }, ...state.activityLog]
}

export function getSnapshot() {
  return state
}

export function subscribe(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export const actions = {
  // Replace the whole requirement set with results from the real backend
  // (e.g. after an SRS upload). Resets per-requirement history to version 1.
  loadRequirements(reqs) {
    if (!reqs || reqs.length === 0) return
    const finalizedSet = new Set(readFinalizedIds())
    const finalizedDecompSet = new Set(readFinalizedDecompIds())
    const hydrated = reqs.map((r) => ({
      ...r,
      finalized: finalizedSet.has(r.id),
      decompUnlocked: finalizedSet.has(r.id),
      decompFinalized: finalizedDecompSet.has(r.id),
    }))
    setState({
      requirements: hydrated,
      requirementHistory: Object.fromEntries(
        hydrated.map((r) => [r.id, [{ version: 1, score: r.overallScore, status: r.status, timestamp: r.lastChecked }]]),
      ),
      activityLog: withActivity(
        `SRS processed — ${hydrated.length} requirement(s) extracted and scored by the Quality Analysis agent.`,
        'primary',
      ),
    })
  },

  finalizeRequirement(id) {
    const set = new Set(readFinalizedIds())
    set.add(id)
    saveFinalizedIds(Array.from(set))

    setState({
      requirements: state.requirements.map((r) =>
        r.id === id ? { ...r, finalized: true, decompUnlocked: true } : r,
      ),
      activityLog: withActivity(
        `Requirement ${id} finalized and unlocked for Backlog Decomposition.`,
        'success',
      ),
    })
  },

  finalizeDecomposition(id) {
    const set = new Set(readFinalizedDecompIds())
    set.add(id)
    saveFinalizedDecompIds(Array.from(set))

    setState({
      requirements: state.requirements.map((r) =>
        r.id === id ? { ...r, decompFinalized: true } : r,
      ),
      userStories: {
        ...state.userStories,
        [id]: (state.userStories[id] || []).map((s) => ({ ...s, status: 'Accepted' })),
      },
      activityLog: withActivity(
        `Requirement ${id} decomposition finalized & locked — ready for Effort Estimation.`,
        'success',
      ),
    })
  },

  addRequirement(req) {
    setState({
      requirements: [...state.requirements, req],
      requirementHistory: {
        ...state.requirementHistory,
        [req.id]: [{ version: 1, score: req.overallScore, status: req.status, timestamp: req.lastChecked }],
      },
      activityLog: withActivity(`${req.id} added and scored by the Quality Analysis agent.`, 'primary'),
    })
  },

  // Write an ABSOLUTE backend re-score onto an existing requirement (replaces the
  // scores — never adds a delta), clears the stale flag, and appends a history
  // version. This is the real fix for the "score keeps climbing" bug.
  applyRequirementResult(id, mapped) {
    const prevHistory = state.requirementHistory[id] || []
    setState({
      requirements: state.requirements.map((r) =>
        r.id === id ? { ...r, ...mapped, stale: false } : r,
      ),
      requirementHistory: {
        ...state.requirementHistory,
        [id]: [
          ...prevHistory,
          {
            version: prevHistory.length + 1,
            score: mapped.overallScore,
            status: mapped.status,
            timestamp: mapped.lastChecked || new Date().toISOString(),
          },
        ],
      },
      activityLog: withActivity(
        `Quality Gate re-scored ${id} — now ${mapped.overallScore}% (${mapped.status}).`,
        mapped.status === 'Passing' ? 'success' : mapped.status === 'Failing' ? 'danger' : 'warning',
      ),
    })
  },

  // Local edit of the requirement text — marks it stale so the UI prompts a re-check.
  updateRequirementText(id, patch) {
    setState({
      requirements: state.requirements.map((r) => (r.id === id ? { ...r, ...patch, stale: true } : r)),
    })
  },

  getRequirementHistory(id) {
    return state.requirementHistory[id] || []
  },

  // Shallow-merges each incoming story onto the existing one (by id) rather
  // than replacing the array wholesale, so a stories-query resolving after
  // the decomposition-results query can't wipe out investResult/stale badges
  // the latter already attached (defense-in-depth; the server-side adapter
  // fix is the primary guard — see adapters/decomposition.js).
  //
  // Also detects task-set changes per story (content, not just reference) and
  // flags that story's task-validation evaluation stale — this is the single
  // place every task create/edit/delete mutation funnels through (they all
  // invalidate ['planning-stories'] and re-hydrate via this function), so it
  // catches staleness regardless of which mutation caused it.
  loadStories(map) {
    if (!map || Object.keys(map).length === 0) return
    const merged = { ...state.userStories }
    const changedTaskStoryIds = new Set()
    for (const [reqId, incomingStories] of Object.entries(map)) {
      const existingById = new Map((merged[reqId] || []).map((s) => [s.id, s]))
      merged[reqId] = incomingStories.map((incoming) => {
        const existing = existingById.get(incoming.id)
        if (existing && tasksSignature(existing.tasks) !== tasksSignature(incoming.tasks)) {
          changedTaskStoryIds.add(incoming.id)
        }
        return existing
          ? { ...existing, ...incoming, investResult: incoming.investResult ?? existing.investResult }
          : incoming
      })
    }
    const patch = { userStories: merged }
    if (changedTaskStoryIds.size > 0) {
      const nextEvaluations = { ...state.taskValidationEvaluations }
      for (const storyId of changedTaskStoryIds) {
        if (nextEvaluations[storyId]) {
          nextEvaluations[storyId] = { ...nextEvaluations[storyId], stale: true }
        }
      }
      patch.taskValidationEvaluations = nextEvaluations
    }
    setState(patch)
  },

  loadEstimations(map) {
    if (!map || Object.keys(map).length === 0) return
    setState({ estimations: { ...state.estimations, ...map } })
  },

  loadKanbanTasks(tasks) {
    if (!tasks) return
    setState({ kanbanTasks: tasks })
  },

  getStories(reqId) {
    return state.userStories[reqId] || []
  },

  // The story set changed, so any prior coverage/INVEST result for this
  // requirement is now STALE — flag it (keep all its data) rather than
  // deleting it, so the student still sees their last feedback instead of
  // the evidence panel silently vanishing. The agent needs to re-run its
  // analysis to clear the stale flag.
  addStory(reqId, story) {
    setState({
      userStories: { ...state.userStories, [reqId]: [...(state.userStories[reqId] || []), story] },
      decompositionEvaluations: {
        ...state.decompositionEvaluations,
        [reqId]: state.decompositionEvaluations[reqId]
          ? { ...state.decompositionEvaluations[reqId], stale: true }
          : null,
      },
      activityLog: withActivity(`${story.id} written for ${reqId} — ready for decomposition analysis.`, 'primary', 'student'),
    })
  },

  // Student edits after AI feedback — keeps the story's own INVEST result
  // visible (marked editedSinceAnalysis instead of wiped) and flags the
  // requirement's evaluation stale, since the set changed.
  updateStoryText(reqId, storyId, patch) {
    setState({
      userStories: {
        ...state.userStories,
        [reqId]: (state.userStories[reqId] || []).map((s) =>
          s.id === storyId ? { ...s, ...patch, editedSinceAnalysis: true } : s,
        ),
      },
      decompositionEvaluations: {
        ...state.decompositionEvaluations,
        [reqId]: state.decompositionEvaluations[reqId]
          ? { ...state.decompositionEvaluations[reqId], stale: true }
          : null,
      },
    })
  },

  getDecompositionEvaluation(reqId) {
    return state.decompositionEvaluations[reqId] || null
  },

  // Records one full decomposition agent pass against the requirement's
  // current story set. A fresh result is never stale, and clears each
  // story's own editedSinceAnalysis flag since this result reflects the
  // current story text.
  recordDecompositionAnalysis(reqId, result) {
    const prevHistory = state.decompositionHistory[reqId] || []
    const fingerprint = (entry) => [
      entry.timestamp || '',
      entry.readiness || '',
      entry.score ?? '',
      entry.analysisFailed ? 'failed' : 'complete',
    ].join('|')
    const newEntry = {
      version: prevHistory.length + 1,
      score: result.score,
      coverage: result.coverage,
      readiness: result.readiness,
      readinessReason: result.readinessReason,
      gateStatus: result.gateStatus, // legacy, unused by the UI
      qualityBand: result.qualityBand,
      analysisFailed: Boolean(result.analysisFailed),
      failureReason: result.failureReason || null,
      timestamp: result.evaluatedAt || new Date().toISOString(),
      summary: (result.studentFeedback || [])[0] || '',
    }
    // A completed POST invalidates and refetches the latest-results query.
    // Both paths carry the same persisted assessed_at timestamp, so only one
    // history entry must be retained for that single database assessment.
    const newFingerprint = fingerprint(newEntry)
    const uniqueHistory = prevHistory.filter((entry, index, entries) => (
      fingerprint(entry) !== newFingerprint
      && entries.findIndex((candidate) => fingerprint(candidate) === fingerprint(entry)) === index
    ))
    newEntry.version = uniqueHistory.length + 1
    setState({
      userStories: {
        ...state.userStories,
        [reqId]: (state.userStories[reqId] || []).map((s) => ({
          ...s,
          investResult: result.investResults[s.id] || s.investResult,
          editedSinceAnalysis: false,
        })),
      },
      decompositionEvaluations: {
        ...state.decompositionEvaluations,
        [reqId]: { ...result, stale: false },
      },
      decompositionHistory: {
        ...state.decompositionHistory,
        [reqId]: [newEntry, ...uniqueHistory],
      },
      activityLog: withActivity(
        result.analysisFailed
          ? `Decomposition analysis for ${reqId} could not be completed — system error, please re-run.`
          : `Decomposition Agent analyzed ${reqId} — ${result.readiness}, score ${result.score}/4 (${result.qualityBand}).`,
        result.analysisFailed ? 'danger' : result.readiness === 'Ready' ? 'success' : 'warning',
      ),
    })
  },

  getDecompositionHistory(reqId) {
    return state.decompositionHistory[reqId] || []
  },

  getTaskValidationEvaluation(storyId) {
    return state.taskValidationEvaluations[storyId] || null
  },

  // Records one task-validation agent pass against a story's current task
  // set. Mirrors recordDecompositionAnalysis: a fresh result is never stale,
  // and nothing about the story's tasks is ever discarded regardless of the
  // readiness tier or score.
  recordTaskValidation(storyId, result) {
    setState({
      taskValidationEvaluations: {
        ...state.taskValidationEvaluations,
        [storyId]: { ...result, stale: false },
      },
      activityLog: withActivity(
        result.analysisFailed
          ? `Task validation for ${storyId} could not be completed — system error, please re-run.`
          : `Task Validation Agent analyzed ${storyId}'s tasks — ${result.readiness}, score ${result.score}/4 (${result.qualityBand}).`,
        result.analysisFailed ? 'danger' : result.readiness === 'Valid' ? 'success' : 'warning',
      ),
    })
  },

  deleteStory(reqId, storyId) {
    setState({
      userStories: {
        ...state.userStories,
        [reqId]: (state.userStories[reqId] || []).filter((s) => s.id !== storyId),
      },
      decompositionEvaluations: {
        ...state.decompositionEvaluations,
        [reqId]: state.decompositionEvaluations[reqId]
          ? { ...state.decompositionEvaluations[reqId], stale: true }
          : null,
      },
      activityLog: withActivity(`Story ${storyId} deleted from ${reqId}.`, 'primary', 'student'),
    })
  },

  acceptStory(reqId, storyId) {
    setState({
      userStories: {
        ...state.userStories,
        [reqId]: (state.userStories[reqId] || []).map((s) => (s.id === storyId ? { ...s, status: 'Accepted' } : s)),
      },
      activityLog: withActivity(`${storyId} accepted — ready for effort estimation.`, 'success', 'student'),
    })
  },

  addBug(reqId, storyId, title, severity) {
    setState({
      userStories: {
        ...state.userStories,
        [reqId]: (state.userStories[reqId] || []).map((s) =>
          s.id === storyId
            ? { ...s, bugs: [...(s.bugs || []), { id: nextId('BUG'), title, severity, status: 'Open' }] }
            : s,
        ),
      },
    })
  },

  toggleBugStatus(reqId, storyId, bugId) {
    setState({
      userStories: {
        ...state.userStories,
        [reqId]: (state.userStories[reqId] || []).map((s) => {
          if (s.id !== storyId) return s
          return {
            ...s,
            bugs: (s.bugs || []).map((b) => (b.id === bugId ? { ...b, status: b.status === 'Open' ? 'Fixed' : 'Open' } : b)),
          }
        }),
      },
    })
  },

  // Subtasks are just UserStoryTask rows with a parent_task_id, so "done" is
  // status === 'done' (the real backend status enum), not a separate local
  // boolean — this optimistically mirrors what the PATCH .../tasks/{id} call
  // just persisted (see the TaskRow call site).
  toggleSubtask(reqId, storyId, taskId, subtaskId) {
    setState({
      userStories: {
        ...state.userStories,
        [reqId]: (state.userStories[reqId] || []).map((s) => {
          if (s.id !== storyId) return s
          return {
            ...s,
            tasks: s.tasks.map((t) =>
              t.id !== taskId
                ? t
                : {
                    ...t,
                    subtasks: t.subtasks.map((st) =>
                      st.id === subtaskId
                        ? { ...st, status: st.status === 'done' ? 'todo' : 'done' }
                        : st,
                    ),
                  },
            ),
          }
        }),
      },
    })
  },

  setEstimation(storyId, patch) {
    setState({ estimations: { ...state.estimations, [storyId]: { ...(state.estimations[storyId] || {}), ...patch } } })
  },

  confirmEstimation(reqId, storyId, title, finalPoints, reason) {
    setState({
      estimations: {
        ...state.estimations,
        [storyId]: { ...state.estimations[storyId], finalPoints, reason: reason || '', confirmed: true },
      },
      kanbanTasks: [
        ...state.kanbanTasks,
        {
          id: nextId('K'),
          title,
          requirementId: reqId,
          storyId,
          points: finalPoints,
          status: 'Todo',
          assigneeId: null,
          dueDate: nextDueDate(state.kanbanTasks.length),
        },
      ],
      activityLog: withActivity(`${storyId} estimated at ${finalPoints} SP and sent to the sprint backlog.`, 'success', 'student'),
    })
  },

  moveKanbanTask(taskId, status) {
    const task = state.kanbanTasks.find((t) => t.id === taskId)
    setState({
      kanbanTasks: state.kanbanTasks.map((t) => (t.id === taskId ? { ...t, status } : t)),
      activityLog:
        status === 'Done' && task ? withActivity(`${task.id} — "${task.title}" marked Done.`, 'success', 'sprint') : state.activityLog,
    })
  },

  assignKanbanTask(taskId, assigneeId) {
    setState({ kanbanTasks: state.kanbanTasks.map((t) => (t.id === taskId ? { ...t, assigneeId } : t)) })
  },
}
