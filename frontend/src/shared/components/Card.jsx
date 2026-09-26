import { Card as ShadcnCard } from '@/components/ui/card'
import LoadingState from './LoadingState.jsx'

export default function Card({
  className = '',
  loading = false,
  query,
  loadingVariant = 'card',
  loadingFallback,
  children,
  ...props
}) {
  const isLoading = loading || Boolean(query?.isLoading || query?.isPending)

  if (isLoading) {
    return loadingFallback || (
      <LoadingState
        loading={true}
        variant={loadingVariant}
        className={className}
      />
    )
  }

  return (
    <ShadcnCard className={`p-6 shadow-sm border border-border bg-card text-card-foreground ${className}`} {...props}>
      {children}
    </ShadcnCard>
  )
}

