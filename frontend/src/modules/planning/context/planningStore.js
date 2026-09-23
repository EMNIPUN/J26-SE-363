// Plain external store (not React state) for the student pipeline.
// DashboardShell keys its <Outlet/> wrapper by location.pathname for the
// route-entrance animation, which remounts every route element — including
// this module's routes — on each navigation. A React Context/useState would
// therefore reset on every click between SRS Quality / Decomposition /
// Estimation / Sprint Management. Living outside the component tree, this
// store survives navigation and only resets on a full page reload.
import {
  REQUIREMENTS,
  USER_STORIES_SEED,
  STORY_ESTIMATIONS_SEED,
  KANBAN_SEED,
  QUALITY_DIMENSIONS,
  ACTIVITY_FEED,
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

function statusFromScore(score) {
  if (score >= 70) return 'Passing'
  if (score >= 50) return 'Needs Review'
  return 'Failing'
}

let idCounter = 2000
function nextId(prefix) {
  idCounter += 1
  return `${prefix}-${idCounter}`
}

const initialHistory = Object.fromEntries(
  REQUIREMENTS.map((r) => [
    r.id,
    [{ version: 1, score: r.overallScore, status: r.status, timestamp: r.lastChecked }],
  ]),
)

const initialActivity = ACTIVITY_FEED.map((a) => ({
  id: nextId('ACT'),
  text: a.text,
  tone: a.tone,
  timestamp: new Date().toISOString(),
}))

let state = {
  requirements: REQUIREMENTS,
  userStories: USER_STORIES_SEED,
  estimations: STORY_ESTIMATIONS_SEED,
  kanbanTasks: KANBAN_SEED,
  requirementHistory: initialHistory,
  activityLog: initialActivity,
  decompositionEvaluations: {},
}

const listeners = new Set()

function setState(patch) {
  state = { ...state, ...patch }
  listeners.forEach((listener) => listener())
}

function withActivity(text, tone = 'primary') {
  return [{ id: nextId('ACT'), text, tone, timestamp: new Date().toISOString() }, ...state.activityLog]
}

export function getSnapshot() {
  return state
}

export function subscribe(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export const actions = {
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

  rescoreRequirement(id, delta) {
    const current = state.requirements.find((r) => r.id === id)
    if (!current) return
    const dimensionScores = Object.fromEntries(
      Object.entries(current.dimensionScores).map(([k, v]) => [k, Math.min(100, v + delta)]),
    )
    const overallScore = Math.min(
      100,
      Math.round(Object.values(dimensionScores).reduce((a, b) => a + b, 0) / QUALITY_DIMENSIONS.length),
    )
    const status = statusFromScore(overallScore)
    const prevHistory = state.requirementHistory[id] || []

    setState({
      requirements: state.requirements.map((r) =>
        r.id === id ? { ...r, dimensionScores, overallScore, status } : r,
      ),
      requirementHistory: {
        ...state.requirementHistory,
        [id]: [
          ...prevHistory,
          { version: prevHistory.length + 1, score: overallScore, status, timestamp: new Date().toISOString() },
        ],
      },
      activityLog: withActivity(
        `Quality Gate re-scored ${id} — now ${overallScore}% (${status}).`,
        status === 'Passing' ? 'success' : status === 'Failing' ? 'danger' : 'warning',
      ),
    })
  },

  updateRequirementText(id, patch) {
    setState({ requirements: state.requirements.map((r) => (r.id === id ? { ...r, ...patch } : r)) })
  },

  getRequirementHistory(id) {
    return state.requirementHistory[id] || []
  },

  getStories(reqId) {
    return state.userStories[reqId] || []
  },

  addStory(reqId, story) {
    setState({
      userStories: { ...state.userStories, [reqId]: [...(state.userStories[reqId] || []), story] },
      // The story set changed, so any prior coverage/INVEST result for this
      // requirement is stale — the agent needs to re-run its analysis.
      decompositionEvaluations: { ...state.decompositionEvaluations, [reqId]: null },
      activityLog: withActivity(`${story.id} written for ${reqId} — ready for decomposition analysis.`, 'primary'),
    })
  },

  // Student edits after AI feedback — clears this story's own INVEST result
  // and invalidates the requirement's coverage analysis, since the set changed.
  updateStoryText(reqId, storyId, patch) {
    setState({
      userStories: {
        ...state.userStories,
        [reqId]: (state.userStories[reqId] || []).map((s) =>
          s.id === storyId ? { ...s, ...patch, investResult: null } : s,
        ),
      },
      decompositionEvaluations: { ...state.decompositionEvaluations, [reqId]: null },
    })
  },

  getDecompositionEvaluation(reqId) {
    return state.decompositionEvaluations[reqId] || null
  },

  // Records one full coverage_analyzer -> invest_validator -> pattern_retriever
  // -> decomposition_scorer -> reflect pass (see decompositionEngine.js) against
  // the requirement's current story set.
  recordDecompositionAnalysis(reqId, result) {
    setState({
      userStories: {
        ...state.userStories,
        [reqId]: (state.userStories[reqId] || []).map((s) => ({
          ...s,
          investResult: result.investResults[s.id] || s.investResult,
        })),
      },
      decompositionEvaluations: { ...state.decompositionEvaluations, [reqId]: result },
      activityLog: withActivity(
        `Decomposition Agent analyzed ${reqId} — coverage ${Math.round(result.coverage * 100)}%, score ${result.score}/100 (${result.verdict}).`,
        result.verdict === 'Validated' ? 'success' : 'warning',
      ),
    })
  },

  acceptStory(reqId, storyId) {
    setState({
      userStories: {
        ...state.userStories,
        [reqId]: (state.userStories[reqId] || []).map((s) => (s.id === storyId ? { ...s, status: 'Accepted' } : s)),
      },
      activityLog: withActivity(`${storyId} accepted — ready for effort estimation.`, 'success'),
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

  addTask(reqId, storyId, title) {
    setState({
      userStories: {
        ...state.userStories,
        [reqId]: (state.userStories[reqId] || []).map((s) =>
          s.id === storyId
            ? { ...s, tasks: [...s.tasks, { id: nextId('T'), title, status: 'Todo', subtasks: [] }] }
            : s,
        ),
      },
    })
  },

  addSubtask(reqId, storyId, taskId, title) {
    setState({
      userStories: {
        ...state.userStories,
        [reqId]: (state.userStories[reqId] || []).map((s) => {
          if (s.id !== storyId) return s
          return {
            ...s,
            tasks: s.tasks.map((t) =>
              t.id === taskId ? { ...t, subtasks: [...t.subtasks, { id: nextId('ST'), title, done: false }] } : t,
            ),
          }
        }),
      },
    })
  },

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
                : { ...t, subtasks: t.subtasks.map((st) => (st.id === subtaskId ? { ...st, done: !st.done } : st)) },
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
      activityLog: withActivity(`${storyId} estimated at ${finalPoints} SP and sent to the sprint backlog.`, 'success'),
    })
  },

  moveKanbanTask(taskId, status) {
    const task = state.kanbanTasks.find((t) => t.id === taskId)
    setState({
      kanbanTasks: state.kanbanTasks.map((t) => (t.id === taskId ? { ...t, status } : t)),
      activityLog:
        status === 'Done' && task ? withActivity(`${task.id} — "${task.title}" marked Done.`, 'success') : state.activityLog,
    })
  },

  assignKanbanTask(taskId, assigneeId) {
    setState({ kanbanTasks: state.kanbanTasks.map((t) => (t.id === taskId ? { ...t, assigneeId } : t)) })
  },
}
