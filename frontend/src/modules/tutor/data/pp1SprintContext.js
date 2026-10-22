/**
 * PP1 demo sprint context aligned with AI Backend sprint fixtures
 * (P-ETCS / sprint-01). Used so Sprint context details are visible
 * before analysis runs. Every task is assigned to 36841e50-ac3f-4bf2-952e-08eb4315becd.
 */
export const PP1_SPRINT_CONTEXT = {
  projectId: 'P-ETCS',
  projectName: 'Ethical Tourism Certification System Backend',
  sprintId: 'sprint-01',
  sprintName: 'Foundation and Backend Architecture',
  sprintGoal:
    'Establish the Express/Mongo feature-module architecture, shared common utilities, and initial certificate lifecycle API surface.',
  courseCode: 'SE3020',
  tasks: [
    {
      task_id: 'task-s1-initial-repo',
      title: 'Initialize backend repository',
      description:
        'Create the initial commit and repository baseline for the ethical tourism certification backend.',
      status: 'done',
      priority: 'high',
      assignedToYou: true,
      acceptance_criteria: [
        'Repository exists with initial commit',
        'Project can be cloned and opened by the team',
      ],
    },
    {
      task_id: 'task-s1-architecture',
      title: 'Establish feature-based backend architecture',
      description:
        'Scaffold core modules, common utilities, middleware patterns, and test infrastructure.',
      status: 'done',
      priority: 'high',
      assignedToYou: true,
      acceptance_criteria: [
        'common/, modules/, and app entrypoints exist',
        'Shared utilities and middleware layout are in place',
        'Test infrastructure folder structure is ready',
      ],
    },
    {
      task_id: 'task-s1-lifecycle-apis',
      title: 'Implement initial certificate lifecycle APIs',
      description: 'Deliver the first certificate lifecycle endpoints.',
      status: 'done',
      priority: 'high',
      assignedToYou: true,
      acceptance_criteria: [
        'Lifecycle routes are mounted under /certification',
        'Basic issue/get certificate operations work',
      ],
    },
    {
      task_id: 'task-s1-common-models',
      title: 'Define shared User and Hotel models',
      description:
        'Place shared Mongoose models in common/models for use across certification, audit, and search modules.',
      status: 'done',
      priority: 'medium',
      assignedToYou: true,
      acceptance_criteria: [
        'User model supports Admin, Hotel Owner, Auditor, Tourist roles',
        'Hotel model is reusable across modules',
      ],
    },
  ],
}

export function tasksAssignedToStudent() {
  return PP1_SPRINT_CONTEXT.tasks.filter((task) => task.assignedToYou)
}
