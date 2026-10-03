// In-browser stand-in for the Adaptive AI Tutor backend.
//
// Each function resolves with the same shape the FastAPI endpoint will
// return (apiClient already unwraps response.data) and rejects with an
// ApiError, so hooks and components behave identically once tutorApi.js is
// pointed at the real backend.
//
// Anything a real backend would compute — knowledge gaps, gap status,
// suggestions, the next recommendation, competency updates from activity
// results fetched over MCP — is simulated here so that React never has to.
import ApiError from '@/shared/api/apiError.js'
import {
  activityKindLabels,
  competencySummary,
  conceptCompetencies,
  concepts,
  confidencePolicy,
  defaultReply,
  evidenceTypeByKind,
  evidenceUpdateMessage,
  externalActivities,
  externalPlatform,
  gapPolicy,
  initialConversation,
  keywordReplies,
  learningLoopText,
  levelGuidance,
  levelPolicy,
  performancePolicy,
  quickActionReplies,
  quickActions,
  recommendationText,
  resultChatText,
  suggestionPolicy,
  tutorContext,
  webResources,
} from '../data/mockData.js'
import { MAX_MESSAGE_LENGTH } from '../utils/constants.js'

const LATENCY_MS = 450
const TUTOR_REPLY_LATENCY_MS = 900
const SESSION_STORAGE_KEY = 'selvia-tutor-mock-session'
const SESSION_VERSION = 4

// Written by the stand-in learning app (public/mock-learning-app) when the
// student finishes an activity; read here the way the backend would query
// the external platform through MCP.
const MOCK_PLATFORM_COMPLETIONS_KEY = 'selvia-mock-learning-app-completions'

// For testing error states: set sessionStorage 'selvia-tutor-mock-fail' to a
// comma-separated list of function names (or '*') to make them fail with 500.
const FAILURE_STORAGE_KEY = 'selvia-tutor-mock-fail'

const GAP_STATUS_ORDER = { major_gap: 0, moderate_gap: 1, sufficient: 2 }
const LEVEL_ORDER = { beginner: 0, intermediate: 1, advanced: 2 }

// ---------------------------------------------------------------------------
// Session state (persisted per browser tab so a refresh keeps progress)
// ---------------------------------------------------------------------------

function createSession() {
  return {
    version: SESSION_VERSION,
    competencies: Object.fromEntries(conceptCompetencies.map((c) => [c.conceptId, { ...c }])),
    confidence: competencySummary.confidence,
    evidence: structuredClone(competencySummary.evidence),
    updatedAt: competencySummary.updatedAt,
    activityProgress: {},
    assessments: {},
    conversation: structuredClone(initialConversation),
  }
}

function loadSession() {
  try {
    const saved = JSON.parse(sessionStorage.getItem(SESSION_STORAGE_KEY))
    if (saved?.version === SESSION_VERSION) return saved
  } catch {
    // fall through to a fresh session
  }
  return createSession()
}

let session = loadSession()
let messageSequence = 0

function saveSession() {
  try {
    sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session))
  } catch {
    // storage unavailable; state still lives in memory
  }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function respond(value, latency = LATENCY_MS) {
  return new Promise((resolve) => {
    setTimeout(() => resolve(structuredClone(value)), latency)
  })
}

function fail(message, status = 404) {
  return new Promise((_, reject) => {
    setTimeout(() => reject(new ApiError({ message, status, code: `HTTP_${status}` })), LATENCY_MS)
  })
}

function fill(template, values) {
  return template.replace(/\{(\w+)\}/g, (match, key) => (key in values ? String(values[key]) : match))
}

function conceptRef(conceptId) {
  return { id: conceptId, name: concepts[conceptId]?.name ?? conceptId }
}

function classifyGap(required, current) {
  const gap = Math.max(0, required - current)
  let status = 'sufficient'
  if (gap >= gapPolicy.majorGapMin) status = 'major_gap'
  else if (gap > 0) status = 'moderate_gap'
  return { gap, status }
}

