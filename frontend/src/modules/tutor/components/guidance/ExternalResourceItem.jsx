import { Clock, ExternalLink, Globe } from 'lucide-react'
import { Button } from '@/components/ui/button'
import ItemBadges from './ItemBadges.jsx'
import { RESOURCE_FORMAT, getMeta } from '../../utils/statusMeta.js'
import { isSafeExternalUrl } from '../../utils/url.js'

export default function ExternalResourceItem({ resource }) {
  const { provider, title, description, url, format, level, estimatedMinutes, matchesLevel } = resource
  const formatMeta = getMeta(RESOURCE_FORMAT, format)

  return (
    <article className="flex h-full flex-col gap-3 rounded-lg border border-border/60 bg-card p-4">
      <p className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
        <Globe className="h-3.5 w-3.5" aria-hidden="true" />
        <span className="font-semibold text-foreground">{provider}</span>
        <span aria-hidden="true">·</span>
        {formatMeta.label}
      </p>
      <div className="flex-1">
        <h4 className="text-sm font-semibold leading-snug text-foreground">{title}</h4>
        <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{description}</p>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <ItemBadges level={level} matchesLevel={matchesLevel} />
        <span className="flex items-center gap-1 text-[11px] text-muted-foreground">
          <Clock className="h-3.5 w-3.5" aria-hidden="true" />
          {estimatedMinutes} min
        </span>
      </div>
      {isSafeExternalUrl(url) && (
        <Button asChild size="sm" variant="outline" className="w-full">
          <a href={url} target="_blank" rel="noopener noreferrer">
            Open on {provider}
            <ExternalLink aria-hidden="true" />
            <span className="sr-only">(opens in a new tab)</span>
          </a>
        </Button>
      )}
    </article>
  )
}
