// Pure helper shared by the compact WorkflowStepper and the Dashboard's larger
// progress section, so both always agree on what "72% decomposed" means.
import { PROJECT_INFO, getGroupPipelineData } from './data/mockData.js'

export const STAGE_ORDER = ['quality', 'decomposition', 'effort', 'sprint']

// Average completion across all 4 stages for a group, from static seed data.
// Returns null for the live group (PROJECT_INFO.groupId) — its completion is
// shown via its own workspace using the live store, not this static snapshot.
export function getGroupCompletion(group) {
  if (group.id === PROJECT_INFO.groupId) return null
  const stats = computeStageStats(getGroupPipelineData(group))
  return Math.round((stats.quality.percent + stats.decomposition.percent + stats.effort.percent + stats.sprint.percent) / 4)
}

export function computeStageStats({ requirements, userStories, estimations, kanbanTasks }) {
  const totalReq = requirements.length
  const passedReq = requirements.filter((r) => r.status === 'Passing').length
  const qualityPercent = totalReq ? Math.round((passedReq / totalReq) * 100) : 0

  const decomposableReq = requirements.filter((r) => r.status === 'Passing')
  const decomposedReq = decomposableReq.filter((r) => (userStories[r.id] || []).length > 0)
  const decompositionPercent = decomposableReq.length
    ? Math.round((decomposedReq.length / decomposableReq.length) * 100)
    : 0

  const allStories = requirements.flatMap((r) => userStories[r.id] || [])
  const acceptedStories = allStories.filter((s) => s.status === 'Accepted')
  const estimatedStories = acceptedStories.filter((s) => estimations[s.id]?.confirmed)
  const effortPercent = acceptedStories.length
    ? Math.round((estimatedStories.length / acceptedStories.length) * 100)
    : 0

  const totalPoints = kanbanTasks.reduce((s, t) => s + t.points, 0)
  const donePoints = kanbanTasks.filter((t) => t.status === 'Done').reduce((s, t) => s + t.points, 0)
  const sprintPercent = totalPoints ? Math.round((donePoints / totalPoints) * 100) : 0
  const blockedCount = kanbanTasks.filter((t) => t.status === 'Blocked').length

  return {
    quality: {
      key: 'quality',
      label: 'SRS Quality',
      percent: qualityPercent,
      caption: `${passedReq}/${totalReq} requirements passed`,
      complete: totalReq > 0 && passedReq === totalReq,
      to: '/planning/requirements/srs-quality',
    },
    decomposition: {
      key: 'decomposition',
      label: 'Decomposition',
      percent: decompositionPercent,
      caption: decomposableReq.length
        ? `${decomposedReq.length}/${decomposableReq.length} requirements decomposed`
        : 'Waiting on SRS Quality',
      complete: decomposableReq.length > 0 && decomposedReq.length === decomposableReq.length,
      blocked: decomposableReq.length === 0,
      to: '/planning/requirements/decomposition',
    },
    effort: {
      key: 'effort',
      label: 'Effort Estimation',
      percent: effortPercent,
      caption: acceptedStories.length
        ? `${estimatedStories.length}/${acceptedStories.length} stories estimated`
        : 'Waiting on Decomposition',
      complete: acceptedStories.length > 0 && estimatedStories.length === acceptedStories.length,
      blocked: acceptedStories.length === 0,
      to: '/planning/requirements/estimation',
    },
    sprint: {
      key: 'sprint',
      label: 'Sprint Management',
      percent: sprintPercent,
      caption: kanbanTasks.length ? `${PROJECT_INFO.sprintName} active` : 'Waiting on Effort Estimation',
      complete: false,
      blocked: kanbanTasks.length === 0,
      blockedTaskCount: blockedCount,
      to: '/planning/sprint-management',
    },
  }
}

export function getNextAction(stats) {
  const { quality, decomposition, effort, sprint } = stats
  if (quality.percent < 100) {
    const remaining = 100 - quality.percent
    return { text: `Resolve failing requirements in SRS Quality`, to: quality.to, tone: remaining > 50 ? 'danger' : 'warning' }
  }
  if (decomposition.percent < 100 && !decomposition.blocked) {
    return { text: `Decompose the remaining requirements`, to: decomposition.to, tone: 'warning' }
  }
  if (effort.percent < 100 && !effort.blocked) {
    return { text: `Estimate the remaining user stories`, to: effort.to, tone: 'warning' }
  }
  if (sprint.blockedTaskCount > 0) {
    return { text: `${sprint.blockedTaskCount} sprint task(s) are blocked — check DART`, to: sprint.to, tone: 'danger' }
  }
  return { text: `Keep the sprint board moving`, to: sprint.to, tone: 'success' }
}