function conceptStanding(conceptId) {
  const { required, current } = session.competencies[conceptId]
  return {
    conceptId,
    name: concepts[conceptId].name,
    description: concepts[conceptId].description,
    required,
    current,
    ...classifyGap(required, current),
  }
}

function standingsBySeverity() {
  return conceptCompetencies
    .map((c) => conceptStanding(c.conceptId))
    .sort((a, b) => GAP_STATUS_ORDER[a.status] - GAP_STATUS_ORDER[b.status] || b.gap - a.gap)
}

function levelFor(competency) {
  if (competency < levelPolicy.beginnerBelow) return 'beginner'
  if (competency < levelPolicy.intermediateBelow) return 'intermediate'
  return 'advanced'
}

// Created on first use so activities added to the catalogue later also work
// in an existing session.
function progressFor(activity) {
  session.activityProgress[activity.id] ??= {
    progress: activity.initialProgress ?? 0,
    lastScore: null,
    syncedCompletions: 0,
    lastAssessmentId: null,
  }
  return session.activityProgress[activity.id]
}

function isActivityDone(activity) {
  const { progress, lastScore } = progressFor(activity)
  return progress >= 100 || lastScore != null
}

// Unfinished first, then items at the student's level, then easiest first.
function bySuggestionOrder(a, b) {
  return (
    Number(a.done) - Number(b.done) ||
    Number(b.matchesLevel) - Number(a.matchesLevel) ||
    LEVEL_ORDER[a.level] - LEVEL_ORDER[b.level]
  )
}

// Activities the suggestion policy allows for a concept, in policy order.
function suggestedActivities(conceptId, status) {
  const policy = suggestionPolicy[status]
  return externalActivities.filter(
    (a) => a.conceptId === conceptId && policy.kinds.includes(a.kind) && Boolean(a.challenge) === Boolean(policy.challengeOnly),
  )
}

// Picks the next activity: the most severe gap, then the first unfinished
// activity in the order its gap status allows (falling back to a retake).
function buildRecommendation() {
  const target = standingsBySeverity().find((s) => s.status !== 'sufficient')
  if (!target) return null

  const level = levelFor(target.current)
  const { kinds } = suggestionPolicy[target.status]
  const candidates = suggestedActivities(target.conceptId, target.status)
  const byKind = (kind) =>
    candidates
      .filter((a) => a.kind === kind)
      .map((a) => ({ ...a, done: isActivityDone(a), matchesLevel: a.level === level }))
      .sort(bySuggestionOrder)

  const ordered = kinds.flatMap(byKind)
  const activity = ordered.find((a) => !a.done) ?? ordered.find((a) => a.kind !== 'learning') ?? ordered[0]
  if (!activity) return null

  const values = {
    concept: target.name,
    current: target.current,
    required: target.required,
    platform: externalPlatform.name,
  }
  const { summary, reasons, actionLabel } = recommendationText

  return {
    id: `rec-${activity.id}`,
    type: activity.kind,
    title: activity.title,
    summary: fill(summary[activity.kind], values),
    conceptId: target.conceptId,
    conceptName: target.name,
    estimatedMinutes: activity.estimatedMinutes,
    reasons: [reasons.largestGap, reasons[target.status], reasons[activity.kind], reasons.evidence].map((r) => fill(r, values)),
    action: { kind: 'activity', targetId: activity.id, label: actionLabel[activity.kind] },
  }
}

function toActivityItem(activity, level, recommendedId) {
  const progress = progressFor(activity)
  return {
    id: activity.id,
    kind: activity.kind,
    title: activity.title,
    summary: activity.summary,
    level: activity.level,
    estimatedMinutes: activity.estimatedMinutes,
    itemCount: activity.itemCount ?? null,
    progress: progress.progress,
    lastScore: progress.lastScore,
    done: isActivityDone(activity),
    matchesLevel: activity.level === level,
    recommended: activity.id === recommendedId,
    challenge: Boolean(activity.challenge),
  }
}

