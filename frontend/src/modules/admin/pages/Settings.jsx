import PageHeader from '../../../shared/components/PageHeader.jsx'
import Card from '../../../shared/components/Card.jsx'
import Switch from '../../../shared/components/Switch.jsx'
import Button from '../../../shared/components/Button.jsx'
import { useTheme } from '../../../shared/theme/useTheme.js'
import { Sun, Moon, Laptop } from 'lucide-react'

export default function Settings() {
  const { theme, setTheme } = useTheme()

  return (
    <div className="space-y-6 max-w-2xl">
      <PageHeader
        title="Settings"
        breadcrumb={['Admin', 'Settings']}
        description="Platform-wide preferences and appearance settings."
      />

      <Card className="space-y-4">
        <h3 className="text-base font-semibold text-foreground pb-2 border-b border-border">Appearance & Theme</h3>
        <p className="text-xs text-muted-foreground">Select your interface theme preference across the platform.</p>
        <div className="grid grid-cols-3 gap-3 pt-1">
          <button
            type="button"
            onClick={() => setTheme('light')}
            className={`flex flex-col items-center gap-2 p-3 rounded-lg border text-xs font-medium transition-colors cursor-pointer ${
              theme === 'light'
                ? 'border-primary bg-primary/10 text-primary font-semibold'
                : 'border-border bg-card text-muted-foreground hover:bg-accent'
            }`}
          >
            <Sun className="h-5 w-5" />
            <span>Light</span>
          </button>
          <button
            type="button"
            onClick={() => setTheme('dark')}
            className={`flex flex-col items-center gap-2 p-3 rounded-lg border text-xs font-medium transition-colors cursor-pointer ${
              theme === 'dark'
                ? 'border-primary bg-primary/10 text-primary font-semibold'
                : 'border-border bg-card text-muted-foreground hover:bg-accent'
            }`}
          >
            <Moon className="h-5 w-5" />
            <span>Dark / Black</span>
          </button>
          <button
            type="button"
            onClick={() => setTheme('system')}
            className={`flex flex-col items-center gap-2 p-3 rounded-lg border text-xs font-medium transition-colors cursor-pointer ${
              theme === 'system'
                ? 'border-primary bg-primary/10 text-primary font-semibold'
                : 'border-border bg-card text-muted-foreground hover:bg-accent'
            }`}
          >
            <Laptop className="h-5 w-5" />
            <span>System</span>
          </button>
        </div>
      </Card>

      <Card className="space-y-1">
        <h3 className="text-base font-semibold text-foreground pb-2 border-b border-border">Notifications</h3>
        <Switch label="Email digest for at-risk students" defaultChecked />
        <Switch label="Nudge students when momentum drops" defaultChecked />
        <Switch label="Weekly security scan summary" />
      </Card>

      <Card className="space-y-1">
        <h3 className="text-base font-semibold text-foreground pb-2 border-b border-border">Access</h3>
        <Switch label="Allow instructors to invite students" defaultChecked />
        <Switch label="Require MFA for admin accounts" />
      </Card>

      <div>
        <Button size="md">Save changes</Button>
      </div>
    </div>
  )
}

