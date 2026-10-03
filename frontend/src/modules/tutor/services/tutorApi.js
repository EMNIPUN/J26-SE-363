// Public service layer for the Adaptive AI Tutor.
//
// Hooks and components call only this module. Today every function
// delegates to mockApi; when the FastAPI backend is ready each one is
// re-pointed at apiClient + ENDPOINTS.TUTOR without changing its signature
// or return shape. The planned endpoint is noted on each function.
import mockApi from './mockApi.js'

export const tutorApi = {
  /** GET /tutor/context → { project, sprint, task } */
  getTutorContext: () => mockApi.getTutorContext(),

  /** GET /tutor/required-knowledge → [{ conceptId, name, description, required, current, gap, status }] */
  getRequiredKnowledge: () => mockApi.getRequiredKnowledge(),

  /** GET /tutor/competencies → { confidence, updatedAt, evidence, items: [{ conceptId, name, score }] } */
  getCompetencies: () => mockApi.getCompetencies(),

  /** GET /tutor/knowledge-gaps → same shape as required knowledge, ordered by severity */
  getKnowledgeGaps: () => mockApi.getKnowledgeGaps(),

  /** GET /tutor/recommendation → { id, type, title, summary, conceptId, conceptName, reasons, action, ... } */
  getRecommendation: () => mockApi.getRecommendation(),

  /** GET /tutor/conversation → [{ id, role, content, createdAt, context?, action? }] */
  getTutorConversation: () => mockApi.getTutorConversation(),

  /** GET /tutor/quick-actions → [{ id, label, prompt }] */
  getQuickActions: () => mockApi.getQuickActions(),

  /**
   * POST /tutor/messages → { message, reply } (the stored student message and the Tutor's reply)
   * @param {{ message?: string, quickActionId?: string }} payload
   */
  sendTutorMessage: (payload) => mockApi.sendTutorMessage(payload),

  /**
   * GET /tutor/sprint-guidance → { platform, focusConceptId, concepts: [{ ...gap fields, level,
   * levelSummary, suggestionSummary, suggestions: { learning?, practice?, challenge?, webResources? } }] }
   * Which suggestion groups are present depends on the concept's gap status.
   * focusConceptId is null once every requirement is met.
   */
  getSprintGuidance: () => mockApi.getSprintGuidance(),

  /**
   * GET /tutor/activities?kind=exercise|quiz|learning → { platform, kind, concepts: [{ ...gap fields, level,
   * suggested, suggestionSummary, items }] } grouped by concept, most severe gap first
   */
  getActivityCatalog: (kind) => mockApi.getActivityCatalog(kind),

  /**
   * GET /tutor/learning-loop → { focusConcept, latestAssessmentId, steps: [{ id, label, status, detail }] }
   * status: 'done' | 'current' | 'upcoming' | 'skipped'
   */
  getLearningLoop: () => mockApi.getLearningLoop(),

  /**
   * GET /tutor/activities/:activityId → activity details + launchUrl for the external
   * learning platform (the backend resolves the URL through MCP).
   */
  getActivity: (activityId) => mockApi.getActivity(activityId),

  /**
   * POST /tutor/activities/:activityId/sync — the backend pulls the latest result from the
   * external platform through MCP and records it as learning evidence.
   * → { status: 'in_progress' } | { status: 'completed', assessmentId, result }
   */
  syncActivityResult: (activityId) => mockApi.syncActivityResult(activityId),

  /**
   * GET /tutor/assessments → completed activities, newest first:
   * [{ assessmentId, activityId, assessmentType, title, completedAt, score, band, primaryConcept, primaryGain, gapsClosed }]
   */
  getAssessmentHistory: () => mockApi.getAssessmentHistory(),

  /**
   * GET /tutor/assessments/:assessmentId/competency-update → { score, band, conceptPerformance,
   * changes (before/after competency and gap per concept), confidence, evidence, message, nextRecommendation, ... }
   */
  getUpdatedCompetency: (assessmentId) => mockApi.getUpdatedCompetency(assessmentId),
}

export default tutorApi
