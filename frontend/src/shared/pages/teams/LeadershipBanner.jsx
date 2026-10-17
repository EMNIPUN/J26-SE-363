import PropTypes from 'prop-types'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'

/**
 * A leadership offer in progress. The offered student sees Accept and Decline; the leader and the
 * lecturers see who the offer is waiting on, and can withdraw it.
 */
export default function LeadershipBanner({
  pending,
  leader,
  isOfferedToMe,
  canWithdraw,
  busy,
  onRespond,
  onWithdraw,
}) {
  if (!pending) return null

  return (
    <Card className="flex-col gap-3 border-primary/30 bg-primary/5 p-4 sm:flex-row sm:items-center sm:justify-between">
      {isOfferedToMe ? (
        <>
          <p className="text-sm text-foreground">
            {leader ? <strong>{leader.name}</strong> : 'The team'} asked you to take over as team leader.
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              loading={busy === 'decline'}
              disabled={Boolean(busy)}
              onClick={() => onRespond(false)}
            >
              Decline
            </Button>
            <Button
              loading={busy === 'accept'}
              disabled={Boolean(busy)}
              onClick={() => onRespond(true)}
            >
              Accept
            </Button>
          </div>
        </>
      ) : (
        <>
          <p className="text-sm text-foreground">
            Waiting for <strong>{pending.name}</strong> to accept leadership.
          </p>
          {canWithdraw && (
            <Button
              variant="outline"
              loading={busy === 'withdraw'}
              disabled={Boolean(busy)}
              onClick={onWithdraw}
            >
              Withdraw offer
            </Button>
          )}
        </>
      )}
    </Card>
  )
}

LeadershipBanner.propTypes = {
  pending: PropTypes.shape({ name: PropTypes.string }),
  leader: PropTypes.shape({ name: PropTypes.string }),
  isOfferedToMe: PropTypes.bool.isRequired,
  canWithdraw: PropTypes.bool.isRequired,
  // What is being sent right now: 'accept', 'decline', 'withdraw' or nothing.
  busy: PropTypes.string,
  onRespond: PropTypes.func.isRequired,
  onWithdraw: PropTypes.func.isRequired,
}
