import { describe, expect, it } from 'vitest'
import { parseRoster, rosterToText } from './rosterText.js'

describe('parseRoster', () => {
  it('reads id, login, e-mails and name and skips comments and blank lines', () => {
    const { students, problems } = parseRoster('# team\nSTU-1, amy-gh, amy@x.org amy2@y.org, Amy A\n\nSTU-2, bob-gh\n')
    expect(problems).toEqual([])
    expect(students).toEqual([
      { student_id: 'STU-1', logins: ['amy-gh'], emails: ['amy@x.org', 'amy2@y.org'], names: ['Amy A'] },
      { student_id: 'STU-2', logins: ['bob-gh'], emails: [], names: [] },
    ])
  })

  it('reports duplicates, missing ids and bad e-mails instead of guessing', () => {
    const { students, problems } = parseRoster('STU-1, a, a@x.org\nSTU-1, b\n, c\nSTU-3, d, not-an-email')
    expect(students.map((s) => s.student_id)).toEqual(['STU-1'])
    expect(problems).toEqual(['line 2: STU-1 is listed twice', 'line 3: no student id', 'line 4: "not-an-email" is not an e-mail address'])
  })

  it('round-trips', () => {
    const { students } = parseRoster('STU-1, amy-gh, amy@x.org, Amy A')
    expect(parseRoster(rosterToText(students)).students).toEqual(students)
  })
})