// Every activity of one kind, grouped by concept (most severe gap first).
// Challenges are only offered once a concept is sufficient. `suggested` says
// whether the concept's gap status calls for this kind.
function buildActivityCatalog(kind) {
  const recommendedId = buildRecommendation()?.action?.targetId
  const groups = standingsBySeverity()
    .map((standing) => {
      const policy = suggestionPolicy[standing.status]
      const level = levelFor(standing.current)
      const items = externalActivities
        .filter(
          (a) =>
            a.conceptId === standing.conceptId &&
            a.kind === kind &&
            (!a.challenge || standing.status === 'sufficient'),
        )
        .map((a) => toActivityItem(a, level, recommendedId))
        .sort(bySuggestionOrder)
      return {
        ...standing,
        level,
        suggested: policy.kinds.includes(kind) && !policy.challengeOnly,
        suggestionSummary: policy.summary,
        items,
      }
    })
    .filter((group) => group.items.length > 0)

  return { platform: { name: externalPlatform.name }, kind, concepts: groups }
}

function loopKindStep(kind, target, recommendation) {
  const text = learningLoopText
  const base = { id: kind, label: text[kind].label }
  if (!target) return { ...base, status: 'done', detail: text.kindNone }

  if (!suggestionPolicy[target.status].kinds.includes(kind)) {
    return { ...base, status: 'skipped', detail: text.kindSkipped }
  }
  const activities = suggestedActivities(target.conceptId, target.status).filter((a) => a.kind === kind)
  const done = activities.filter(isActivityDone).length
  let status = 'upcoming'
  if (recommendation?.type === kind) status = 'current'
  else if (activities.length > 0 && done === activities.length) status = 'done'
  return {
    ...base,
    status,
    detail: fill(text.kindDetail, { done, total: activities.length, concept: target.name }),
  }
}

// Where the student is in the adaptive loop. Learning / practice / quiz steps
// describe the concept the Tutor is currently focusing on.
function buildLearningLoop() {
  const text = learningLoopText
  const standings = standingsBySeverity()
  const recommendation = buildRecommendation()
  const target = standings.find((s) => s.status !== 'sufficient') ?? null
  const major = standings.filter((s) => s.status === 'major_gap').length
  const moderate = standings.filter((s) => s.status === 'moderate_gap').length
  const results = Object.values(session.assessments).sort((a, b) => b.completedAt.localeCompare(a.completedAt))
  const latest = results[0]
  const latestChange = latest?.changes.find((c) => c.conceptId === latest.primaryConcept.id) ?? latest?.changes[0]
  const hasEvidence = Boolean(latest)

  return {
    focusConcept: target ? conceptRef(target.conceptId) : null,
    latestAssessmentId: latest?.assessmentId ?? null,
    steps: [
      { id: 'task', label: text.task.label, status: 'done', detail: tutorContext.task.title },
      {
        id: 'required',
        label: text.required.label,
        status: 'done',
        detail: fill(text.required.detail, { count: standings.length }),
      },
      {
        id: 'competency',
        label: text.competency.label,
        status: 'done',
        detail: fill(text.competency.detail, { confidence: session.confidence }),
      },
      {
        id: 'gaps',
        label: text.gaps.label,
        status: 'done',
        detail: target ? fill(text.gaps.detail, { major, moderate }) : text.gaps.noneDetail,
      },
      {
        id: 'recommendation',
        label: text.recommendation.label,
        status: 'done',
        detail: recommendation?.title ?? text.recommendation.noneDetail,
      },
      loopKindStep('learning', target, recommendation),
      loopKindStep('exercise', target, recommendation),
      loopKindStep('quiz', target, recommendation),
      {
        id: 'evidence',
        label: text.evidence.label,
        status: hasEvidence ? 'done' : 'upcoming',
        detail: hasEvidence ? fill(text.evidence.detail, { total: session.evidence.total }) : text.evidence.pendingDetail,
      },
      {
        id: 'updated',
        label: text.updated.label,
        status: hasEvidence ? 'done' : 'upcoming',
        detail: latestChange
          ? fill(text.updated.detail, { concept: latestChange.name, before: latestChange.before, after: latestChange.after })
          : text.updated.pendingDetail,
      },
      {
        id: 'next',
        label: text.next.label,
        status: hasEvidence ? 'done' : 'upcoming',
        detail: hasEvidence ? text.next.detail : text.next.pendingDetail,
      },
    ],
  }
}

