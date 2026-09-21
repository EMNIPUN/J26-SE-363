import PlaceholderPage from '../../../../shared/components/PlaceholderPage.jsx'

export default function Reports() {
  return (
    <PlaceholderPage
      moduleKey="performance"
      title="Reports"
      breadcrumb={['Performance', 'Instructor', 'Reports']}
      description="Exportable per-student and per-group performance reports."
      bullets={['Export to PDF / CSV', 'Report template picker', 'Scheduled report history']}
    />
  )
}
