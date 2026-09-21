import PlaceholderPage from '../../../../../shared/components/PlaceholderPage.jsx'

export default function Decomposition() {
  return (
    <PlaceholderPage
      moduleKey="planning"
      title="Requirement Decomposition"
      breadcrumb={['Planning', 'Requirements', 'Decomposition']}
      description="Breaks a high-level requirement down into implementable sub-tasks and user stories."
      bullets={[
        'Auto-generated sub-task tree',
        'Editable story splits',
        'Push accepted breakdown to sprint backlog',
      ]}
    />
  )
}
