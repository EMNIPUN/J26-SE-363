import apiClient from '@/shared/api/apiClient.js'
import { ENDPOINTS } from '@/shared/api/endpoints.js'
import { STUDENTS, GROUPS } from '@/shared/constants/academicScope.js'

/**
 * Standard 7 Activity Factors defined by the Performance Assessment research methodology:
 */
export const DEFAULT_AHP_FACTORS = [
  { id: 'commit_frequency', name: 'Commit Rhythm & Cadence', weight: 0.20, category: 'code' },
  { id: 'code_volume_churn', name: 'Code Churn (Effective Diffs)', weight: 0.18, category: 'code' },
  { id: 'pr_review_rigor', name: 'Pull Request Review Rigor', weight: 0.16, category: 'collaboration' },
  { id: 'task_completion_rate', name: 'Sprint Task Completion', weight: 0.15, category: 'process' },
  { id: 'standup_attendance', name: 'Daily Scrum Participation', weight: 0.12, category: 'process' },
  { id: 'story_point_velocity', name: 'Story Point Velocity', weight: 0.11, category: 'process' },
  { id: 'issue_discussion', name: 'Issue & Architecture Debate', weight: 0.08, category: 'collaboration' },
]

export const MOCK_STUDENT_DETAILED_DATA = {
  'std-it23155534': {
    studentId: 'IT23155534',
    name: 'Sadeesha Sathsara Kumbukage',
    email: 'sadeeshasathsara99@gmail.com',
    roleInGroup: 'Performance Lead & Backend Architect',
    overallScore: 8.8,
    groupParityScore: 9.1,
    atRisk: {
      isAtRisk: false,
      probability: 0.12,
      tier: 'Low',
      trend: 'improving',
      sprintTrajectory: [
        { sprint: 'Sprint 1', probability: 0.22, score: 8.1 },
        { sprint: 'Sprint 2', probability: 0.17, score: 8.4 },
        { sprint: 'Sprint 3', probability: 0.15, score: 8.6 },
        { sprint: 'Sprint 4', probability: 0.12, score: 8.8 },
      ],
      primaryFactor: 'Consistent daily commits & high PR review feedback',
    },
    factors: [
      { id: 'commit_frequency', label: 'Commit Rhythm', studentValue: 92, groupAvg: 78, weight: 0.20 },
      { id: 'code_volume_churn', label: 'Code Churn (Effective Diffs)', studentValue: 88, groupAvg: 80, weight: 0.18 },
      { id: 'pr_review_rigor', label: 'PR Review Rigor', studentValue: 94, groupAvg: 68, weight: 0.16 },
      { id: 'task_completion_rate', label: 'Sprint Task Completion', studentValue: 90, groupAvg: 82, weight: 0.15 },
      { id: 'standup_attendance', label: 'Daily Standups', studentValue: 96, groupAvg: 85, weight: 0.12 },
      { id: 'story_point_velocity', label: 'Story Points Delivered', studentValue: 84, groupAvg: 76, weight: 0.11 },
      { id: 'issue_discussion', label: 'Issue & Design Discussion', studentValue: 82, groupAvg: 72, weight: 0.08 },
    ],
    comprehension: {
      status: 'Verified',
      score: 94,
      verdict: 'High Confidence: Genuine Author',
      transcript: [
        {
          question: 'Can you explain why you used an in-memory token manager instead of localStorage in tokenManager.js?',
          answer: 'localStorage is vulnerable to XSS harvesting from malicious scripts or third-party packages. By keeping tokens in JS closure memory and refresh tokens in HttpOnly cookies, we prevent script access.',
          aiConfidence: 96,
          evaluation: 'Accurate and comprehensive understanding of client-side web application security model.',
        },
        {
          question: 'How does your AHP matrix ensure mathematical consistency when weighting the 7 factors?',
          answer: 'We compute the Principal Eigenvalue (lambda_max) and calculate the Consistency Index CI = (lambda_max - n)/(n - 1). Dividing by the Random Index RI yields the Consistency Ratio CR. If CR < 0.1, the matrix is mathematically consistent.',
          aiConfidence: 98,
          evaluation: 'Flawless recall of Saaty\'s AHP theorem and decision matrix properties.',
        },
      ],
    },
    activityTimeline: [
      { id: 'act-1', type: 'commit', message: 'feat(auth): add RequireRole route guard and 403 page', date: 'Today, 2:30 PM', hash: '30869c2' },
      { id: 'act-2', type: 'review', message: 'Approved PR #5: unified routing architecture', date: 'Yesterday, 6:15 PM', hash: 'PR-005' },
      { id: 'act-3', type: 'standup', message: 'Sprint 4 Standup: completed Keycloak token propagation', date: '2 days ago', status: 'On Track' },
      { id: 'act-4', type: 'commit', message: 'feat(keycloak): add MENTOR custom theme and templates', date: '3 days ago', hash: 'e87f7c7' },
    ],
  },
}

