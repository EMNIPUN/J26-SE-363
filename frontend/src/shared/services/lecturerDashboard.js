import {
  ARBITRATION_CASES,
  GROUPS,
  PROJECT_INFO,
  QUALITY_GATE_THRESHOLD,
} from '../../modules/planning/data/mockData.js'
import { computeStageStats } from '../../modules/planning/stageStats.js'
import { INITIAL_FINDINGS } from '../../modules/security/data/mockFindings.js'
import { ATTEMPT_HISTORY, ESTIMATES, EVIDENCE } from '../../modules/tutor/data/tutorWorkspace.js'

// Assembles the lecturer dashboard from the records already loaded in the app
// (planning store, security findings, tutor sample, selected-team profiles).
// It counts and groups; it does not score, rank, or predict anything new.
// Swap the body for an API call once a summary endpoint exists.

export const DATA_SOURCE_NOTE =
  'Built from the project records loaded in this app. These are sample records until the backend summary is connected.'

function isEscalated(item) {
  return item.status === 'Open' && (item.category === 'NOVEL' || item.confidenceAgreement < 40)
}

function groupForRequirement(requirementId) {
  return GROUPS.find((group) => group.requirementIds.includes(requirementId))
}

export function buildLecturerSummary({ planning, teamStudents }) {
  const liveGroup = GROUPS.find((group) => group.id === PROJECT_INFO.groupId)
  const stats = computeStageStats(planning)
  const tasks = planning.kanbanTasks
  const blockedTasks = tasks.filter((task) => task.status === 'Blocked')
  const outstandingTasks = tasks.filter((task) => task.status !== 'Done')

  const criticalOpen = INITIAL_FINDINGS.filter(
    (finding) => finding.priority === 'Critical' && finding.status !== 'closed',
  )
  const belowGate = GROUPS.filter((group) => group.qualityGate < QUALITY_GATE_THRESHOLD)
  const inferredStudents = teamStudents.filter(
    (student) => student.riskLevel === 'High' || student.riskProbability >= 0.5,
  )

  const attention = [
    ...ARBITRATION_CASES.filter(isEscalated).map((item) => {
      const group = groupForRequirement(item.requirementId)
      return {
        id: `arb-${item.id}`,
        kind: 'Observed',
        type: 'decision',
        title: item.title,
        detail: `${group?.name || 'A group'} · ${item.requirementId} · agents agree ${item.confidenceAgreement}%`,
        evidence: 'The agents did not converge, so this case was held for you instead of being applied.',
        path: '/planning/instructor/arbitration',
        cta: 'Review case',
        dismissible: false,
      }
    }),
    ...(blockedTasks.length > 0 && liveGroup
      ? [
          {
            id: 'blocked-live',
            kind: 'Observed',
            type: 'blocker',
            title: `${liveGroup.name} has ${blockedTasks.length} blocked sprint task${blockedTasks.length === 1 ? '' : 's'}`,
            detail: blockedTasks.map((task) => task.title).join(' · '),
            evidence: blockedTasks.map((task) => task.blockedReason).filter(Boolean).join(' ') ||
              'Marked Blocked on the sprint board.',
            path: `/planning/instructor/groups/${liveGroup.id}`,
            cta: 'Open group',
            dismissible: false,
          },
        ]
      : []),
    ...belowGate.map((group) => ({
      id: `gate-${group.id}`,
      kind: 'Observed',
      type: 'quality',
      title: `${group.name} is below the quality gate`,
      detail: `${group.project} · recorded score ${group.qualityGate}%`,
      evidence: 'This is the quality-gate score stored on the project record.',
      path: `/planning/instructor/groups/${group.id}`,
      cta: 'Open group',
      dismissible: false,
    })),
    ...(criticalOpen.length > 0
      ? [
          {
            id: 'security-critical',
            kind: 'Observed',
            type: 'security',
            title: `${criticalOpen.length} critical security finding${criticalOpen.length === 1 ? '' : 's'} still open`,
            detail: criticalOpen.map((finding) => finding.title).join(' · '),
            evidence: 'Taken from the findings loaded in the security workspace. Not a new scan.',
            path: '/security/dashboard',
            cta: 'Open findings',
            dismissible: false,
          },
        ]
      : []),
    ...inferredStudents.map((student) => ({
      id: `risk-${student.id}`,
      kind: 'Inferred',
      type: 'support',
      title: `${student.name} may need a check-in`,
      detail: `${student.commitsCount} commits recorded · stand-ups ${student.standupAttendance} · profile risk ${student.riskLevel}`,
      evidence:
        'Inferred from the performance profile for the selected team. Students do not see this note, and it is not a confirmed problem.',
      path: `/performance/students?studentId=${student.id}`,
      cta: 'View evidence',
      dismissible: true,
    })),
  ]

  const statusCounts = GROUPS.reduce((acc, group) => {
    acc[group.status] = (acc[group.status] || 0) + 1
    return acc
  }, {})

  const requirementCounts = planning.requirements.reduce((acc, requirement) => {
    acc[requirement.status] = (acc[requirement.status] || 0) + 1
    return acc
  }, {})

  const findingCounts = INITIAL_FINDINGS.reduce((acc, finding) => {
    acc[finding.status] = (acc[finding.status] || 0) + 1
    return acc
  }, {})

  const learningCounts = ESTIMATES.reduce((acc, estimate) => {
    acc[estimate.status] = (acc[estimate.status] || 0) + 1
    return acc
  }, {})

  const explanationScores = teamStudents.filter((student) => typeof student.comprehensionRate === 'number')

  return {
    attention,
    projects: {
      count: GROUPS.length,
      batches: [...new Set(GROUPS.map((group) => group.batch))],
      students: GROUPS.reduce((sum, group) => sum + (group.members || 0), 0),
      milestone: liveGroup
        ? {
            groupName: liveGroup.name,
            sprintName: PROJECT_INFO.sprintName,
            sprintNumber: PROJECT_INFO.sprintNumber,
            totalSprints: PROJECT_INFO.totalSprints,
            sprintEndDate: PROJECT_INFO.sprintEndDate,
          }
        : null,
    },
    groups: {
      list: [...GROUPS].sort((a, b) => {
        const score = (group) => (group.qualityGate < QUALITY_GATE_THRESHOLD ? 0 : 1) * 100 + group.qualityGate
        return score(a) - score(b)
      }),
      statusCounts,
      teamStudentCount: teamStudents.length,
      inferredCount: inferredStudents.length,
    },
    progress: liveGroup
      ? {
          groupName: liveGroup.name,
          groupId: liveGroup.id,
          stages: [stats.quality, stats.decomposition, stats.effort, stats.sprint],
          outstandingCount: outstandingTasks.length,
          blockedCount: blockedTasks.length,
          totalTasks: tasks.length,
        }
      : null,
    requirements: {
      groupName: liveGroup?.name,
      total: planning.requirements.length,
      passing: requirementCounts.Passing || 0,
      failing: requirementCounts.Failing || 0,
      review: requirementCounts['Needs Review'] || 0,
      groupsBelowGate: belowGate.length,
      threshold: QUALITY_GATE_THRESHOLD,
    },
    security: {
      total: INITIAL_FINDINGS.length,
      open: findingCounts.open || 0,
      review: findingCounts.review || 0,
      learning: findingCounts.learning || 0,
      closed: findingCounts.closed || 0,
      criticalOpen: criticalOpen.length,
    },
    learning: {
      sampleLearnerConcepts: ESTIMATES.length,
      needsAttention: learningCounts['Needs Attention'] || 0,
      developing: learningCounts.Developing || 0,
      insufficient: learningCounts['Insufficient Evidence'] || 0,
      attempts: ATTEMPT_HISTORY.length,
      evidenceRecords: EVIDENCE.length,
      explanationScoresOnFile: explanationScores.length,
      teamStudentCount: teamStudents.length,
    },
  }
}
