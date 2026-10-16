/**
 * Maps sprint backlog items from the backend into the shape the planning UI uses.
 * Handles both old sprint-task shape (data JSONB) and new backlog item shape (typed columns).
 */

export function mapBacklogItem(raw) {
  if (!raw) return null
  return {
    id: raw.id,
    title: raw.task_description || raw.title || '',
    requirementId: raw.requirement_id || raw.requirement_ref || '',
    storyId: raw.user_story_id || raw.story_ref || '',
    sprintId: raw.sprint_id || null,
    points: raw.final_story_points ?? raw.points ?? 0,
    hours: raw.final_estimated_hours ?? null,
    status: raw.status || 'todo',
    priority: raw.priority || 'medium',
    taskType: raw.task_type || 'story',
    estimationSource: raw.estimation_source || 'student_only',
    assigneeId: raw.assigned_to || null,
    createdAt: raw.created_at || null,
    updatedAt: raw.updated_at || null,
  }
}

export function mapBacklogItems(rawList) {
  return (rawList || []).map(mapBacklogItem).filter(Boolean)
}

// Backward compat exports
export const mapSprintTask = mapBacklogItem
export const mapSprintTasks = mapBacklogItems
