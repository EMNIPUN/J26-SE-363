import PlaceholderPage from '../../../../shared/components/PlaceholderPage.jsx'

export default function InstructorDashboard() {
  return (
    <PlaceholderPage
      moduleKey="performance"
      title="Instructor Dashboard"
      breadcrumb={['Performance', 'Instructor', 'Dashboard']}
      description="Overview of individual contribution scores across every student in every supervised group, with at-risk students flagged."
      bullets={[
        'Contribution score distribution',
        'At-risk students this sprint',
        'Group comparison view',
      ]}
    />
  )
}
