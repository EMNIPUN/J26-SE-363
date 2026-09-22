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
} from '../data/mockData.js'

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

let state = {
  requirements: REQUIREMENTS,
  userStories: USER_STORIES_SEED,
  estimations: STORY_ESTIMATIONS_SEED,
  kanbanTasks: KANBAN_SEED,
}

const listeners = new Set()

function setState(patch) {
  state = { ...state, ...patch }
  listeners.forEach((listener) => listener())
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
    setState({ requirements: [...state.requirements, req] })
  },

  rescoreRequirement(id, delta) {
    setState({
      requirements: state.requirements.map((r) => {
        if (r.id !== id) return r
        const dimensionScores = Object.fromEntries(
          Object.entries(r.dimensionScores).map(([k, v]) => [k, Math.min(100, v + delta)]),
        )
        const overallScore = Math.min(
          100,
          Math.round(Object.values(dimensionScores).reduce((a, b) => a + b, 0) / QUALITY_DIMENSIONS.length),
        )
        return { ...r, dimensionScores, overallScore, status: statusFromScore(overallScore) }
      }),
    })
  },

  updateRequirementText(id, patch) {
    setState({ requirements: state.requirements.map((r) => (r.id === id ? { ...r, ...patch } : r)) })
  },

  getStories(reqId) {
    return state.userStories[reqId] || []
  },

  generateStories(reqId, stories) {
    setState({ userStories: { ...state.userStories, [reqId]: [...(state.userStories[reqId] || []), ...stories] } })
  },

  addStory(reqId, story) {
    setState({ userStories: { ...state.userStories, [reqId]: [...(state.userStories[reqId] || []), story] } })
  },

  updateStory(reqId, storyId, patch) {
    setState({
      userStories: {
        ...state.userStories,
        [reqId]: (state.userStories[reqId] || []).map((s) => (s.id === storyId ? { ...s, ...patch } : s)),
      },
    })
  },

  applyAgentSuggestion(reqId, storyId) {
    setState({
      userStories: {
        ...state.userStories,
        [reqId]: (state.userStories[reqId] || []).map((s) => {
          if (s.id !== storyId || !s.agentSuggestion) return s
          return {
            ...s,
            title: s.agentSuggestion.title,
            acceptanceCriteria: s.agentSuggestion.acceptanceCriteria,
            agentSuggestion: null,
          }
        }),
      },
    })
  },

  dismissAgentSuggestion(reqId, storyId) {
    setState({
      userStories: {
        ...state.userStories,
        [reqId]: (state.userStories[reqId] || []).map((s) => (s.id === storyId ? { ...s, agentSuggestion: null } : s)),
      },
    })
  },

  acceptStory(reqId, storyId) {
    setState({
      userStories: {
        ...state.userStories,
        [reqId]: (state.userStories[reqId] || []).map((s) => (s.id === storyId ? { ...s, status: 'Accepted' } : s)),
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

  confirmEstimation(reqId, storyId, title, points) {
    setState({
      estimations: { ...state.estimations, [storyId]: { ...state.estimations[storyId], points, confirmed: true } },
      kanbanTasks: [
        ...state.kanbanTasks,
        { id: nextId('K'), title, requirementId: reqId, storyId, points, status: 'Todo', assigneeId: null },
      ],
    })
  },

  moveKanbanTask(taskId, status) {
    setState({ kanbanTasks: state.kanbanTasks.map((t) => (t.id === taskId ? { ...t, status } : t)) })
  },

  assignKanbanTask(taskId, assigneeId) {
    setState({ kanbanTasks: state.kanbanTasks.map((t) => (t.id === taskId ? { ...t, assigneeId } : t)) })
  },
}
