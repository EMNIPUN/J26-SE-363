import {
  ASSESSMENTS,
  ATTEMPT_HISTORY,
  CONCEPTS,
  ESTIMATES,
  EVIDENCE,
  EXERCISES,
  MATERIALS,
  PROGRESS_EXPLANATION,
  PROJECT,
  RECOMMENDATION_HISTORY,
  RECOMMENDATIONS,
  ROADMAPS,
  TASKS,
} from '../data/tutorWorkspace.js'

// In-memory stand-in for the tutor API. Estimates are never recalculated here.
// A later integration should replace these functions with tutorService calls.

const wait = (ms = 180) => new Promise((resolve) => setTimeout(resolve, ms))

const session = {
  phase: 'initial',
  exerciseResults: {},
  assessmentResults: {},
  evidence: [],
  recommendationHistory: [],
}

function snapshot() {
  const recommendation = RECOMMENDATIONS[session.phase]
  return {
    project: PROJECT,
    tasks: TASKS,
    concepts: CONCEPTS,
    estimates: ESTIMATES,
    materials: MATERIALS,
    recommendation,
    roadmap: ROADMAPS[session.phase],
    exercises: EXERCISES.map((exercise) => ({
      ...exercise,
      status: session.exerciseResults[exercise.id]?.status || 'Available',
    })),
    assessments: ASSESSMENTS.map((assessment) => ({
      ...assessment,
      status: session.assessmentResults[assessment.id] ? 'Completed this session' : 'Available',
    })),
    attempts: [
      ...Object.values(session.assessmentResults).map((result) => ({
        id: result.id,
        assessmentId: result.assessmentId,
        title: result.title,
        when: 'This session',
        scoreText: result.scoreText,
        conceptIds: result.conceptIds,
        note: 'Quiz score only. Competency estimates were not changed.',
      })),
      ...ATTEMPT_HISTORY,
    ],
    evidence: [...session.evidence, ...EVIDENCE],
    recommendationHistory: [...session.recommendationHistory, ...RECOMMENDATION_HISTORY],
    explanation: PROGRESS_EXPLANATION,
    competencyHistory: [],
  }
}

function conceptBundle(conceptId) {
  const concept = CONCEPTS[conceptId]
  if (!concept) return null
  return {
    ...concept,
    estimate: ESTIMATES.find((item) => item.conceptId === conceptId) || null,
    resources: (concept.resourceIds || []).map((id) => MATERIALS[id]).filter(Boolean),
  }
}

