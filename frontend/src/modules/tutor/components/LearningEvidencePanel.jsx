import { CheckCircle2, CircleX, ClipboardList, HelpCircle } from 'lucide-react'

function requiredConceptIndex(requiredKnowledge) {
  const names = {}
  for (const task of requiredKnowledge?.tasks || []) {
    for (const concept of task.required_concepts || []) {
      if (concept?.concept_id) {
        names[concept.concept_id] = concept.concept_name || concept.concept_id
      }
    }
  }
  return names
}

function evidenceForRequiredConcepts(records, requiredKnowledge) {
  const names = requiredConceptIndex(requiredKnowledge)
  const allowed = new Set(Object.keys(names))
  const courseId = requiredKnowledge?.course_id
  if (allowed.size === 0) return []
  return records.filter((record) => {
    const conceptId = record.conceptId || record.concept_id
    if (!allowed.has(conceptId)) return false
    const rowCourse = record.courseId || record.course_id
    if (courseId && rowCourse && rowCourse !== courseId) return false
    return true
  })
}

function formatWhen(value) {
  if (!value) return '—'
  try {
    return new Date(value).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    })
  } catch {
    return String(value)
  }
}

function scoreLabel(record) {
  if (typeof record.percentage === 'number') return `${Math.round(record.percentage)}%`
  if (typeof record.score === 'number' && typeof record.maxScore === 'number') {
    return `${record.score}/${record.maxScore}`
  }
  if (typeof record.score === 'number') return String(record.score)
  return '—'
}

function sourceLabel(sourceType) {
  if (!sourceType) return 'Performance record'
  return String(sourceType).replaceAll('_', ' ').toLowerCase()
}

/**
 * Student-facing evidence list for the Learning evidence checkpoint.
 */
export default function LearningEvidencePanel({
  evidenceCount,
  performanceEvidence = [],
  normalizedEvidence = [],
  requiredKnowledge = null,
  loading = false,
  status = 'pending',
}) {
  const names = requiredConceptIndex(requiredKnowledge)
  const hasCount = typeof evidenceCount === 'number'
  const records = evidenceForRequiredConcepts(
    Array.isArray(performanceEvidence) ? performanceEvidence : [],
    requiredKnowledge,
  )
  const visibleIds = new Set(records.map((record) => record.id).filter(Boolean))
  const visibleNormalized = (normalizedEvidence || []).filter((item) =>
    visibleIds.has(item.evidence_id),
  )
  const normalizedById = Object.fromEntries(
    visibleNormalized.map((item) => [item.evidence_id, item]),
  )

  if (!hasCount) {
    if (loading || status === 'running' || status === 'preparing') {
      return (
        <p className="rounded-xl bg-card px-4 py-3 text-sm text-muted-foreground">
          Collecting your learning evidence from SLAP…
        </p>
      )
    }
    return (
      <p className="rounded-xl bg-card px-4 py-3 text-sm text-muted-foreground">
        Run analysis to retrieve performance evidence for your required concepts.
      </p>
    )
  }

  const usableForBkt = visibleNormalized.length

  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl bg-card px-4 py-4 shadow-xs">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Required-concept records
          </p>
          <p className="mt-1 text-3xl font-semibold tracking-tight text-foreground">
            {records.length}
          </p>
        </div>
        <div className="rounded-2xl bg-card px-4 py-4 shadow-xs">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            Usable for BKT
          </p>
          <p className="mt-1 text-3xl font-semibold tracking-tight text-foreground">
            {usableForBkt}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            Item/exercise attempts with Boolean correctness (lesson views excluded).
          </p>
        </div>
      </div>

      {records.length === 0 ? (
        <p className="rounded-xl bg-card px-4 py-3 text-sm text-muted-foreground">
          No evidence was found for the concepts this sprint requires. Evidence from other courses is not shown.
        </p>
      ) : (
        <ul className="space-y-3">
          {records.map((record, index) => {
            const id = record.id || `evidence-${index}`
            const conceptId = record.conceptId || record.concept_id
            const normalized = normalizedById[id]
            const correct = normalized?.correct
            const title = conceptId
              ? names[conceptId] || conceptId
              : 'No concept linked'

            return (
              <li key={id} className="rounded-2xl bg-card px-4 py-4 shadow-xs">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                      <ClipboardList className="h-3.5 w-3.5" aria-hidden="true" />
                      {sourceLabel(record.sourceType || record.source_type)}
                      {record.attemptNumber != null
                        ? ` · attempt ${record.attemptNumber}`
                        : ''}
                    </p>
                    <h4 className="mt-1 text-sm font-semibold text-foreground">{title}</h4>
                    {conceptId ? (
                      <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">
                        {conceptId}
                      </p>
                    ) : (
                      <p className="mt-0.5 text-xs text-muted-foreground">
                        Skipped for BKT (missing concept id)
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-semibold tabular-nums text-foreground">
                      {scoreLabel(record)}
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      {formatWhen(record.observedAt || record.observed_at)}
                    </p>
                  </div>
                </div>

                <div className="mt-3 flex flex-wrap items-center gap-3 text-xs">
                  {correct === true ? (
                    <span className="inline-flex items-center gap-1 font-medium text-emerald-700 dark:text-emerald-400">
                      <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                      Counted as correct for BKT
                    </span>
                  ) : correct === false ? (
                    <span className="inline-flex items-center gap-1 font-medium text-amber-800 dark:text-amber-300">
                      <CircleX className="h-3.5 w-3.5" aria-hidden="true" />
                      Counted as incorrect for BKT
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 text-muted-foreground">
                      <HelpCircle className="h-3.5 w-3.5" aria-hidden="true" />
                      Not used for BKT
                    </span>
                  )}
                  {record.status ? (
                    <span className="rounded-md bg-muted px-2 py-0.5 text-muted-foreground">
                      {String(record.status)}
                    </span>
                  ) : null}
                </div>
              </li>
            )
          })}
        </ul>
      )}

      <p className="text-xs leading-relaxed text-muted-foreground">
        This list shows evidence for the required concepts of this course only.
        BKT uses chronological exercise or assessment-answer records that include a concept
        id, a valid item or exercise id, and Boolean is_correct — not a score threshold.
        Missing usable evidence stays unknown, not zero.
      </p>
    </div>
  )
}
