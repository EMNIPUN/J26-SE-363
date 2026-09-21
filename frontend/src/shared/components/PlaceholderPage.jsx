import PageHeader from './PageHeader.jsx'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'

export default function PlaceholderPage({
  title,
  breadcrumb = [],
  description,
  bullets = [],
}) {

  return (
    <div className="space-y-6">
      <PageHeader title={title} breadcrumb={breadcrumb} description={description} />

      {bullets.length > 0 && (
        <Card className="border-border">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              Planned for this page
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc list-inside space-y-1.5 text-sm text-foreground">
              {bullets.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      <div className="p-10 border-2 border-dashed border-border rounded-xl text-center text-sm text-muted-foreground bg-muted/30">
        Dummy content — real UI for this page is not implemented yet.
      </div>
    </div>
  )
}

