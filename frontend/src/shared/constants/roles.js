// Internal role keys stay 'instructor' (routes, guards, nav config);
// everything user-facing calls that role "Lecturer".
export const ROLE_LABEL = {
  student: 'Student',
  instructor: 'Lecturer',
  admin: 'Administrator',
}

export const PORTAL_LABEL = {
  student: 'Student Portal',
  instructor: 'Lecturer Portal',
  admin: 'Admin Portal',
}

export function getRoleLabel(role) {
  return ROLE_LABEL[role] || 'User'
}
