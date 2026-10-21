import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Scale, ShieldAlert } from 'lucide-react'
import { Card } from '@/components/ui/card'
import EmptyState from '@/shared/components/EmptyState.jsx'
import PageHeader from '@/shared/components/PageHeader.jsx'
import { assessmentApi, assessmentKeys } from '../../assessment/assessmentApi.js'
import { FACTORS, FACTOR_LABEL } from '../../assessment/format.js'
import { ChartSkeleton, PanelSkeleton, Stagger } from '../../assessment/Reveal.jsx'

/**
 * How the marks are made, in the proposal's words: seven factors, fixed weights, a pattern adjustment, and the limits of the evidence.
 * Read from the latest finished run of the team, so it always shows what that run really used.
 */
export default function Method() {
  const { teamId } = useParams()
  const runs = useQuery({ queryKey: assessmentKeys.runs(teamId, undefined), queryFn: () => assessmentApi.runs(teamId) })
  const method = runs.data?.find((r) => r.summary?.method)?.summary.method
  const weights = method?.weights || {}
  const max = Math.max(0.01, ...Object.values(weights))

  return (
    <Stagger className="space-y-6" step={100}>
      <PageHeader title="Method and weights" description="How a mark is made, and what each factor can and cannot tell you. The agent decides nothing on its own: the formula is fixed and every step can be traced." />
      <Card className="gap-3 p-5">
        <h3 className="flex items-center gap-2 text-sm font-semibold"><Scale className="h-4 w-4" aria-hidden="true" />The formula</h3>
        <p className="rounded-lg bg-muted p-3 font-mono text-sm">mark = 100 × pattern adjustment × Σ ( weight × factor score )</p>
        <ul className="list-disc space-y-1 pl-5 text-sm text-muted-foreground">
          <li>Only the factors that could be measured count. The weight of a missing factor is shared among the others in proportion, so a student is never marked down for something the data cannot show.</li>
          <li>The working pattern (for example a steady contributor, or a last-minute rusher) adjusts the total once the sprint is final. During the sprint it is shown as a tendency only.</li>
          <li>The agent explains and flags. It cannot change a weight, a factor score or the formula. You can always set your own mark; the prediction stays next to it.</li>
        </ul>
      </Card>

      {runs.isPending ? (
        <div className="space-y-6" aria-busy="true"><PanelSkeleton height={220} /><ChartSkeleton height={160} /></div>
      ) : !method ? (
        <EmptyState icon={Scale} title="Shown after the first assessment" description="The weights and factor notes are read from a finished run so that they are exactly what that run used. Start a snapshot from the Assessment page." />
      ) : (
        <>
          <Card className="gap-4 p-5">
            <h3 className="text-sm font-semibold">Weights</h3>
            <div className="space-y-3">
              {Object.entries(weights).sort((a, b) => b[1] - a[1]).map(([id, w]) => (
                <div key={id} className="grid grid-cols-[170px_1fr_44px] items-center gap-3 text-sm">
                  <span className="truncate">{FACTOR_LABEL[id] || id}</span>
                  <div className="h-2.5 rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${(w / max) * 100}%` }} /></div>
                  <span className="text-right tabular-nums text-muted-foreground">{Math.round(w * 100)}%</span>
                </div>
              ))}
            </div>
          </Card>
          <div className="grid gap-3 @2xl:grid-cols-2">
            {[...FACTORS.map((f) => f.id), 'behavioral_pattern'].map((id) => {
              const f = method.factors?.[id]
              if (!f) return null
              return (
                <Card key={id} className="gap-2 p-4">
                  <h4 className="text-sm font-semibold">{FACTOR_LABEL[id]}</h4>
                  <p className="text-sm">{f.measures}</p>
                  {f.validation && <p className="text-xs text-muted-foreground"><span className="font-medium text-foreground">How far to trust it. </span>{f.validation}</p>}
                  {f.limits && <p className="text-xs text-muted-foreground"><span className="font-medium text-foreground">Limits. </span>{f.limits}</p>}
                </Card>
              )
            })}
          </div>
        </>
      )}

      <Card className="flex-row gap-3 border-amber-300/70 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/30">
        <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" aria-hidden="true" />
        <div className="space-y-1 text-sm text-amber-900 dark:text-amber-200">
          <p className="font-medium">Read the marks with this in mind</p>
          <p>The factor models were checked on 144 student sprints that an assistant rated, not on grades from teaching staff, so they have not yet been compared with your own judgement. Code Ownership is tested on Python only. Task Complexity is close to the sprint's story points. Treat every mark as a prediction to check against what you know of the team.</p>
        </div>
      </Card>
    </Stagger>
  )
}
