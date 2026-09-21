import PlaceholderPage from '../../../../shared/components/PlaceholderPage.jsx'

export default function InstructorGroups() {
  return (
    <PlaceholderPage
      moduleKey="planning"
      title="Groups"
      breadcrumb={['Planning', 'Instructor', 'Groups']}
      description="Group roster and per-group requirement quality-gate summary."
      bullets={['Group roster', 'Per-group quality gate summary', 'Drill into a single group']}
    />
  )
}
