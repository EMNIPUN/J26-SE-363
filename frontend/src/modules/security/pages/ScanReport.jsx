import PlaceholderPage from '../../../shared/components/PlaceholderPage.jsx'

export default function ScanReport() {
  return (
    <PlaceholderPage
      moduleKey="security"
      title="Scan Report"
      breadcrumb={['Security', 'Scan Report']}
      description="Results of the latest hybrid SAST + LLM scan (Bandit / Semgrep + LLM false-positive verification)."
      bullets={[
        'Findings list with file/line references',
        'LLM verification verdict per finding',
        'Educational-value & fix-complexity scores',
      ]}
    />
  )
}
