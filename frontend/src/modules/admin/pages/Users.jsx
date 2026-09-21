import { UserPlus, Search } from 'lucide-react'
import PageHeader from '../../../shared/components/PageHeader.jsx'
import Card from '../../../shared/components/Card.jsx'
import Badge from '../../../shared/components/Badge.jsx'
import Avatar from '../../../shared/components/Avatar.jsx'
import Button from '../../../shared/components/Button.jsx'
import '../../../shared/styles/table.css'

const USERS = [
  { name: 'Nimal Perera', email: 'student@lms.edu', role: 'Student', status: 'Active' },
  { name: 'Dr. Amara Silva', email: 'instructor@lms.edu', role: 'Instructor', status: 'Active' },
  { name: 'System Admin', email: 'admin@lms.edu', role: 'Admin', status: 'Active' },
  { name: 'Kasun Fernando', email: 'kasun.f@lms.edu', role: 'Student', status: 'Active' },
  { name: 'Dr. Ishara Weerasinghe', email: 'ishara.w@lms.edu', role: 'Instructor', status: 'Invited' },
  { name: 'Tharindu Jayasuriya', email: 'tharindu.j@lms.edu', role: 'Student', status: 'Suspended' },
]

const ROLE_TONE = { Student: 'primary', Instructor: 'success', Admin: 'warning' }
const STATUS_TONE = { Active: 'success', Invited: 'neutral', Suspended: 'danger' }

export default function Users() {
  return (
    <div>
      <PageHeader
        title="Users"
        breadcrumb={['Admin', 'Users']}
        description="Everyone with access to the platform, across all three roles."
        actions={
          <Button icon={UserPlus} size="md">
            Invite user
          </Button>
        }
      />

      <Card>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-border)' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              maxWidth: 320,
              padding: '8px 12px',
              border: '1px solid var(--color-border)',
              borderRadius: 'var(--radius-md)',
              background: 'var(--color-surface-muted)',
            }}
          >
            <Search size={15} strokeWidth={2} color="var(--color-text-muted)" />
            <input
              type="text"
              placeholder="Search users..."
              style={{
                border: 'none',
                background: 'transparent',
                outline: 'none',
                fontSize: 13.5,
                width: '100%',
                fontFamily: 'var(--font-sans)',
              }}
            />
          </div>
        </div>

        <div style={{ padding: '4px 20px 20px' }}>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Role</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {USERS.map((u) => (
                <tr key={u.email}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <Avatar name={u.name} size={30} />
                      <div>
                        <div style={{ fontWeight: 600, color: 'var(--color-heading)' }}>{u.name}</div>
                        <div style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{u.email}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <Badge tone={ROLE_TONE[u.role]}>{u.role}</Badge>
                  </td>
                  <td>
                    <Badge tone={STATUS_TONE[u.status]}>{u.status}</Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
