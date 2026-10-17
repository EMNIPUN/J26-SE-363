export const TERM_MAX_LENGTH = 32

/**
 * The rows the term dropdown shows for what has been typed: the terms that contain it, plus an
 * "add new" row when it is not an existing term (compared without regard to case).
 */
export function termOptions(terms, typed) {
  const text = typed.trim()
  const rows = terms
    .filter((term) => term.toLowerCase().includes(text.toLowerCase()))
    .map((term) => ({ kind: 'term', term }))
  const exists = terms.some((term) => term.toLowerCase() === text.toLowerCase())
  if (text && !exists && text.length <= TERM_MAX_LENGTH) rows.push({ kind: 'new', term: text })
  return rows
}
