import { useState } from 'react'
import {
  Download,
  Printer,
} from 'lucide-react'
import { useScope } from '@/shared/context/useScope.js'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { toast } from 'sonner'

export default function Reports() {
  const { selectedGroup, teamStudents } = useScope()
  const [exporting, setExporting] = useState(false)

  const handleExportCSV = () => {
    setExporting(true)
    const headers = ['Student ID,Name,Role,AHP Score (10),Contribution %,Risk Level,Viva %,Final Mark (100)']
    const rows = teamStudents.map((s) => {
      const finalMark = Math.round((s.currentScore || 8.5) * 10)
      return `${s.studentId},"${s.name}","${s.roleInGroup || 'Member'}",${s.currentScore || 8.5},${Math.round(100 / teamStudents.length)}%,${s.riskLevel || 'Low'},${s.comprehensionRate || 92}%,${finalMark}`
    })

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers, ...rows].join('\n')
    const encodedUri = encodeURI(csvContent)
    const link = document.createElement('a')
    link.setAttribute('href', encodedUri)
    link.setAttribute('download', `performance_report_${selectedGroup?.code || 'team'}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    toast.success('CSV Export Generated', {
      description: `Gradebook export for ${selectedGroup?.code} has been downloaded.`,
    })
    setExporting(false)
  }

  const handlePrint = () => {
    window.print()
  }

  return (
    <div className="space-y-6 animate-fade-rise">
      {/* Header and Export Actions */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="text-xs font-mono font-bold text-primary">
              {selectedGroup?.code}
            </Badge>
            <span className="text-xs text-muted-foreground">
              Official Evaluation Ledger
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">
            Academic Performance Gradebook & Reports
          </h1>
          <p className="text-xs text-muted-foreground">
            SLIIT final viva evaluation summary, AHP weighted scores, and forensic contribution records.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handlePrint}
            className="text-xs gap-1.5 cursor-pointer"
          >
            <Printer className="h-3.5 w-3.5" />
            <span>Print Report</span>
          </Button>

          <Button
            size="sm"
            onClick={handleExportCSV}
            disabled={exporting}
            className="text-xs gap-1.5 cursor-pointer"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Export CSV</span>
          </Button>
        </div>
      </div>

      {/* Gradebook Table Card */}
      <Card className="p-5 bg-card border-border shadow-xs space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-border">
          <div>
            <h3 className="text-sm font-semibold text-foreground">
              Team Member Final Gradebook
            </h3>
            <p className="text-[11px] text-muted-foreground">
              {selectedGroup?.name} • Project: {selectedGroup?.projectTitle}
            </p>
          </div>
          <Badge variant="secondary" className="text-xs font-mono">
            {teamStudents.length} Students Evaluated
          </Badge>
        </div>

        {/* Responsive Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-muted/40 text-muted-foreground font-semibold border-b border-border">
              <tr>
                <th className="p-3">Student Name</th>
                <th className="p-3">Student ID</th>
                <th className="p-3">Role / Component</th>
                <th className="p-3 text-center">AHP Score (10)</th>
                <th className="p-3 text-center">Viva Oral (%)</th>
                <th className="p-3 text-center">Risk Tier</th>
                <th className="p-3 text-right">Final Mark (100)</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {teamStudents.map((s) => {
                const finalMark = Math.round((s.currentScore || 8.5) * 10)
                const isLowRisk = s.riskLevel === 'Low' || !s.riskLevel
                return (
                  <tr key={s.id} className="hover:bg-muted/20 transition-colors">
                    <td className="p-3 font-semibold text-foreground">
                      {s.name}
                    </td>
                    <td className="p-3 font-mono text-muted-foreground">
                      {s.studentId}
                    </td>
                    <td className="p-3 text-muted-foreground">
                      {s.roleInGroup || s.assignedComponent || 'Engineering Lead'}
                    </td>
                    <td className="p-3 text-center font-mono font-bold text-foreground">
                      {s.currentScore || 8.5}
                    </td>
                    <td className="p-3 text-center font-mono font-medium">
                      {s.comprehensionRate || 92}%
                    </td>
                    <td className="p-3 text-center">
                      <Badge
                        variant={isLowRisk ? 'secondary' : 'destructive'}
                        className={`text-[10px] font-semibold ${
                          isLowRisk
                            ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20'
                            : ''
                        }`}
                      >
                        {s.riskLevel || 'Low'}
                      </Badge>
                    </td>
                    <td className="p-3 text-right font-mono font-bold text-sm text-foreground">
                      {finalMark}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Examiner Verification Block */}
      <Card className="p-5 bg-card border-border shadow-xs space-y-3">
        <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
          SLIIT Viva Evaluation Panel Certification
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2 text-xs">
          <div className="p-3.5 rounded-lg border border-border/70 space-y-3 bg-muted/10">
            <span className="font-semibold text-foreground">Lead Supervisor Signature</span>
            <div className="h-10 border-b border-dashed border-border" />
            <div className="flex items-center justify-between text-[11px] text-muted-foreground">
              <span>Date: ______________</span>
              <span>Status: Certified</span>
            </div>
          </div>

          <div className="p-3.5 rounded-lg border border-border/70 space-y-3 bg-muted/10">
            <span className="font-semibold text-foreground">Co-Supervisor / External Examiner</span>
            <div className="h-10 border-b border-dashed border-border" />
            <div className="flex items-center justify-between text-[11px] text-muted-foreground">
              <span>Date: ______________</span>
              <span>Status: Certified</span>
            </div>
          </div>
        </div>
      </Card>
    </div>
  )
}
