import PlaceholderPage from '../../../../shared/components/PlaceholderPage.jsx'

export default function Blackboard() {
  return (
    <PlaceholderPage
      moduleKey="planning"
      title="Blackboard"
      breadcrumb={['Planning', 'Student', 'Blackboard']}
      description="Shared workspace where the requirement-analysis agents post drafts, questions and arbitration notes for the student to review."
      bullets={[
        'Agent-generated requirement drafts',
        'Inline clarification requests',
        'CTIA arbitration transcript',
      ]}
    />
  )
}
