import PlaceholderPage from '../../../shared/components/PlaceholderPage.jsx'

export default function Remediation() {
  return (
    <PlaceholderPage
      moduleKey="security"
      title="Remediation"
      breadcrumb={['Security', 'Remediation']}
      description="LLM-generated remediation report with code-level fix suggestions for a selected vulnerability."
      bullets={[
        'Suggested fix diff',
        'Explanation of why it is vulnerable',
        'Mark as fixed / re-scan',
      ]}
    />
  )
}
