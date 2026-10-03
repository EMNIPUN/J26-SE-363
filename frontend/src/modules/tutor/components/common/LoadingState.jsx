import { Skeleton } from '@/components/ui/skeleton'

export default function LoadingState({ rows = 3, label = 'Loading' }) {
  return (
    <div role="status" aria-label={label} className="space-y-3">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="space-y-1.5">
          <Skeleton className="h-2.5 w-1/4" />
          <Skeleton className={i === rows - 1 ? 'h-3.5 w-2/3' : 'h-3.5 w-5/6'} />
        </div>
      ))}
    </div>
  )
}
