import PlaceholderPage from '../../../../shared/components/PlaceholderPage.jsx'

export default function InstructorDashboard() {
  return (
    <PlaceholderPage
      moduleKey="planning"
      title="Instructor Dashboard"
      breadcrumb={['Planning', 'Instructor', 'Dashboard']}
      description="Cross-project view of requirement quality-gate pass rates across every supervised group."
      bullets={[
        'Quality gate pass rate by group',
        'Groups with unresolved arbitration flags',
        'Trend over the last 3 sprints',
      ]}
    />
  )
}
