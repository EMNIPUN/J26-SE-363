import PlaceholderPage from '../../../../../shared/components/PlaceholderPage.jsx'

export default function Traceability() {
  return (
    <PlaceholderPage
      moduleKey="planning"
      title="Requirement Traceability"
      breadcrumb={['Planning', 'Requirements', 'Traceability']}
      description="Maps each requirement to the code, tests and commits that implement it, so gaps in coverage surface early."
      bullets={[
        'Requirement → code coverage matrix',
        'Orphan requirement detection',
        'Traceability graph view',
      ]}
    />
  )
}
