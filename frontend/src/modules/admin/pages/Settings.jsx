import PageHeader from '../../../shared/components/PageHeader.jsx'
import Card from '../../../shared/components/Card.jsx'
import Switch from '../../../shared/components/Switch.jsx'
import Button from '../../../shared/components/Button.jsx'

export default function Settings() {
  return (
    <div>
      <PageHeader
        title="Settings"
        breadcrumb={['Admin', 'Settings']}
        description="Platform-wide preferences. These are dummy toggles for the prototype."
      />

      <Card style={{ padding: '8px 20px', maxWidth: 560, marginBottom: 20 }}>
        <h3 style={{ padding: '14px 0 4px' }}>Notifications</h3>
        <Switch label="Email digest for at-risk students" defaultChecked />
        <Switch label="Nudge students when momentum drops" defaultChecked />
        <Switch label="Weekly security scan summary" />
      </Card>

      <Card style={{ padding: '8px 20px', maxWidth: 560, marginBottom: 20 }}>
        <h3 style={{ padding: '14px 0 4px' }}>Access</h3>
        <Switch label="Allow instructors to invite students" defaultChecked />
        <Switch label="Require MFA for admin accounts" />
      </Card>

      <Button size="md">Save changes</Button>
    </div>
  )
}
