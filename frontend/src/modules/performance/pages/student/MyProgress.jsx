import PlaceholderPage from '../../../../shared/components/PlaceholderPage.jsx'

export default function MyProgress() {
  return (
    <PlaceholderPage
      moduleKey="performance"
      title="My Progress"
      breadcrumb={['Performance', 'Student', 'My Progress']}
      description="A student's own contribution score, broken down by the 7 activity factors collected from GitHub and Scrum."
      bullets={[
        'AHP-weighted contribution score',
        'Per-factor breakdown (commits, reviews, standups, ...)',
        'At-risk prediction status',
      ]}
    />
  )
}
