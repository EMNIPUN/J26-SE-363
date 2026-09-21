import PlaceholderPage from '../../../../../shared/components/PlaceholderPage.jsx'

export default function Estimation() {
  return (
    <PlaceholderPage
      moduleKey="planning"
      title="Effort Estimation"
      breadcrumb={['Planning', 'Requirements', 'Estimation']}
      description="Predicts effort/story points per requirement using historical project data, to feed sprint planning."
      bullets={[
        'Per-requirement effort prediction',
        'Confidence interval per estimate',
        'Comparison against team velocity',
      ]}
    />
  )
}
