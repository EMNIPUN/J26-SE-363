export function mapSprintTask(raw) {
  if (!raw) return null
  const d = raw.data || {}
  return {
    id: raw.task_ref,
    title: d.title || '',
    requirementId: raw.requirement_ref,
    storyId: raw.story_ref,
    points: d.points ?? 0,
    status: raw.status || 'Todo',
    assigneeId: d.assigneeId || null,
    dueDate: d.dueDate || null,
    blockedReason: d.blockedReason || null,
    dependsOn: d.dependsOn || null,
  }
}

export function mapSprintTasks(rawList) {
  return (rawList || []).map(mapSprintTask).filter(Boolean)
}
