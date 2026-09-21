import PlaceholderPage from '../../../shared/components/PlaceholderPage.jsx'

export default function Nudges() {
  return (
    <PlaceholderPage
      moduleKey="tutor"
      title="Nudges"
      breadcrumb={['Tutor', 'Nudges']}
      description="Proactive nudges sent to a student when learning momentum drops or a sprint deadline is at risk."
      bullets={['Nudge history', 'Nudge trigger rules', 'Dismiss / snooze a nudge']}
    />
  )
}
