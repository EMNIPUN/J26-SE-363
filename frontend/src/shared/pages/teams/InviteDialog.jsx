import { useState } from 'react'
import PropTypes from 'prop-types'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { useInviteToTeam } from '../../hooks/useTeams.js'
import { showToast } from '../../utils/toast.jsx'
import EmailListEditor from './EmailListEditor.jsx'

const OUTCOME_TEXT = {
  invited: 'invited',
  reinvited: 'invited again',
  already_member: 'already in the team',
  already_invited: 'already invited',
}

function summarise(results) {
  const counts = {}
  for (const { outcome } of results) counts[outcome] = (counts[outcome] ?? 0) + 1
  return Object.entries(counts)
    .map(([outcome, count]) => `${count} ${OUTCOME_TEXT[outcome]}`)
    .join(', ')
}

export default function InviteDialog({ team, hasLeader, open, onOpenChange }) {
  const invite = useInviteToTeam(team)
  const [students, setStudents] = useState([])
  const [lecturers, setLecturers] = useState([])
  const [chosenLeader, setChosenLeader] = useState(null)

  // A leader can only be named while the team has none.
  const leader = !hasLeader && students.includes(chosenLeader) ? chosenLeader : null

  const close = (next) => {
    onOpenChange(next)
    if (!next) {
      setStudents([])
      setLecturers([])
      setChosenLeader(null)
    }
  }

  const submit = () =>
    invite.mutate(
      { students, lecturers, leader_email: leader },
      {
        onSuccess: ({ results }) => {
          showToast.success(summarise(results))
          close(false)
        },
      },
    )

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Invite people</DialogTitle>
          <DialogDescription>They get an email and can accept in SELVIA.</DialogDescription>
        </DialogHeader>

        <div className="grid gap-5">
          <EmailListEditor
            label="Students"
            emails={students}
            onChange={setStudents}
            leader={leader}
            onLeaderChange={hasLeader ? undefined : setChosenLeader}
            optional
          />
          <EmailListEditor
            label="Other lecturers"
            hint="Lecturers evaluate the team. They do not take part in development."
            emails={lecturers}
            onChange={setLecturers}
            optional
          />
        </div>

        <DialogFooter>
          <Button variant="ghost" onClick={() => close(false)} disabled={invite.isPending}>
            Cancel
          </Button>
          <Button
            onClick={submit}
            disabled={invite.isPending || students.length + lecturers.length === 0}
          >
            {invite.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
            Send invitations
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

InviteDialog.propTypes = {
  team: PropTypes.string.isRequired,
  hasLeader: PropTypes.bool.isRequired,
  open: PropTypes.bool.isRequired,
  onOpenChange: PropTypes.func.isRequired,
}
