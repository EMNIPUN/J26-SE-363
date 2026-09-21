import PlaceholderPage from '../../../shared/components/PlaceholderPage.jsx'

export default function Dashboard() {
  return (
    <PlaceholderPage
      moduleKey="security"
      title="AEGIS Dashboard"
      breadcrumb={['Security', 'Dashboard']}
      description="Overview of vulnerabilities found across the project's codebase, classified by OWASP Top 10 category and MSSM score."
      bullets={[
        'Open vulnerabilities by severity',
        'OWASP Top 10 category breakdown',
        'MSSM score trend over sprints',
      ]}
    />
  )
}
