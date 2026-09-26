import { AlertCircle, RefreshCw } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import LoadingState from './LoadingState.jsx'
import EmptyState from './EmptyState.jsx'

/**
 * Universal Query Boundary & Auto-Skeleton Component
 *
 * Automatically connects TanStack Query (or custom fetch status) to the global skeleton loader:
 *
 * 1. While Fetching (`isLoading: true`) -> Automatically renders matching skeletons
 * 2. If Failed (`isError: true`) -> Renders an error box with retry button
 * 3. If Empty (`isEmpty: true` or empty array) -> Renders empty state fallback if provided
 * 4. When Ready -> Renders children or invokes children as a render function: {(data) => <View data={data} />}
 *
 * @example
 * const projectQuery = useProjects()
 *
 * <QueryBoundary query={projectQuery} variant="card" count={3}>
 *   {(projects) => <ProjectList items={projects} />}
 * </QueryBoundary>
 */
export default function QueryBoundary({
  query,
  variant = 'card',
  count = 1,
  className = '',
  loadingFallback,
  errorFallback,
  emptyFallback,
  checkEmpty = false,
  emptyIcon,
  emptyTitle,
  emptyDescription,
  emptyActionLabel,
  onEmptyAction,
  children,
}) {
  // Support a single query or an array of queries: [query1, query2]
  const queries = Array.isArray(query) ? query : [query].filter(Boolean)

  const isLoading = queries.some((q) => q?.isLoading || q?.isPending)
  const isError = queries.some((q) => q?.isError)
  const error = queries.find((q) => q?.error)?.error
  const refetch = () => queries.forEach((q) => q?.refetch?.())

  // 1. Auto-Loading: Render matching global skeleton loader
  if (isLoading) {
    return (
      <LoadingState
        loading={true}
        variant={variant}
        count={count}
        className={className}
        fallback={loadingFallback}
      />
    )
  }

  // 2. Auto-Error: Render standard error fallback with retry
  if (isError) {
    if (errorFallback) {
      return typeof errorFallback === 'function' ? errorFallback(error, refetch) : errorFallback
    }

    return (
      <Card className={`p-6 border-destructive/20 bg-destructive/5 text-center ${className}`}>
        <div className="flex flex-col items-center justify-center max-w-sm mx-auto space-y-3">
          <div className="p-2.5 rounded-full bg-destructive/10 text-destructive">
            <AlertCircle className="h-5 w-5" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-foreground">Failed to load data</h4>
            <p className="text-xs text-muted-foreground mt-1">
              {error?.message || 'An unexpected error occurred while communicating with the server.'}
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={refetch}
            className="cursor-pointer gap-2 mt-1 active:scale-95"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Try again</span>
          </Button>
        </div>
      </Card>
    )
  }

  // Primary data from first query
  const primaryData = queries[0]?.data

  // 3. Auto-Empty (optional check)
  const isEmptyData =
    checkEmpty &&
    (primaryData == null || (Array.isArray(primaryData) && primaryData.length === 0))

  if (isEmptyData) {
    if (emptyFallback) return emptyFallback

    return (
      <EmptyState
        icon={emptyIcon}
        title={emptyTitle || 'No data available'}
        description={emptyDescription || 'There are no records to display at this moment.'}
        actionLabel={emptyActionLabel}
        onAction={onEmptyAction}
        className={className}
      />
    )
  }

  // 4. Render Children (Function-as-a-Child or Standard JSX)
  if (typeof children === 'function') {
    return children(Array.isArray(query) ? queries.map((q) => q?.data) : primaryData)
  }

  return children
}
