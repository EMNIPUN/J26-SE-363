import { ShieldAlert, GitCommit, FileCode, HelpCircle } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { PriorityBadge, StatusBadge, ConfidenceBadge } from './FindingBadges.jsx'
import CodeBlock from './CodeBlock.jsx'

export default function FindingDetailDialog({ finding, open, onOpenChange, onRequestReview }) {
  if (!finding) return null

  const canRequestReview = finding.status !== 'review' && finding.status !== 'closed'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <PriorityBadge priority={finding.priority} />
            <StatusBadge status={finding.status} />
            <ConfidenceBadge confidence={finding.confidence} />
          </div>
          <DialogTitle className="flex items-start gap-2">
            <ShieldAlert className="h-4 w-4 text-destructive mt-1 shrink-0" />
            <span>{finding.title}</span>
          </DialogTitle>
          <DialogDescription className="font-mono">
            {finding.file}
            {finding.line ? `:${finding.line}` : ''}
            {finding.endpoint ? ` • ${finding.endpoint}` : ''}
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="rounded-lg border border-border bg-muted/30 p-3">
            <p className="text-muted-foreground mb-0.5">OWASP</p>
            <p className="font-medium text-foreground">{finding.owasp}</p>
          </div>
          <div className="rounded-lg border border-border bg-muted/30 p-3">
            <p className="text-muted-foreground mb-0.5">CWE</p>
            <p className="font-medium text-foreground">{finding.cwe}</p>
          </div>
          <div className="rounded-lg border border-border bg-muted/30 p-3">
            <p className="text-muted-foreground mb-0.5">CVSS v3.1</p>
            <p className="font-medium text-foreground">
              {finding.cvss?.toFixed(1)}
              <span className="text-muted-foreground font-mono text-[10px] ml-1">
                {finding.cvssVector}
              </span>
            </p>
          </div>
          <div className="rounded-lg border border-border bg-muted/30 p-3">
            <p className="text-muted-foreground mb-0.5">Detected by</p>
            <p className="font-medium text-foreground">{finding.detector}</p>
          </div>
        </div>

        <div className="space-y-1.5">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
            <FileCode className="h-3.5 w-3.5" /> Evidence
          </h4>
          <CodeBlock lines={finding.code} highlightIndex={finding.vulnerableLine} />
        </div>

        <div className="space-y-1.5">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Why it matters
          </h4>
          <p className="text-sm text-foreground leading-relaxed">{finding.whyItMatters}</p>
        </div>

        <div className="space-y-1.5">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground flex items-center gap-1.5">
            <GitCommit className="h-3.5 w-3.5" /> Project context
          </h4>
          {finding.context.linked ? (
            <div className="flex flex-wrap gap-1.5">
              {finding.context.requirement && (
                <Badge variant="outline">{finding.context.requirement}</Badge>
              )}
              <Badge variant="outline" className="font-mono">
                {finding.context.commit}
              </Badge>
              {finding.context.sprintTask && (
                <Badge variant="outline">{finding.context.sprintTask}</Badge>
              )}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground italic">
              This finding could not be confidently linked to a requirement or user story. Shown
              as unlinked rather than guessed.
            </p>
          )}
        </div>

        {finding.probeQuestion && (
          <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 flex items-start gap-2">
            <HelpCircle className="h-4 w-4 text-primary mt-0.5 shrink-0" />
            <div>
              <p className="text-xs font-semibold text-foreground">Learning-check probe</p>
              <p className="text-xs text-muted-foreground mt-0.5">{finding.probeQuestion}</p>
            </div>
          </div>
        )}

        {canRequestReview && onRequestReview && (
          <div className="flex justify-end pt-1">
            <Button
              variant="outline"
              size="sm"
              className="cursor-pointer"
              onClick={() => onRequestReview(finding.id)}
            >
              Request review
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
