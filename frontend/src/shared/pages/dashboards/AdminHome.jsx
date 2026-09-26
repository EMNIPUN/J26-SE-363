import { Users, FolderKanban, ShieldAlert, Activity } from 'lucide-react'
import { useAuth } from '../../auth/useAuth.js'
import { getModule } from '../../constants/modules.js'
import StatCard from '../../components/StatCard.jsx'
import ComponentLinkGrid from '../../components/ComponentLinkGrid.jsx'
import Card from '../../components/Card.jsx'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

const quickLinks = [
  { ...getModule('planning'), to: '/planning/dashboard' },
  { ...getModule('performance'), to: '/performance/dashboard' },
  { ...getModule('security'), to: '/security/dashboard' },
]

export default function AdminHome() {
  const { user } = useAuth()

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
          Welcome back, {user.name} 👋
        </h1>
        <p className="text-sm text-muted-foreground mt-1">System-wide overview across every component.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Users} label="Total Users" value="342" tone="primary" />
        <StatCard icon={FolderKanban} label="Active Projects" value="28" tone="primary" />
        <StatCard icon={ShieldAlert} label="Open Security Issues" value="19" tone="danger" />
        <StatCard icon={Activity} label="System Uptime" value="99.9%" tone="success" />
      </div>

      <div>
        <div className="flex items-baseline justify-between mb-4">
          <h2 className="text-xl font-bold tracking-tight text-foreground">Components</h2>
          <p className="text-xs text-muted-foreground">Read-only oversight into each teammate's component</p>
        </div>
        <ComponentLinkGrid items={quickLinks} />
      </div>

      <Card>
        <h3 className="text-base font-semibold text-foreground mb-4">Recently added users</h3>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Role</TableHead>
              <TableHead className="w-[140px]">Joined</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell className="font-medium">Kasun Fernando</TableCell>
              <TableCell>Student</TableCell>
              <TableCell className="text-muted-foreground">2 days ago</TableCell>
            </TableRow>
            <TableRow>
              <TableCell className="font-medium">Dr. Ishara Weerasinghe</TableCell>
              <TableCell>Instructor</TableCell>
              <TableCell className="text-muted-foreground">5 days ago</TableCell>
            </TableRow>
            <TableRow>
              <TableCell className="font-medium">Tharindu Jayasuriya</TableCell>
              <TableCell>Student</TableCell>
              <TableCell className="text-muted-foreground">1 week ago</TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}

