import LoadingState from './LoadingState.jsx'
import ErrorState from './ErrorState.jsx'
import EmptyState from './EmptyState.jsx'

function isEmptyData(data) {
  return data == null || (Array.isArray(data) && data.length === 0)
}

// Renders the loading / error / empty / success state of a TanStack query.
// `children` is a render function that receives the query data.
export default function QueryState({
  query,
  isEmpty = isEmptyData,
  loading = <LoadingState />,
  errorTitle,
  emptyIcon,
  emptyTitle = 'Nothing to show yet',
  emptyDescription,
  children,
}) {
  if (query.isPending) return loading

  if (query.isError) {
    return <ErrorState title={errorTitle} message={query.error?.message} onRetry={() => query.refetch()} />
  }

  if (isEmpty(query.data)) {
    return <EmptyState icon={emptyIcon} title={emptyTitle} description={emptyDescription} />
  }

  return children(query.data)
}
