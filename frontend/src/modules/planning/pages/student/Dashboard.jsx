import PlaceholderPage from '../../../../shared/components/PlaceholderPage.jsx'

export default function Dashboard() {
  return (
    <PlaceholderPage
      moduleKey="planning"
      title="Student Dashboard"
      breadcrumb={['Planning', 'Student', 'Dashboard']}
      description="Overview of the student's active project: current sprint, requirement quality-gate status and any open CTIA arbitration flags."
      bullets={[
        'Active project summary card',
        'Six-dimensional quality gate status',
        'Open CTIA arbitration flags',
        'Shortcuts to Blackboard and Requirements tools',
      ]}
    />
  )
}
