import { UserPlus, Search } from 'lucide-react'
import PageHeader from '../../../shared/components/PageHeader.jsx'
import Card from '../../../shared/components/Card.jsx'
import Badge from '../../../shared/components/Badge.jsx'
import Avatar from '../../../shared/components/Avatar.jsx'
import Button from '../../../shared/components/Button.jsx'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

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

      <Card className="p-0 overflow-hidden">
        <div className="p-4 border-b border-border bg-card">
          <div className="relative max-w-xs">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search users..."
              className="pl-9 h-9 text-sm"
            />
          </div>
        </div>

        <div className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead className="w-[140px]">Role</TableHead>
                <TableHead className="w-[140px]">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {USERS.map((u) => (
                <TableRow key={u.email}>
                  <TableCell>
                    <div className="flex items-center gap-3">
                      <Avatar name={u.name} size={34} />
                      <div>
                        <div className="font-semibold text-foreground text-sm">{u.name}</div>
                        <div className="text-xs text-muted-foreground">{u.email}</div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge tone={ROLE_TONE[u.role]}>{u.role}</Badge>
                  </TableCell>
                  <TableCell>
                    <Badge tone={STATUS_TONE[u.status]}>{u.status}</Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Card>
    </div>
  )
}

