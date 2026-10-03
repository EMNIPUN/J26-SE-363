import { Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, Compass, Home } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function NotFound() {
  const navigate = useNavigate()

  return (
    <div className="min-h-[60svh] flex flex-col items-center justify-center text-center gap-4 px-6">
      <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
        <Compass className="h-7 w-7" strokeWidth={1.75} />
      </span>
      <div className="space-y-1.5">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Error 404</p>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">We couldn&apos;t find that page</h1>
        <p className="text-sm text-muted-foreground max-w-md">
          The link may be broken, or the page may have moved. Use the sidebar or head back to your overview.
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-center gap-2 pt-2">
        <Button variant="outline" onClick={() => navigate(-1)} className="cursor-pointer">
          <ArrowLeft className="h-4 w-4" />
          Go back
        </Button>
        <Button asChild>
          <Link to="/app">
            <Home className="h-4 w-4" />
            Back to overview
          </Link>
        </Button>
      </div>
    </div>
  )
}
