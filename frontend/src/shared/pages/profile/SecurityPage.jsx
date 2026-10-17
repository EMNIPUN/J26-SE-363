import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { useAuth } from '../../auth/useAuth.js'
import Badge from '../../components/Badge.jsx'
import PageHeader from '../../components/PageHeader.jsx'

function Row({ title, description, action }) {
  return (
    <div className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0">
        <p className="text-sm font-medium text-foreground">{title}</p>
        <div className="text-sm text-muted-foreground">{description}</div>
      </div>
      {action}
    </div>
  )
}

/** Email and password. Changing the password is done on the sign-in page, which asks for it safely. */
export default function SecurityPage() {
  const { account, changePassword } = useAuth()
  const [starting, setStarting] = useState(false)

  return (
    <div className="grid gap-6">
      <PageHeader title="Security" description="How you sign in." />

      <Card className="divide-y divide-border p-5 sm:p-6">
        <Row
          title="Email"
          description={
            <span className="flex flex-wrap items-center gap-2">
              <span className="break-all">{account.email}</span>
              {account.email_verified ? (
                <Badge tone="success">Verified</Badge>
              ) : (
                <Badge tone="warning">Not verified</Badge>
              )}
            </span>
          }
        />
        <Row
          title="Password"
          description="You are taken to the sign-in page to choose a new one."
          action={
            <Button
              variant="outline"
              loading={starting}
              onClick={() => {
                setStarting(true)
                changePassword()
              }}
            >
              Change password
            </Button>
          }
        />
      </Card>
    </div>
  )
}
