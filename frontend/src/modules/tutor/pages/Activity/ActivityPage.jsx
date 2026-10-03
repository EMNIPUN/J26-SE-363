import { useCallback, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Clock, Info, ShieldAlert, Target } from 'lucide-react'
import { Button } from '@/components/ui/button'
import TutorHeader from '../../components/tutor/TutorHeader.jsx'
import QueryState from '../../components/common/QueryState.jsx'
import LoadingState from '../../components/common/LoadingState.jsx'
import EmptyState from '../../components/common/EmptyState.jsx'
import ItemBadges from '../../components/guidance/ItemBadges.jsx'
import ActivityFrame from '../../components/activity/ActivityFrame.jsx'
import ActivityCompletion from '../../components/activity/ActivityCompletion.jsx'
import { useActivity, useSyncActivity } from '../../hooks/useActivity.js'
import { useActivityCompletionMessage } from '../../hooks/useActivityCompletionMessage.js'
import { useTutorPaths } from '../../utils/tutorPaths.js'
import { ACTIVITY_KIND, getMeta } from '../../utils/statusMeta.js'
import { resolveEmbedUrl } from '../../utils/url.js'

function ActivityMeta({ activity }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-muted-foreground">
      <ItemBadges
        level={activity.level}
        matchesLevel={activity.matchesLevel}
        recommended={activity.recommended}
        challenge={activity.challenge}
      />
      <span className="flex items-center gap-1.5">
        <Target className="h-3.5 w-3.5" aria-hidden="true" />
        <span className="font-medium text-foreground">{activity.concept.name}</span>
      </span>
      <span className="flex items-center gap-1.5">
        <Clock className="h-3.5 w-3.5" aria-hidden="true" />
        About {activity.estimatedMinutes} min
      </span>
      {activity.lastScore != null && (
        <span>
          Last score <span className="font-medium tabular-nums text-foreground">{activity.lastScore}%</span>
        </span>
      )}
    </div>
  )
}

function ActivityWorkspace({ activity }) {
  const frameRef = useRef(null)
  const [result, setResult] = useState(null)
  const [notice, setNotice] = useState(null)
  const { mutate: syncResult, isPending: isSyncing, error: syncError } = useSyncActivity(activity.id)

  const embedUrl = resolveEmbedUrl(activity.launchUrl)
  const platformName = activity.platform.name

  const checkProgress = useCallback(() => {
    setNotice(null)
    syncResult(undefined, {
      onSuccess: (data) => {
        if (data.status === 'completed') setResult(data.result)
        else setNotice(`${platformName} has not reported a finished result yet. Complete the activity, then check again.`)
      },
    })
  }, [syncResult, platformName])

  useActivityCompletionMessage({
    frameRef,
    frameOrigin: embedUrl?.origin,
    activityId: activity.id,
    onCompleted: checkProgress,
    enabled: !result && !isSyncing,
  })

  if (!embedUrl) {
    return (
      <EmptyState
        icon={ShieldAlert}
        title="This activity cannot be opened here"
        description={`The link from ${platformName} is not a secure address, so SELVIA will not embed it.`}
      />
    )
  }

  if (result) {
    return <ActivityCompletion result={result} onReopen={() => setResult(null)} />
  }

  return (
    <div className="flex flex-col gap-3">
      <p className="flex items-start gap-2 text-xs leading-relaxed text-muted-foreground">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" aria-hidden="true" />
        Complete the activity below. When you finish, your result is sent to SELVIA and your competency and knowledge
        gap update automatically. If nothing happens, select Check progress.
      </p>
      <ActivityFrame
        ref={frameRef}
        src={embedUrl.href}
        title={`${activity.title} in ${platformName}`}
        platformName={platformName}
        onCheckProgress={checkProgress}
        isChecking={isSyncing}
        notice={notice}
        error={syncError ? `Could not check your progress: ${syncError.message}` : null}
      />
    </div>
  )
}

export default function ActivityPage() {
  const { activityId } = useParams()
  const paths = useTutorPaths()
  const activityQuery = useActivity(activityId)
  const activity = activityQuery.data
  const kindMeta = getMeta(ACTIVITY_KIND, activity?.kind)

  return (
    <div className="flex flex-col gap-5">
      <TutorHeader
        icon={kindMeta.icon}
        title={activity?.title ?? 'Learning Activity'}
        description={activity?.summary}
        actions={
          <Button asChild variant="outline" size="sm">
            <Link to={paths.sprintGuidance}>
              <ArrowLeft aria-hidden="true" />
              Sprint Guidance
            </Link>
          </Button>
        }
      />
      <QueryState
        query={activityQuery}
        loading={<LoadingState rows={6} label="Loading activity" />}
        errorTitle="Could not open this activity"
      >
        {(data) => (
          <>
            <ActivityMeta activity={data} />
            <ActivityWorkspace key={data.id} activity={data} />
          </>
        )}
      </QueryState>
    </div>
  )
}