function buildResultMessage(result) {
  const changes = result.changes
    .map((c) => fill(resultChatText.change, { concept: c.name, before: c.before, after: c.after }))
    .join('; ')
  const next = result.nextRecommendation
  const content = [
    fill(resultChatText.content, { title: result.title, platform: result.platform, score: result.score, changes: `${changes}.` }),
    next ? fill(resultChatText.next, { title: next.title, concept: next.conceptName }) : resultChatText.done,
  ].join('\n\n')

  messageSequence += 1
  return {
    id: `msg-result-${result.assessmentId}-${messageSequence}`,
    role: 'tutor',
    content,
    createdAt: result.completedAt,
    context: {
      conceptId: result.primaryConcept.id,
      conceptLabel: result.primaryConcept.name,
      recommendedAction: next ? activityKindLabels[next.type] : null,
    },
    ...(next && { action: next.action }),
  }
}

function buildConceptPlan(standing, recommendedId) {
  const policy = suggestionPolicy[standing.status]
  const level = levelFor(standing.current)
  const items = suggestedActivities(standing.conceptId, standing.status)
    .map((a) => toActivityItem(a, level, recommendedId))
    .sort(bySuggestionOrder)

  const learning = items.filter((i) => i.kind === 'learning')
  const practice = policy.kinds.filter((k) => k !== 'learning').flatMap((k) => items.filter((i) => i.kind === k))

  const suggestions = {}
  if (policy.challengeOnly) {
    suggestions.challenge = practice
  } else {
    if (policy.kinds.includes('learning')) suggestions.learning = learning
    suggestions.practice = practice
  }
  if (policy.includeWebResources) {
    suggestions.webResources = webResources
      .filter((r) => r.conceptId === standing.conceptId)
      .map((r) => ({ ...r, matchesLevel: r.level === level }))
      .sort((a, b) => Number(b.matchesLevel) - Number(a.matchesLevel) || LEVEL_ORDER[a.level] - LEVEL_ORDER[b.level])
  }

  return {
    ...standing,
    level,
    levelSummary: levelGuidance[level],
    suggestionSummary: policy.summary,
    suggestions,
  }
}

function buildLaunchUrl(activity) {
  const params = new URLSearchParams({
    activityId: activity.id,
    title: activity.title,
    kind: activity.kind,
    concept: concepts[activity.conceptId].name,
    platform: externalPlatform.name,
  })
  return `${externalPlatform.mockLaunchPath}?${params}`
}

function readPlatformCompletions() {
  try {
    const value = JSON.parse(sessionStorage.getItem(MOCK_PLATFORM_COMPLETIONS_KEY))
    return Array.isArray(value) ? value : []
  } catch {
    return []
  }
}

function withLiveContext(message) {
  if (!message.context) return message
  const competency = session.competencies[message.context.conceptId]?.current ?? null
  return { ...message, context: { ...message.context, competency } }
}

function findKeywordReply(text) {
  const query = text.toLowerCase()
  return keywordReplies.find((reply) => reply.keywords.some((k) => query.includes(k))) ?? defaultReply
}

function performanceBand(score) {
  if (score >= performancePolicy.strongMin) return 'strong'
  if (score >= performancePolicy.developingMin) return 'developing'
  return 'needs_practice'
}

function conceptPerformance(activity) {
  const { score, conceptScores = { [activity.conceptId]: score } } = activity.mockResult
  return Object.entries(conceptScores).map(([conceptId, conceptScore]) => ({
    conceptId,
    name: concepts[conceptId].name,
    score: conceptScore,
    band: performanceBand(conceptScore),
  }))
}

