import PlaceholderPage from '../../../shared/components/PlaceholderPage.jsx'

export default function Chat() {
  return (
    <PlaceholderPage
      moduleKey="tutor"
      title="Tutor Chat"
      breadcrumb={['Tutor', 'Chat']}
      description="Conversational interface with the Project Learning, Sprint Guidance and Learning Momentum agents over MCP."
      bullets={[
        'Message thread with the tutor agent',
        'Agent routing indicator (which agent answered)',
        'Suggested follow-up questions',
      ]}
    />
  )
}
