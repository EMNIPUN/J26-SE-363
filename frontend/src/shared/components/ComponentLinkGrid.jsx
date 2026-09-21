import { Link } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'
import { Card } from '@/components/ui/card'

export default function ComponentLinkGrid({ items }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {items.map((m) => (
        <Card
          key={m.key}
          className="group relative p-5 card-hover-lift active:scale-[0.99] border-border overflow-hidden flex flex-col justify-between bg-card cursor-pointer"
        >
          <Link to={m.to} className="flex flex-col h-full justify-between">
            <div>
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1">
                {m.owner}
              </span>
              <h3 className="text-lg font-semibold text-foreground group-hover:text-primary transition-colors duration-150">
                {m.label}
              </h3>
              <p className="text-xs text-muted-foreground mt-1.5 line-clamp-2">{m.tagline}</p>
            </div>
            <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-xs font-medium text-primary">
              <span>Open component</span>
              <ArrowUpRight className="h-4 w-4 transition-transform duration-200 ease-[cubic-bezier(0.16,1,0.3,1)] group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            </div>
          </Link>
        </Card>
      ))}
    </div>
  )
}

