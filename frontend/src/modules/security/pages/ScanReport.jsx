import { useMemo, useState } from 'react'
import { Search, ScanSearch, RotateCw } from 'lucide-react'
import PageHeader from '@/shared/components/PageHeader.jsx'
import QueryBoundary from '@/shared/components/QueryBoundary.jsx'
import EmptyState from '@/shared/components/EmptyState.jsx'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { showToast } from '@/shared/utils/toast.jsx'
import { useSecurityFindings } from '../hooks/useSecurityFindings.js'
import { CATEGORY_OPTIONS, STATUS_LABELS } from '../data/mockFindings.js'
import { PriorityBadge, StatusBadge, ConfidenceBadge } from '../components/FindingBadges.jsx'
import FindingDetailDialog from '../components/FindingDetailDialog.jsx'

export default function ScanReport() {
  const findingsQuery = useSecurityFindings()

  return (
    <div className="space-y-6 animate-fade-rise">
      <PageHeader
        title="Scan Report"
        breadcrumb={['Project Security', 'Scan Report']}
        description="Deterministic scanner findings (CodeQL, Gitleaks/TruffleHog, OSV-Scanner) triaged by a bounded LLM call for confidence, before any student sees them."
        actions={
          <Button
            variant="outline"
            size="sm"
            className="cursor-pointer"
            onClick={() =>
              showToast.info('Analysis queued', {
                description: 'Re-run analysis is a prototype-only action for the latest commit.',
              })
            }
          >
            <RotateCw className="h-4 w-4" /> Re-run analysis
          </Button>
        }
      />

      <QueryBoundary query={findingsQuery} variant="table" count={5}>
        {(findings) => <ScanReportBody findings={findings} />}
      </QueryBoundary>
    </div>
  )
}

const STATUS_TABS = ['all', 'open', 'review', 'learning', 'closed']

function ScanReportBody({ findings }) {
  const [statusFilter, setStatusFilter] = useState('all')
  const [categoryFilter, setCategoryFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [reviewedIds, setReviewedIds] = useState(() => new Set())

  const statusCounts = useMemo(() => {
    const counts = { all: findings.length, open: 0, review: 0, learning: 0, closed: 0 }
    findings.forEach((f) => {
      const status = reviewedIds.has(f.id) ? 'review' : f.status
      counts[status] = (counts[status] || 0) + 1
    })
    return counts
  }, [findings, reviewedIds])

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    return findings.filter((finding) => {
      const status = reviewedIds.has(finding.id) ? 'review' : finding.status
      if (statusFilter !== 'all' && status !== statusFilter) return false
      if (categoryFilter !== 'all' && finding.category !== categoryFilter) return false
      if (query) {
        const haystack = `${finding.title} ${finding.file}`.toLowerCase()
        if (!haystack.includes(query)) return false
      }
      return true
    })
  }, [findings, statusFilter, categoryFilter, search, reviewedIds])

  const selectedFinding = findings.find((f) => f.id === selectedId) || null
  const selectedDisplayStatus = selectedFinding
    ? reviewedIds.has(selectedFinding.id)
      ? 'review'
      : selectedFinding.status
    : null

  const handleRequestReview = (id) => {
    setReviewedIds((prev) => new Set(prev).add(id))
    showToast.success('Review requested', {
      description: 'This finding is now marked as awaiting review.',
    })
  }

  return (
    <div className="space-y-4">
      <Card className="p-4 bg-card border-border shadow-xs space-y-4">
        <div className="flex flex-col lg:flex-row lg:items-center gap-3 justify-between">
          <Tabs value={statusFilter} onValueChange={setStatusFilter}>
            <TabsList>
              {STATUS_TABS.map((status) => (
                <TabsTrigger key={status} value={status} className="capitalize">
                  {status === 'all' ? 'All' : STATUS_LABELS[status]} ({statusCounts[status] || 0})
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>

          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <Input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search title or file path"
                className="pl-8 h-9 w-56 text-xs"
              />
            </div>
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger className="w-44">
                <SelectValue placeholder="Category" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All categories</SelectItem>
                {CATEGORY_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      </Card>

      {filtered.length === 0 ? (
        <EmptyState
          icon={ScanSearch}
          title="No findings match these filters"
          description="Adjust the status, category, or search filters to see more results."
        />
      ) : (
        <div className="space-y-2">
          {filtered.map((finding) => {
            const displayStatus = reviewedIds.has(finding.id) ? 'review' : finding.status
            return (
              <Card
                key={finding.id}
                onClick={() => setSelectedId(finding.id)}
                className="p-4 bg-card border-border shadow-xs cursor-pointer card-hover-lift"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <PriorityBadge priority={finding.priority} />
                      <span className="text-[11px] text-muted-foreground">{finding.cwe}</span>
                    </div>
                    <p className="text-sm font-semibold text-foreground truncate">{finding.title}</p>
                    <p className="text-[11px] text-muted-foreground font-mono truncate">
                      {finding.file}
                      {finding.line ? `:${finding.line}` : ''}
                      {finding.endpoint ? ` • ${finding.endpoint}` : ''}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <ConfidenceBadge confidence={finding.confidence} />
                    <StatusBadge status={displayStatus} />
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      )}

      <FindingDetailDialog
        finding={selectedFinding ? { ...selectedFinding, status: selectedDisplayStatus } : null}
        open={Boolean(selectedFinding)}
        onOpenChange={(next) => !next && setSelectedId(null)}
        onRequestReview={handleRequestReview}
      />
    </div>
  )
}
