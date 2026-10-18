import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { useNotificationPreferences, useSetNotificationPreference } from '../../hooks/useNotifications.js'
import PageHeader from '../../components/PageHeader.jsx'

/** Which notifications also arrive by email. The notification itself always shows in the app. */
export default function NotificationSettingsPage() {
  const preferences = useNotificationPreferences()
  const set = useSetNotificationPreference()

  return (
    <div className="grid gap-6">
      <PageHeader title="Notifications" description="Choose which ones also reach you by email." />

      {preferences.isPending && <Skeleton className="h-40 w-full" aria-busy="true" />}
      {preferences.isError && <p className="text-sm text-destructive">Your settings could not be loaded.</p>}
      {preferences.isSuccess && (
        <Card className="divide-y divide-border p-0">
          {preferences.data.categories.map((item) => (
            <div key={item.category} className="flex items-center justify-between gap-4 p-4 sm:px-6">
              <div className="min-w-0">
                <label htmlFor={`email-${item.category}`} className="text-sm font-medium text-foreground">
                  {item.label}
                </label>
                <p className="text-sm text-muted-foreground">
                  {item.description}
                  {!item.configurable && ' Always emailed, so you never miss one.'}
                </p>
              </div>
              <Switch
                id={`email-${item.category}`}
                checked={item.email_enabled}
                disabled={!item.configurable || set.isPending}
                onCheckedChange={(enabled) => set.mutate({ category: item.category, enabled })}
                aria-label={`Email me about ${item.label.toLowerCase()}`}
              />
            </div>
          ))}
        </Card>
      )}
    </div>
  )
}
