import PlaceholderPage from '../../../../shared/components/PlaceholderPage.jsx'

export default function Assessments() {
  return (
    <PlaceholderPage
      moduleKey="performance"
      title="Assessments"
      breadcrumb={['Performance', 'Instructor', 'Assessments']}
      description="Manage and trigger scoring assessment runs for a batch or group."
      bullets={['Assessment run history', 'Trigger a new scoring run', 'Adjust AHP factor weights']}
    />
  )
}