export const performanceService = {
  /**
   * Get executive cohort / group overview metrics
   */
  getOverview: async ({ batchId, groupId }) => {
    try {
      const res = await apiClient.get(ENDPOINTS.PERFORMANCE.OVERVIEW, {
        params: { batch_id: batchId, group_id: groupId },
      })
      return res.data
    } catch {
      // Fallback structured data
      const targetGroup = GROUPS.find((g) => g.id === groupId) || GROUPS[0]
      const groupStudents = STUDENTS.filter((s) => s.groupId === targetGroup.id)
      const atRiskCount = groupStudents.filter((s) => s.riskLevel === 'High' || s.riskLevel === 'Critical').length
      const avgScore = (
        groupStudents.reduce((acc, s) => acc + s.currentScore, 0) / (groupStudents.length || 1)
      ).toFixed(1)

      return {
        batchId,
        groupId,
        groupName: targetGroup.name,
        metrics: {
          totalStudents: groupStudents.length,
          atRiskCount,
          averageScore: Number(avgScore),
          comprehensionRate: 91,
          parityIndex: 0.88,
        },
        students: groupStudents,
        parityDistribution: [
          { group: 'Group 07 (AEGIS)', parityGini: 0.92, status: 'Balanced' },
          { group: 'Group 12 (TrackWise)', parityGini: 0.74, status: 'Moderate' },
          { group: 'Group 03 (NexaPlan)', parityGini: 0.58, status: 'At Risk Imbalance' },
        ],
      }
    }
  },

  /**
   * Get student's personal feedback and factor breakdown
   */
  getMyProgress: async ({ studentId, groupId }) => {
    try {
      const res = await apiClient.get(ENDPOINTS.PERFORMANCE.STUDENT_DETAIL(studentId), {
        params: { group_id: groupId },
      })
      return res.data
    } catch {
      return (
        MOCK_STUDENT_DETAILED_DATA[studentId] ||
        MOCK_STUDENT_DETAILED_DATA['std-it23155534']
      )
    }
  },

  /**
   * Get student roster
   */
  getStudents: async ({ batchId, groupId, specializationId }) => {
    try {
      const res = await apiClient.get(ENDPOINTS.PERFORMANCE.STUDENTS, {
        params: { batch_id: batchId, group_id: groupId, specialization_id: specializationId },
      })
      return res.data
    } catch {
      let filtered = STUDENTS
      if (batchId) filtered = filtered.filter((s) => s.batchId === batchId)
      if (specializationId) filtered = filtered.filter((s) => s.specializationId === specializationId)
      if (groupId && groupId !== 'all') filtered = filtered.filter((s) => s.groupId === groupId)
      return filtered
    }
  },

  /**
   * Get single student forensic details
   */
  getStudentDetail: async (studentId) => {
    try {
      const res = await apiClient.get(ENDPOINTS.PERFORMANCE.STUDENT_DETAIL(studentId))
      return res.data
    } catch {
      return (
        MOCK_STUDENT_DETAILED_DATA[studentId] ||
        MOCK_STUDENT_DETAILED_DATA['std-it23155534']
      )
    }
  },

  /**
   * Trigger automated batch assessment run
   */
  triggerAssessmentRun: async ({ batchId, groupId, sprintNumber }) => {
    try {
      const res = await apiClient.post(ENDPOINTS.PERFORMANCE.ANALYTICS, {
        batch_id: batchId,
        group_id: groupId,
        sprint: sprintNumber,
      })
      return res.data
    } catch {
      return {
        success: true,
        runId: `run-${Date.now()}`,
        status: 'Completed',
        evaluatedCount: 4,
        timestamp: new Date().toISOString(),
      }
    }
  },
}

export default performanceService
