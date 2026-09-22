import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

/**
 * Standalone Skeleton Wireframes (Can be used directly or through LoadingState)
 */

export function SkeletonCard({ className = '' }) {
  return (
    <Card className={`p-5 space-y-3 border-border bg-card animate-pulse ${className}`}>
      <div className="space-y-2">
        <Skeleton className="h-4 w-1/3" />
        <Skeleton className="h-3 w-1/2" />
      </div>
      <div className="space-y-2 pt-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-5/6" />
        <Skeleton className="h-3 w-2/3" />
      </div>
    </Card>
  )
}

export function SkeletonStat({ className = '' }) {
  return (
    <Card className={`p-5 flex items-start gap-4 border-border bg-card animate-pulse ${className}`}>
      <Skeleton className="h-11 w-11 rounded-lg shrink-0" />
      <div className="flex-1 space-y-2 py-0.5 min-w-0">
        <Skeleton className="h-3 w-20" />
        <Skeleton className="h-6 w-14" />
        <Skeleton className="h-2.5 w-16" />
      </div>
    </Card>
  )
}

export function SkeletonTable({ rows = 5, cols = 4, className = '' }) {
  return (
    <Card className={`p-0 overflow-hidden border-border bg-card animate-pulse ${className}`}>
      {/* Table Header Skeleton */}
      <div className="flex items-center gap-4 px-4 py-3 border-b border-border bg-muted/40">
        {Array.from({ length: cols }).map((_, c) => (
          <Skeleton key={`th-${c}`} className="h-3.5 flex-1" />
        ))}
      </div>
      {/* Table Rows Skeleton */}
      <div className="divide-y divide-border/40">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={`tr-${r}`} className="flex items-center gap-4 px-4 py-3">
            {Array.from({ length: cols }).map((_, c) => (
              <Skeleton
                key={`td-${r}-${c}`}
                className={`h-3 ${c === 0 ? 'w-24' : 'flex-1'}`}
              />
            ))}
          </div>
        ))}
      </div>
    </Card>
  )
}

export function SkeletonList({ count = 4, className = '' }) {
  return (
    <div className={`space-y-2.5 animate-pulse ${className}`}>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={`list-${i}`}
          className="flex items-center gap-3 p-3 rounded-lg border border-border bg-card"
        >
          <Skeleton className="h-8 w-8 rounded-full shrink-0" />
          <div className="flex-1 space-y-1.5 min-w-0">
            <Skeleton className="h-3.5 w-1/3" />
            <Skeleton className="h-2.5 w-2/3" />
          </div>
        </div>
      ))}
    </div>
  )
}

export function SkeletonText({ lines = 3, className = '' }) {
  return (
    <div className={`space-y-2 animate-pulse ${className}`}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={`line-${i}`}
          className={`h-3 ${i === lines - 1 ? 'w-2/3' : 'w-full'}`}
        />
      ))}
    </div>
  )
}

/**
 * Universal Intelligent Loading State Wrapper
 *
 * Developers can wrap any section:
 * <LoadingState loading={isLoading} variant="card | stat | table | list | text" count={3} fallback={<Custom />}>
 *   <MyComponent />
 * </LoadingState>
 */
export default function LoadingState({
  loading = false,
  variant = 'card',
  count = 1,
  fallback,
  children,
  className = '',
}) {
  if (!loading) return children

  if (fallback) return fallback

  const renderSingle = (index) => {
    switch (variant) {
      case 'stat':
        return <SkeletonStat key={index} className={className} />
      case 'table':
        return <SkeletonTable key={index} className={className} />
      case 'list':
        return <SkeletonList key={index} count={count} className={className} />
      case 'text':
        return <SkeletonText key={index} lines={count} className={className} />
      case 'card':
      default:
        return <SkeletonCard key={index} className={className} />
    }
  }

  if (count > 1 && variant !== 'list' && variant !== 'text') {
    return (
      <div className={`grid gap-4 ${className}`}>
        {Array.from({ length: count }).map((_, i) => renderSingle(i))}
      </div>
    )
  }

  return renderSingle(0)
}
