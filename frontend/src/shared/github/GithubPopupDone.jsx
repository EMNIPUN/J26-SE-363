import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { CheckCircle2, ShieldAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { announceResult } from './githubPopup.js'
import { reasonText } from './gateCopy.js'

/** The page GitHub's small window ends on. It tells the window that opened it what happened and closes itself. */
export default function GithubPopupDone() {
  const [params] = useSearchParams()
  const github = params.get('github') || 'error'
  const reason = params.get('reason') || undefined
  const ok = github === 'installed' || github === 'connected'

  useEffect(() => {
    announceResult({ github, reason })
    const t = setTimeout(() => window.close(), 400)
    return () => clearTimeout(t)
  }, [github, reason])

  return (
    <div className="fixed inset-0 z-[200] grid place-items-center bg-background p-6 text-center">
      <div className="max-w-sm space-y-3">
        {ok ? <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-500" aria-hidden="true" /> : <ShieldAlert className="mx-auto h-10 w-10 text-rose-500" aria-hidden="true" />}
        <p className="text-lg font-semibold">{ok ? 'Done. Going back to SELVIA...' : 'That did not work'}</p>
        {!ok && <p className="text-sm text-muted-foreground">{reasonText(reason)}</p>}
        <Button variant="outline" onClick={() => window.close()}>Close this window</Button>
      </div>
    </div>
  )
}