// Applies an activity result reported by the external platform to the
// competency model and stores the before/after snapshot.
function recordActivityResult(activity) {
  const { score, competencyGain } = activity.mockResult
  const assessmentId = `asm-${activity.id}-${Object.keys(session.assessments).length + 1}`

  const changes = Object.entries(competencyGain).map(([conceptId, gain]) => {
    const entry = session.competencies[conceptId]
    const before = entry.current
    const gapBefore = classifyGap(entry.required, before)
    entry.current = Math.min(100, before + gain)
    const gapAfter = classifyGap(entry.required, entry.current)
    return {
      conceptId,
      name: concepts[conceptId].name,
      required: entry.required,
      before,
      after: entry.current,
      gapBefore: gapBefore.gap,
      gapAfter: gapAfter.gap,
      statusBefore: gapBefore.status,
      statusAfter: gapAfter.status,
    }
  })

  const confidenceBefore = session.confidence
  session.confidence = Math.min(confidencePolicy.max, confidenceBefore + confidencePolicy.gainPerActivity)

  const evidenceBefore = session.evidence.total
  session.evidence.total += 1
  const bucket = session.evidence.breakdown.find((b) => b.type === evidenceTypeByKind[activity.kind])
  if (bucket) bucket.count += 1

  const progress = progressFor(activity)
  progress.progress = 100
  progress.lastScore = score
  progress.syncedCompletions += 1
  progress.lastAssessmentId = assessmentId

  session.updatedAt = new Date().toISOString()

  const result = {
    assessmentId,
    activityId: activity.id,
    assessmentType: activity.kind,
    title: activity.title,
    platform: externalPlatform.name,
    status: 'completed',
    completedAt: session.updatedAt,
    score,
    band: performanceBand(score),
    primaryConcept: conceptRef(activity.conceptId),
    conceptPerformance: conceptPerformance(activity),
    changes,
    confidence: { before: confidenceBefore, after: session.confidence },
    evidence: { before: evidenceBefore, after: session.evidence.total },
    message: evidenceUpdateMessage,
    nextRecommendation: buildRecommendation(),
  }

  session.assessments[assessmentId] = result
  session.conversation.push(buildResultMessage(result))
  saveSession()
  return result
}

function shouldSimulateFailure(name) {
  try {
    const targets = (sessionStorage.getItem(FAILURE_STORAGE_KEY) ?? '').split(',').map((s) => s.trim())
    return targets.includes('*') || targets.includes(name)
  } catch {
    return false
  }
}

function withFailureSimulation(api) {
  return Object.fromEntries(
    Object.entries(api).map(([name, fn]) => [
      name,
      (...args) => (shouldSimulateFailure(name) ? fail('Simulated server error (mock).', 500) : fn(...args)),
    ]),
  )
}

// ---------------------------------------------------------------------------
// Public mock API
// ---------------------------------------------------------------------------

