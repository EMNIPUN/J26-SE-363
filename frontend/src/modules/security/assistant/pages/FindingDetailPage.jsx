import { Link, useLocation, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import QueryBoundary from '@/shared/components/QueryBoundary.jsx'
import AssistantFrame from '../components/AssistantFrame.jsx'
import { FindingHeader, FixGuidance, ProbeCard, RiskBreakdown, ScannerVsVerdict, TraceLinks } from '../components/FindingParts.jsx'
import RequestReviewButton from '../components/RequestReviewButton.jsx'
import { useFinding } from '../hooks/useSecurityAssistant.js'

export function FindingCard({ finding, overview, team, run }) {
  return (
    <div data-slot="finding-card" data-group={finding.group_id} className="space-y-4">
      <FindingHeader finding={finding} action={<RequestReviewButton team={team} run={run} finding={finding} />} />
      <ScannerVsVerdict finding={finding} model={overview.llm?.model} />
      <RiskBreakdown risk={finding.risk} />
      <TraceLinks finding={finding} />
      <FixGuidance finding={finding} />
      <ProbeCard probe={finding.probe} threshold={overview.llm?.threshold} />
    </div>
  )
}

function Loaded({ overview, selection, team }) {
  const { groupId, category } = useParams()
  const { search } = useLocation()
  const query = useFinding(team, selection.run, groupId, selection.student)
  return (
    <div className="space-y-4">
      <Link to={`/teams/${team}/security/assistant/findings/${category}${search}`} className="inline-flex items-center gap-1 text-sm text-primary hover:underline">
        <ArrowLeft className="h-4 w-4" /> Back to {category} findings
      </Link>
      <QueryBoundary query={query} variant="card" count={3}>
        {(finding) => <FindingCard finding={finding} overview={overview} team={team} run={selection.run} />}
      </QueryBoundary>
    </div>
  )
}

export default function FindingDetailPage() {
  return (
    <AssistantFrame
      title="Finding detail"
      description="Everything the run knows about one finding."
      howToRead="Read top to bottom: what the scanner saw, what the model concluded, how it was ranked, where the code came from, then how to fix it and the question that checks understanding."
    >
      {(context) => <Loaded {...context} />}
    </AssistantFrame>
  )
}
