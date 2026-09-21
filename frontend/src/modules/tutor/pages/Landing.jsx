import PlaceholderPage from '../../../shared/components/PlaceholderPage.jsx'

export default function Landing() {
  return (
    <PlaceholderPage
      moduleKey="tutor"
      title="Tutor Landing"
      breadcrumb={['Tutor', 'Landing']}
      description="Entry point into the adaptive AI tutor: current learning momentum, active sprint guidance, and a call-to-action into chat."
      bullets={[
        'Learning momentum summary',
        'Suggested next topic',
        'Enter chat with the tutor agent',
      ]}
    />
  )
}