export const mockApi = withFailureSimulation({
  getTutorContext() {
    return respond(tutorContext)
  },

  getRequiredKnowledge() {
    return respond(conceptCompetencies.map((c) => conceptStanding(c.conceptId)))
  },

  getCompetencies() {
    return respond({
      confidence: session.confidence,
      updatedAt: session.updatedAt,
      evidence: session.evidence,
      items: conceptCompetencies.map(({ conceptId }) => ({
        conceptId,
        name: concepts[conceptId].name,
        score: session.competencies[conceptId].current,
      })),
    })
  },

  getKnowledgeGaps() {
    return respond(standingsBySeverity())
  },

  getRecommendation() {
    return respond(buildRecommendation())
  },

  getTutorConversation() {
    return respond(session.conversation.map(withLiveContext))
  },

  getQuickActions() {
    return respond(quickActions)
  },

  sendTutorMessage({ message, quickActionId } = {}) {
    const text = message?.trim() ?? ''
    if (text.length > MAX_MESSAGE_LENGTH) {
      return fail(`Messages can be at most ${MAX_MESSAGE_LENGTH} characters.`, 422)
    }

    let replyContent
    let studentText = text
    if (quickActionId) {
      const quickAction = quickActions.find((a) => a.id === quickActionId)
      replyContent = quickActionReplies[quickActionId]
      if (!quickAction || !replyContent) return fail(`Unknown quick action "${quickActionId}".`, 400)
      studentText = text || quickAction.prompt
    } else {
      if (!text) return fail('Message cannot be empty.', 422)
      replyContent = findKeywordReply(text)
    }

    messageSequence += 1
    const now = Date.now()
    const studentMessage = {
      id: `msg-mock-${now}-${messageSequence}-s`,
      role: 'student',
      content: studentText,
      createdAt: new Date(now).toISOString(),
    }
    const reply = {
      id: `msg-mock-${now}-${messageSequence}-t`,
      role: 'tutor',
      createdAt: new Date(now + TUTOR_REPLY_LATENCY_MS).toISOString(),
      ...replyContent,
    }

    session.conversation.push(studentMessage, reply)
    saveSession()
    return respond({ message: studentMessage, reply: withLiveContext(reply) }, TUTOR_REPLY_LATENCY_MS)
  },

  getSprintGuidance() {
    const recommendation = buildRecommendation()
    const recommendedId = recommendation?.action?.targetId
    const plans = standingsBySeverity().map((standing) => buildConceptPlan(standing, recommendedId))
    return respond({
      platform: { name: externalPlatform.name },
      focusConceptId: recommendation?.conceptId ?? null,
      concepts: plans,
    })
  },

  getActivityCatalog(kind) {
    if (!activityKindLabels[kind]) return fail(`Unknown activity kind "${kind}".`, 400)
    return respond(buildActivityCatalog(kind))
  },

  getLearningLoop() {
    return respond(buildLearningLoop())
  },

  getActivity(activityId) {
    const activity = externalActivities.find((a) => a.id === activityId)
    if (!activity) return fail('This activity could not be found on the learning platform.')

    const standing = conceptStanding(activity.conceptId)
    return respond({
      ...toActivityItem(activity, levelFor(standing.current), buildRecommendation()?.action?.targetId),
      concept: conceptRef(activity.conceptId),
      platform: { name: externalPlatform.name },
      launchUrl: buildLaunchUrl(activity),
      lastAssessmentId: progressFor(activity).lastAssessmentId,
    })
  },

  syncActivityResult(activityId) {
    const activity = externalActivities.find((a) => a.id === activityId)
    if (!activity) return fail('This activity could not be found on the learning platform.')

    const progress = progressFor(activity)
    const reportedCompletions = readPlatformCompletions().filter((id) => id === activityId).length
    if (reportedCompletions <= progress.syncedCompletions) {
      return respond({ status: 'in_progress', activityId })
    }

    const result = recordActivityResult(activity)
    return respond({ status: 'completed', activityId, assessmentId: result.assessmentId, result }, TUTOR_REPLY_LATENCY_MS)
  },

  getAssessmentHistory() {
    const history = Object.values(session.assessments)
      .sort((a, b) => b.completedAt.localeCompare(a.completedAt))
      .map((r) => {
        const primaryChange = r.changes.find((c) => c.conceptId === r.primaryConcept.id)
        return {
          assessmentId: r.assessmentId,
          activityId: r.activityId,
          assessmentType: r.assessmentType,
          title: r.title,
          completedAt: r.completedAt,
          score: r.score,
          band: r.band,
          primaryConcept: r.primaryConcept,
          primaryGain: primaryChange ? primaryChange.after - primaryChange.before : 0,
          gapsClosed: r.changes.filter((c) => c.statusBefore !== 'sufficient' && c.statusAfter === 'sufficient').length,
        }
      })
    return respond(history)
  },

  getUpdatedCompetency(assessmentId) {
    const result = session.assessments[assessmentId]
    if (!result) return fail('Assessment result not found. It may belong to an earlier session.')
    return respond(result)
  },

  resetSession() {
    session = createSession()
    saveSession()
    try {
      sessionStorage.removeItem(MOCK_PLATFORM_COMPLETIONS_KEY)
    } catch {
      // storage unavailable
    }
    return respond({ reset: true }, 0)
  },
})

export default mockApi
