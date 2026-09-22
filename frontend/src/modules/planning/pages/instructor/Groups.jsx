import { useNavigate } from 'react-router-dom'
import PageHeader from '../../../../shared/components/PageHeader.jsx'
import Card from '../../../../shared/components/Card.jsx'
import Badge from '../../../../shared/components/Badge.jsx'
import { Progress } from '@/components/ui/progress'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { GROUPS } from '../../data/mockData.js'
import { RISK_TONE } from '../../utils.js'

export default function InstructorGroups() {
  const navigate = useNavigate()

  return (
    <div className="space-y-6">
      <PageHeader
        title="Groups"
        breadcrumb={['Planning', 'Instructor', 'Groups']}
        description="Group roster and per-group requirement quality-gate summary."
      />

      <Card className="p-0 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Group</TableHead>
              <TableHead>Members</TableHead>
              <TableHead className="w-[220px]">Quality gate</TableHead>
              <TableHead className="w-[110px]">Risk</TableHead>
              <TableHead className="w-[110px]">Open flags</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {GROUPS.map((g) => (
              <TableRow
                key={g.id}
                className="cursor-pointer"
                onClick={() => navigate(`/planning/instructor/groups/${g.id}`)}
              >
                <TableCell className="font-medium">{g.name}</TableCell>
                <TableCell className="text-muted-foreground">{g.members}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Progress value={g.qualityGate} className="h-1.5 w-28" />
                    <span className="text-xs font-medium text-foreground">{g.qualityGate}%</span>
                  </div>
                </TableCell>
                <TableCell>
                  <Badge tone={RISK_TONE[g.risk]}>{g.risk}</Badge>
                </TableCell>
                <TableCell>{g.openArbitrations}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
    </div>
  )
}
