import PlaceholderPage from '../../../../shared/components/PlaceholderPage.jsx'

export default function InstructorProjects() {
  return (
    <PlaceholderPage
      moduleKey="planning"
      title="Projects"
      breadcrumb={['Planning', 'Instructor', 'Projects']}
      description="List of every project the instructor supervises, with a link into each project's requirement set."
      bullets={['Project list with status badges', 'Filter by batch / group', 'Create new project']}
    />
  )
}
