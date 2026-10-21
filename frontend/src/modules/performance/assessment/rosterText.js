/**
 * The roster a lecturer types or pastes: one student per line, `student id, GitHub login, commit e-mail(s), name`.
 * E-mails may be several, separated by spaces or semicolons. Blank lines and lines starting with # are ignored.
 */
export function parseRoster(text) {
  const students = []
  const problems = []
  const seen = new Set()
  String(text || '').split('\n').forEach((raw, i) => {
    const line = raw.trim()
    if (!line || line.startsWith('#')) return
    const [id, login = '', emails = '', name = ''] = line.split(',').map((s) => s.trim())
    if (!id) return problems.push(`line ${i + 1}: no student id`)
    if (seen.has(id)) return problems.push(`line ${i + 1}: ${id} is listed twice`)
    seen.add(id)
    const list = emails.split(/[\s;]+/).filter(Boolean)
    const bad = list.find((e) => !/^[^@\s]+@[^@\s]+$/.test(e))
    if (bad) return problems.push(`line ${i + 1}: "${bad}" is not an e-mail address`)
    students.push({ student_id: id, logins: login ? [login] : [], emails: list, names: name ? [name] : [] })
  })
  return { students, problems }
}

export function rosterToText(roster = []) {
  return roster.map((s) => [s.student_id, (s.logins || [])[0] || '', (s.emails || []).join(' '), (s.names || [])[0] || ''].join(', ')).join('\n')
}
