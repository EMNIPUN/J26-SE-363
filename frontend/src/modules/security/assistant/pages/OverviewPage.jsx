import AssistantFrame from '../components/AssistantFrame.jsx'
import { CoverageGrid, IncompleteBanner, ProvenanceCard, StageStrip, ToolRunsTable } from '../components/OverviewParts.jsx'

export function OverviewBody({ overview }) {
  return (
    <div className="space-y-4">
      <IncompleteBanner run={overview.run} scan={overview.scan} />
      <ProvenanceCard overview={overview} />
      <StageStrip stages={overview.stages} />
      <ToolRunsTable toolRuns={overview.scan.tool_runs} />
      <CoverageGrid coverage={overview.scan.coverage} counts={overview.counts} />
    </div>
  )
}

export default function OverviewPage() {
  return (
    <AssistantFrame
      title="Security Assistant: run overview"
      description="Where a run came from, which stages and tools ran, and how much of each vulnerability type was actually checked."
      howToRead="Start with the banner: INCOMPLETE means something did not run and the result is not a clean one; then read the coverage per type before trusting any '0 findings'."
    >
      {({ overview }) => <OverviewBody overview={overview} />}
    </AssistantFrame>
  )
}
