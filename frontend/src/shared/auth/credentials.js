// Dummy accounts for the prototype — there is no real backend yet.
// Each role has one fixed demo login so any teammate can log in and see
// that role's dashboard without needing a real auth service.
export const DEMO_ACCOUNTS = [
  {
    role: 'student',
    name: 'Nimal Perera',
    email: 'student@lms.edu',
    password: 'student123',
  },
  {
    role: 'instructor',
    name: 'Dr. Amara Silva',
    email: 'instructor@lms.edu',
    password: 'instructor123',
  },
  {
    role: 'admin',
    name: 'System Admin',
    email: 'admin@lms.edu',
    password: 'admin123',
  },
]

export function findAccount(email, password) {
  return DEMO_ACCOUNTS.find(
    (acc) => acc.email.toLowerCase() === email.trim().toLowerCase() && acc.password === password,
  )
}