export const tutorWorkspaceService = {
  async getProjectContext() {
    await wait()
    return snapshot()
  },

  async getSprintTasks() {
    await wait()
    return TASKS
  },

  async getRequiredConcepts(taskId) {
    await wait()
    const task = TASKS.find((item) => item.id === taskId)
    if (!task) return []
    return task.conceptIds.map((id) => conceptBundle(id)).filter(Boolean)
  },

  async getRecommendation() {
    await wait()
    return { ...snapshot(), source: 'sample-decision-table' }
  },

  async getExercise(exerciseId) {
    await wait()
    const exercise = EXERCISES.find((item) => item.id === exerciseId)
    if (!exercise) throw new Error('That exercise is not in the sample set.')
    return {
      ...exercise,
      status: session.exerciseResults[exercise.id]?.status || 'Available',
      lastResult: session.exerciseResults[exercise.id] || null,
    }
  },

  async submitExercise(exerciseId, answer) {
    await wait(240)
    const exercise = EXERCISES.find((item) => item.id === exerciseId)
    if (!exercise) throw new Error('That exercise is not in the sample set.')
    const text = String(answer || '')
    const matched =
      exercise.type === 'multiple-choice'
        ? text === exercise.answerId
        : (exercise.acceptedIncludes || []).some((needle) => text.toLowerCase().includes(needle))
    const result = {
      id: `sub-${exerciseId}`,
      exerciseId,
      matched,
      status: matched ? 'Submitted' : 'Needs another try',
      feedback: matched ? exercise.successFeedback : exercise.retryFeedback,
      evaluatedBy: 'sample-check',
      executed: false,
    }
    session.exerciseResults[exerciseId] = result
    if (matched) {
      session.evidence.unshift({
        id: `ev-live-${exerciseId}`,
        kind: 'Exercise submission',
        title: exercise.title,
        when: 'This session',
        detail: 'Sample check passed. Code was not executed. Competency estimate unchanged.',
        conceptId: exercise.conceptId,
      })
      if (exerciseId === 'ex-debug-token' && session.phase === 'initial') {
        session.phase = 'practised'
        session.recommendationHistory.unshift({
          id: 'hist-live-practice',
          intervention: RECOMMENDATIONS.initial.intervention,
          conceptId: 'concept-token',
          reason: RECOMMENDATIONS.initial.explanation,
          completed: true,
          followUp: 'Sample decision table moved to the reassessment. Estimates were not recalculated.',
        })
      }
    }
    return { result, workspace: snapshot() }
  },

  async getAssessment(assessmentId) {
    await wait()
    const assessment = ASSESSMENTS.find((item) => item.id === assessmentId)
    if (!assessment) throw new Error('That assessment is not in the sample set.')
    return {
      ...assessment,
      status: session.assessmentResults[assessment.id] ? 'Completed this session' : 'Available',
      lastResult: session.assessmentResults[assessment.id] || null,
    }
  },

  async submitAssessment(assessmentId, answers) {
    await wait(280)
    const assessment = ASSESSMENTS.find((item) => item.id === assessmentId)
    if (!assessment) throw new Error('That assessment is not in the sample set.')
    const reviews = assessment.questions.map((question) => {
      const selected = answers[question.id]
      const correct = selected === question.answerIndex
      return {
        questionId: question.id,
        conceptId: question.conceptId,
        correct,
        explanation: question.explanation,
        selected,
      }
    })
    const correctCount = reviews.filter((item) => item.correct).length
    const result = {
      id: `attempt-live-${assessmentId}`,
      assessmentId,
      title: assessment.title,
      conceptIds: assessment.conceptIds,
      scoreText: `${correctCount} of ${assessment.questions.length}`,
      correctCount,
      total: assessment.questions.length,
      reviews,
      competencyEstimate: 'Unchanged sample snapshot',
      confidence: 'Not updated from this score',
    }
    session.assessmentResults[assessmentId] = result
    session.evidence.unshift({
      id: `ev-live-${assessmentId}`,
      kind: 'Assessment result',
      title: assessment.title,
      when: 'This session',
      detail: `${result.scoreText}. Stored as quiz evidence only.`,
      conceptId: assessment.conceptIds[0],
    })
    if (assessmentId === 'as-reassess-token' && session.phase === 'practised') {
      session.phase = 'reassessed'
      session.recommendationHistory.unshift({
        id: 'hist-live-reassess',
        intervention: RECOMMENDATIONS.practised.intervention,
        conceptId: 'concept-token',
        reason: RECOMMENDATIONS.practised.explanation,
        completed: true,
        followUp: `${result.scoreText}. Competency percentage was not derived from this score.`,
      })
    }
    return { result, workspace: snapshot() }
  },

  async sendTutorMessage(message) {
    await wait(420)
    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
      throw new Error('You appear to be offline. The sample tutor reply was not prepared.')
    }
    const q = message.toLowerCase()
    const data = snapshot()
    const task = TASKS.find((item) => item.id === data.recommendation.taskId)
    const concept = CONCEPTS[data.recommendation.conceptId]
    let body
    if (q.includes('why') && q.includes('recommend')) {
      body = data.recommendation.explanation
    } else if (q.includes('task') || q.includes('current')) {
      body = `${task.title}: ${task.description}\n\nAcceptance criteria:\n${task.acceptance.map((item) => `- ${item}`).join('\n')}`
    } else if (q.includes('worked') || q.includes('example')) {
      body =
        'A sign-in response can look like this. The middle segment is readable JSON. The third segment is the signature.\n\n```txt\neyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJzdHVkZW50IiwiZXhwIjoxNzAwMDAwMDAwfQ.signature\n```\n\nValidation checks the signature and that exp is still in the future.'
    } else if (q.includes('practice') || q.includes('exercise')) {
      body = `The current sample recommendation is “${data.recommendation.intervention}” for ${concept.label}. Open Practice Exercises to try the debugging item. This reply is not a new decision.`
    } else if (q.includes('debug') || q.includes('code')) {
      body =
        'Compare the handler with the acceptance criteria. If next() runs whenever the header exists, an expired token still gets through.\n\n```js\nconst payload = verify(token, secret)\nif (payload.exp < now) return res.status(401).send("Expired")\n```\n\nThis snippet was not run.'
    } else if (q.includes('simply') || q.includes('explain')) {
      body = `${concept.label}: ${concept.description}\n\nCurrent sample status: ${concept.status}. ${data.recommendation.explanation}`
    } else {
      body = `I can talk through the sample project “${PROJECT.name}”, the task “${task.title}”, or a general software engineering idea.\n\nRight now the sample recommendation is: ${data.recommendation.explanation}`
    }
    return {
      role: 'assistant',
      source: 'sample-reply',
      content: `Sample reply, not from the tutor service.\n\n${body}`,
    }
  },
}

export default tutorWorkspaceService
