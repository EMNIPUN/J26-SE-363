import PlaceholderPage from '../../../../shared/components/PlaceholderPage.jsx'

export default function StudentDetail() {
  return (
    <PlaceholderPage
      moduleKey="performance"
      title="Student Detail"
      breadcrumb={['Performance', 'Instructor', 'Student Detail']}
      description="Deep dive into a single student's activity evidence, AHP weighting and the code-comprehension verification result."
      bullets={[
        'Activity timeline (GitHub + Scrum)',
        'Code comprehension verification transcript',
        'Logistic-regression at-risk score over time',
      ]}
    />
  )
}
