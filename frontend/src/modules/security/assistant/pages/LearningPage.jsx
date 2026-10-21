import { useLocation, useSearchParams } from 'react-router-dom'
import { Checkbox } from '@/components/ui/checkbox'
import QueryBoundary from '@/shared/components/QueryBoundary.jsx'
import EmptyState from '@/shared/components/EmptyState.jsx'
import AssistantFrame from '../components/AssistantFrame.jsx'
import { LearningItem, LearningSummaryCard, MockNotice } from '../components/LearningParts.jsx'
import { useLearning } from '../hooks/useSecurityAssistant.js'
import { LEARNING_TITLE } from '../lib/format.js'

// The checks of one run: the notice, the summary, then every question thread. Pure of routing so it can be rendered on its own.
export function LearningBody({ data, mine, onMineChange, linkFor, student }) {
  const items = mine ? data.items.filter((i) => i.mine) : data.items
  const hasId = (data.my_contributor_ids ?? []).length > 0
  return (
    <div className="space-y-4">
      <MockNotice tutor={data.tutor} />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-sm">
          <Checkbox checked={mine} onCheckedChange={(v) => onMineChange(Boolean(v))} aria-label="Only my findings" />
          Only the checks of my findings
        </label>
        <p className="text-xs text-muted-foreground">Threshold for &quot;understood&quot;: {data.threshold} (simulated)</p>
      </div>
      {mine && !hasId && (
        <p role="status" className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
          No contributor id was found for {student ? 'this student' : 'you'} in this run, so &quot;mine&quot; is empty.
        </p>
      )}
      {data.items.length ? (
        <>
          <LearningSummaryCard items={items} scope={mine ? 'only my findings' : 'the whole team'} />
          {items.length ? (
            <ul data-slot="learning-list" className="space-y-3">
              {items.map((item) => (
                <LearningItem key={item.group_id} item={item} threshold={data.threshold} to={linkFor(item)} />
              ))}
            </ul>
          ) : (
            <EmptyState title="None of the comprehension checks are for your findings" description="Switch the filter off to see the checks of the whole team." />
          )}
        </>
      ) : (
        <EmptyState
          title="No comprehension checks in this run"
          description="Probe questions are made only for findings the LLM confirmed. In this run the LLM stages did not run or confirmed nothing, so there is nothing to show: this is not a pass."
        />
      )}
    </div>
  )
}

function Loaded({ selection, team }) {
  const query = useLearning(team, selection.run, selection.student)
  const [params, setParams] = useSearchParams()
  const { search } = useLocation()
  const mine = params.get('mine') === '1'
  const setMine = (value) =>
    setParams((current) => {
      const next = new URLSearchParams(current)
      if (value) next.set('mine', '1')
      else next.delete('mine')
      return next
    })
  return (
    <QueryBoundary query={query} variant="card" count={3}>
      {(data) => (
        <LearningBody
          data={data}
          mine={mine}
          student={selection.student}
          onMineChange={setMine}
          linkFor={(item) => `/teams/${team}/security/assistant/findings/${item.category}/${item.group_id}${search}`}
        />
      )}
    </QueryBoundary>
  )
}

export default function LearningPage() {
  return (
    <AssistantFrame
      title={LEARNING_TITLE}
      description="The question the Tutor would ask about each confirmed finding, the follow-ups, and the simulated score against the threshold. All of it is mock."
      howToRead="Read the MOCK notice first: no student was asked and nothing was graded; then see which checks closed, which were escalated to the lecturer, and how many questions it took."
    >
      {(context) => <Loaded {...context} />}
    </AssistantFrame>
  )
}
