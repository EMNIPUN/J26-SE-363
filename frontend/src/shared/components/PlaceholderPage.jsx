import { Construction, CircleDashed } from 'lucide-react'
import PageHeader from './PageHeader.jsx'
import { Card } from '@/components/ui/card'

export default function PlaceholderPage({
  title,
  breadcrumb = [],
  description,
  bullets = [],
}) {
  return (
    <div className="space-y-6">
      <PageHeader title={title} breadcrumb={breadcrumb} description={description} />

      <Card className="p-8 sm:p-10 items-center text-center card-elevated ring-0 border border-dashed border-border bg-card">
        <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Construction className="h-6 w-6" strokeWidth={1.75} />
        </span>
        <div className="space-y-1">
          <h2 className="text-base font-semibold text-foreground">This page is being built</h2>
          <p className="text-sm text-muted-foreground max-w-md">
            The layout is ready and the features below are planned for an upcoming sprint.
          </p>
        </div>

        {bullets.length > 0 && (
          <ul className="mt-2 w-full max-w-md space-y-2 text-left">
            {bullets.map((item) => (
              <li
                key={item}
                className="flex items-start gap-2.5 rounded-lg border border-border/60 bg-muted/40 px-3 py-2 text-sm text-foreground"
              >
                <CircleDashed className="h-4 w-4 mt-0.5 shrink-0 text-muted-foreground" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}
