import { Navigate, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Checkbox } from '@/components/ui/checkbox'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import QueryBoundary from '@/shared/components/QueryBoundary.jsx'
import EmptyState from '@/shared/components/EmptyState.jsx'
import AssistantFrame from '../components/AssistantFrame.jsx'
import { FindingRow, StatusCounts } from '../components/FindingParts.jsx'
import { useFindings } from '../hooks/useSecurityAssistant.js'
import { CATEGORIES, categoryState, countByCategory, filterFindings, firstCategoryWithFindings, totalOf } from '../lib/format.js'

const STATUSES = ['confirmed', 'dismissed', 'uncertain']

// The tabs, counts by status, the "mine" and status filters, and the list of one type. Pure of routing: the page below feeds it.
export function FindingsBody({ overview, selection, team, category, mine, status, data, onChange, linkFor }) {
  const all = data.findings
  const counts = mine ? countByCategory(filterFindings(all, { mine: true })) : data.counts ?? overview.counts
  const shown = filterFindings(all, { category, status, mine })
  const hasId = (data.my_contributor_ids ?? []).length > 0
  return (
    <div className="space-y-4">
      <Tabs value={category} onValueChange={(value) => onChange({ category: value })}>
        <TabsList className="h-auto flex-wrap">
          {CATEGORIES.map((c) => (
            <TabsTrigger key={c.id} value={c.id} data-category={c.id}>
              {c.id} {c.label}
              <span className="ml-1 rounded bg-muted px-1 text-[11px]">{totalOf(counts[c.id])}</span>
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <StatusCounts row={counts[category]} />
        <div className="flex flex-wrap items-center gap-4 text-sm">
          <label className="flex items-center gap-2">
            <Checkbox checked={mine} onCheckedChange={(value) => onChange({ mine: Boolean(value) })} aria-label="Only my findings" />
            Only my findings
          </label>
          <label className="flex items-center gap-2 text-xs text-muted-foreground">
            Status
            <select
              aria-label="Status"
              className="rounded-md border border-input bg-card px-2 py-1 text-xs text-foreground"
              value={status}
              onChange={(e) => onChange({ status: e.target.value })}
            >
              <option value="">all</option>
              {STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {mine && !hasId && (
        <p role="status" className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
          No contributor id was found for {selection.student ? 'this student' : 'you'} in this run, so &quot;mine&quot; is empty. This does not mean there are no findings.
        </p>
      )}

      {shown.length ? (
        <ul data-slot="finding-list" className="space-y-2">
          {shown.map((f) => (
            <FindingRow key={f.group_id} finding={f} to={linkFor(f)} />
          ))}
        </ul>
      ) : (
        <EmptyState
          title={mine ? 'None of the findings of this type are yours' : status ? `No ${status} findings of this type` : 'No findings of this type in this run'}
          description={categoryState(overview.scan.coverage?.[category], counts[category]).text}
        />
      )}
      <p className="text-xs text-muted-foreground">Team {team}. Open a finding for the scanner evidence, the verdict, the risk breakdown, the links and the fix.</p>
    </div>
  )
}

function Loaded({ overview, selection, team }) {
  const { category: categoryParam } = useParams()
  const navigate = useNavigate()
  const { search } = useLocation()
  const [params, setParams] = useSearchParams()
  const findingsQuery = useFindings(team, selection.run, selection.student)
  const base = `/teams/${team}/security/assistant/findings`
  const category = CATEGORIES.some((c) => c.id === categoryParam) ? categoryParam : null
  if (!category) return <Navigate replace to={`${base}/${firstCategoryWithFindings(overview.counts)}${search}`} />

  const mine = params.get('mine') === '1'
  const status = params.get('status') || ''
  const setParam = (name, value) =>
    setParams((current) => {
      const next = new URLSearchParams(current)
      if (value) next.set(name, value)
      else next.delete(name)
      return next
    })
  const onChange = (change) => {
    if ('category' in change) navigate(`${base}/${change.category}${search}`)
    if ('mine' in change) setParam('mine', change.mine ? '1' : '')
    if ('status' in change) setParam('status', change.status)
  }
  return (
    <QueryBoundary query={findingsQuery} variant="card" count={3}>
      {(data) => (
        <FindingsBody
          {...{ overview, selection, team, category, mine, status, data, onChange }}
          linkFor={(f) => `${base}/${f.category}/${f.group_id}${search}`}
        />
      )}
    </QueryBoundary>
  )
}

export default function FindingsPage() {
  return (
    <AssistantFrame
      title="Findings by vulnerability type"
      description="Every finding of the run, one tab per type (V1 to V5), with what the scanner reported and what the LLM concluded."
      howToRead="Pick a type, then open a finding: the left side of the card is the scanner, the right side the model; a dismissed finding is an argument, not proof."
    >
      {(context) => <Loaded {...context} />}
    </AssistantFrame>
  )
}
