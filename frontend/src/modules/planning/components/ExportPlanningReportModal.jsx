import { useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
import { FileText, Copy, Printer, Check, GraduationCap, ShieldCheck } from 'lucide-react'
import Badge from '../../../shared/components/Badge.jsx'
import { COURSE_INFO } from '../data/lmsAcademicData.js'

export default function ExportPlanningReportModal({
  open,
  onOpenChange,
  requirements = [],
  kanbanTasks = [],
  teamMembers = [],
  projectInfo = {},
  stats = {},
}) {
  const [copied, setCopied] = useState(false)

  const passingReqs = requirements.filter((r) => r.status === 'Passing')
  const reviewReqs = requirements.filter((r) => r.status === 'Needs Review')
  const failingReqs = requirements.filter((r) => r.status === 'Failing')
  const totalPoints = kanbanTasks.reduce((acc, t) => acc + (t.points || 0), 0)
  const donePoints = kanbanTasks.filter((t) => t.status === 'Done').reduce((acc, t) => acc + (t.points || 0), 0)

  const generateMarkdownReport = () => {
    return `# ACADEMIC PLANNING DOSSIER & IEEE 830 QUALITY REPORT
**Course:** ${COURSE_INFO.courseCode} — ${COURSE_INFO.courseName}
**Academic Year:** ${COURSE_INFO.academicYear} | ${COURSE_INFO.faculty}
**Group:** ${COURSE_INFO.group.number} (${COURSE_INFO.group.code}) — ${COURSE_INFO.group.name}
**Supervisor:** ${COURSE_INFO.supervisor.name} (${COURSE_INFO.supervisor.title})
**Generated Date:** ${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
**Active Sprint:** ${projectInfo.sprintName || 'Sprint 5'} (${projectInfo.sprintStartDate} to ${projectInfo.sprintEndDate})

---

## 1. Executive Planning & Quality Summary
- **Total Tracked Requirements:** ${requirements.length}
- **Quality Gate Pass Rate:** ${stats.quality?.percent ?? 79}% (Threshold: 70%)
- **Passing Requirements:** ${passingReqs.length} / ${requirements.length}
- **Under Review / Attention:** ${reviewReqs.length}
- **Blocked / Infeasible:** ${failingReqs.length}
- **Committed Sprint Velocity:** ${totalPoints} Story Points (${donePoints} SP completed)

---

## 2. Requirement Specification & Quality Gate Status
| Req ID | Title | Priority | Gate Status | Score | Suggested Action |
|---|---|---|---|---|---|
${requirements
  .map(
    (r) =>
      `| **${r.id}** | ${r.title.replace(/\|/g, '-')} | ${r.priority} | ${r.status} | ${r.overallScore}% | ${r.status === 'Passing' ? 'Ready for Sprint' : 'Needs Student Refinement'} |`,
  )
  .join('\n')}

---

## 3. Team Workload & Sprint Allocation
| Student Name | Academic Role | Capacity (SP) | Assigned (SP) | Load Status |
|---|---|---|---|---|
${teamMembers
  .map((m) => {
    const assigned = kanbanTasks.filter((t) => t.assigneeId === m.id && t.status !== 'Done')
    const pts = assigned.reduce((s, t) => s + (t.points || 0), 0)
    const status = pts > m.capacity ? 'OVER CAPACITY ⚠' : 'Balanced ✓'
    return `| ${m.name} | ${m.role} | ${m.capacity} SP | ${pts} SP | ${status} |`
  })
  .join('\n')}

---
*Report generated automatically by SELVIA Intelligent LMS Planning Gateway for academic defense and rubric grading.*
`
  }

  const handleCopy = () => {
    const md = generateMarkdownReport()
    navigator.clipboard.writeText(md)
    setCopied(true)
    toast.success('Dossier copied to clipboard in Markdown format')
    setTimeout(() => setCopied(false), 2000)
  }

  const handlePrint = () => {
    window.print()
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1 rounded bg-primary/10 text-primary">
              <FileText className="h-4 w-4" />
            </span>
            <DialogTitle className="text-lg font-bold">Academic Planning Dossier Export</DialogTitle>
          </div>
          <DialogDescription className="text-xs">
            Official project planning summary formatted for academic submission, supervisor viva defense, and IEEE 830 verification.
          </DialogDescription>
        </DialogHeader>

        {/* Preview Container */}
        <div className="p-4 rounded-xl border border-border bg-muted/20 space-y-4 text-xs font-sans print:border-none print:p-0">
          <div className="flex items-start justify-between border-b border-border pb-3">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-wider text-primary">
                {COURSE_INFO.courseCode} · {COURSE_INFO.department}
              </p>
              <h3 className="text-base font-bold text-foreground mt-0.5">{COURSE_INFO.group.name}</h3>
              <p className="text-muted-foreground text-[11px]">
                {COURSE_INFO.group.number} ({COURSE_INFO.group.code}) · Supervised by {COURSE_INFO.supervisor.name}
              </p>
            </div>
            <Badge tone="success" className="text-xs shrink-0">
              Verified LMS Dossier
            </Badge>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 py-1">
            <div className="p-2 rounded-lg bg-card border border-border/80">
              <span className="text-[10px] text-muted-foreground block">Quality Gate</span>
              <span className="text-base font-bold text-foreground">{stats.quality?.percent ?? 79}%</span>
            </div>
            <div className="p-2 rounded-lg bg-card border border-border/80">
              <span className="text-[10px] text-muted-foreground block">Requirements</span>
              <span className="text-base font-bold text-foreground">
                {passingReqs.length} / {requirements.length} Passing
              </span>
            </div>
            <div className="p-2 rounded-lg bg-card border border-border/80">
              <span className="text-[10px] text-muted-foreground block">Sprint Points</span>
              <span className="text-base font-bold text-foreground">{totalPoints} SP</span>
            </div>
            <div className="p-2 rounded-lg bg-card border border-border/80">
              <span className="text-[10px] text-muted-foreground block">Sprint Window</span>
              <span className="text-base font-bold text-foreground truncate">{projectInfo.sprintName}</span>
            </div>
          </div>

          <div>
            <p className="font-semibold text-foreground mb-1.5 flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5 text-primary" /> Tracked SRS Requirements ({requirements.length})
            </p>
            <div className="max-h-48 overflow-y-auto rounded-lg border border-border bg-card">
              <table className="w-full text-left text-[11px]">
                <thead className="bg-muted/50 border-b border-border text-muted-foreground font-semibold">
                  <tr>
                    <th className="p-2">ID</th>
                    <th className="p-2">Requirement</th>
                    <th className="p-2">Priority</th>
                    <th className="p-2 text-right">Gate Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {requirements.map((r) => (
                    <tr key={r.id}>
                      <td className="p-2 font-mono font-medium text-primary">{r.id}</td>
                      <td className="p-2 truncate max-w-[280px]">{r.title}</td>
                      <td className="p-2 text-muted-foreground">{r.priority}</td>
                      <td className="p-2 text-right font-medium">
                        <span
                          className={
                            r.status === 'Passing'
                              ? 'text-emerald-600'
                              : r.status === 'Needs Review'
                                ? 'text-amber-600'
                                : 'text-destructive'
                          }
                        >
                          {r.status} ({r.overallScore}%)
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <DialogFooter className="pt-2 gap-2 flex-wrap sm:justify-between">
          <p className="text-[11px] text-muted-foreground flex items-center gap-1">
            <GraduationCap className="h-3.5 w-3.5 text-primary" /> Ready for Capstone Milestone M3 Defense
          </p>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleCopy}
              className="text-xs cursor-pointer gap-1.5"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
              {copied ? 'Copied Markdown!' : 'Copy Markdown'}
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={handlePrint}
              className="text-xs cursor-pointer gap-1.5 bg-primary text-primary-foreground"
            >
              <Printer className="h-3.5 w-3.5" />
              Print / Save PDF
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
