import { useState } from 'react'
import PropTypes from 'prop-types'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { useAuth } from '../../auth/useAuth.js'
import { useCreateTerm, useTerms } from '../../hooks/useTerms.js'
import { teamKeys } from '../../hooks/useTeams.js'
import { teamService } from '../../services/teamService.js'
import { showToast } from '../../utils/toast.jsx'
import Badge from '../../components/Badge.jsx'
import FormField from '../../components/FormField.jsx'
import PageHeader from '../../components/PageHeader.jsx'
import Stepper from '../../components/Stepper.jsx'
import TermCombobox from '../../components/TermCombobox.jsx'
import EmailListEditor from './EmailListEditor.jsx'

const STEPS = ['Team', 'Project', 'People', 'Review']
const CODE = /^[A-Za-z0-9][A-Za-z0-9._-]{1,62}$/

const emailsOf = (team, role) =>
  (team?.invitations ?? [])
    .filter((invitation) => invitation.status === 'pending' && invitation.role === role)
    .map((invitation) => invitation.email)

// Carry on where the person stopped: the first step that has nothing saved yet.
function firstOpenStep(team) {
  if (!team) return 0
  if (!team.project) return 1
  return team.invitations.some((invitation) => invitation.status === 'pending') ? 3 : 2
}

function Summary({ rows }) {
  return (
    <dl className="divide-y divide-border rounded-lg border border-border text-sm">
      {rows
        .filter(([, value]) => value)
        .map(([label, value]) => (
          <div key={label} className="flex justify-between gap-4 px-3 py-2">
            <dt className="shrink-0 text-muted-foreground">{label}</dt>
            <dd className="text-right font-medium text-foreground">{value}</dd>
          </div>
        ))}
    </dl>
  )
}

Summary.propTypes = { rows: PropTypes.arrayOf(PropTypes.array).isRequired }

/**
 * Sets a team up one step at a time. Every "Continue" saves that step in the Core API, so the
 * team exists (as "pending") from the first step and the person can leave and come back. Nobody
 * else sees it, and no invitation is emailed, until the last step.
 */
export default function TeamSetupWizard({ team = null }) {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const terms = useTerms()
  const createTerm = useCreateTerm()

  // What the Core API has saved so far (null until step 1 is done).
  const [saved, setSaved] = useState(team)
  const [step, setStep] = useState(firstOpenStep(team))
  const [busy, setBusy] = useState(false)
  const [discarding, setDiscarding] = useState(false)

  const [values, setValues] = useState({
    name: team?.name ?? '',
    code: team?.code ?? '',
    term: team?.term ?? '',
    title: team?.project?.title ?? '',
    description: team?.project?.description ?? '',
  })
  const [errors, setErrors] = useState({})
  const [students, setStudents] = useState(emailsOf(team, 'member'))
  const [lecturers, setLecturers] = useState(emailsOf(team, 'lecturer'))
  const [chosenLeader, setChosenLeader] = useState(
    team?.invitations.find((i) => i.status === 'pending' && i.as_leader)?.email ?? null,
  )
  const [peopleError, setPeopleError] = useState('')

  // If nobody is picked, the first student on the list leads (the Core API does the same).
  const leader = students.includes(chosenLeader) ? chosenLeader : (students[0] ?? null)
  const code = saved?.code

  const setField = (name) => (event) => {
    setValues((current) => ({ ...current, [name]: event.target.value }))
    setErrors((current) => ({ ...current, [name]: undefined }))
  }

  const remember = (next) => {
    setSaved(next)
    queryClient.setQueryData(teamKeys.detail(next.code), next)
    queryClient.invalidateQueries({ queryKey: teamKeys.mine })
    return next
  }

  const addTerm = async (name) => {
    try {
      return await createTerm.mutateAsync(name)
    } catch (error) {
      showToast.error(error.message)
      return null
    }
  }

  // --- what each step asks and saves --------------------------------------------------------

  const validate = () => {
    const found = {}
    if (step === 0) {
      if (!values.name.trim()) found.name = 'Enter a team name.'
      if (!code && values.code.trim() && !CODE.test(values.code.trim())) {
        found.code = 'Use letters, digits, dots, dashes or underscores.'
      }
      if (!values.term.trim()) found.term = 'Choose a term, or type a new one to add it.'
      else if (terms.data && !terms.data.some((t) => t.toLowerCase() === values.term.trim().toLowerCase())) {
        found.term = 'Pick the term from the list, or choose "Add new" to add it.'
      }
    }
    if (step === 1 && !values.title.trim()) found.title = 'Enter the project title.'
    setErrors(found)

    if (step === 2) {
      const own = (user.email || '').toLowerCase()
      const both = students.filter((email) => lecturers.includes(email))
      let problem = ''
      if (both.length) problem = `${both[0]} is in both lists.`
      else if (own && [...students, ...lecturers].includes(own)) {
        problem = 'You are added as the lecturer automatically.'
      }
      setPeopleError(problem)
      if (problem) return false
    }
    return Object.keys(found).length === 0
  }

  const save = async () => {
    if (step === 0) {
      if (!saved) {
        const created = await teamService.createTeam({
          name: values.name,
          code: values.code.trim() || null,
          term: values.term,
        })
        remember(created)
        // The address now names the draft, so a reload or a link comes back to it.
        navigate(`/teams/new/${created.code}`, { replace: true })
        return
      }
      const changes = {}
      if (values.name.trim() !== saved.name) changes.name = values.name
      if (values.term !== saved.term) changes.term = values.term
      if (Object.keys(changes).length) remember(await teamService.updateTeam(code, changes))
    } else if (step === 1) {
      remember(
        await teamService.saveProject(code, {
          title: values.title,
          description: values.description || null,
        }),
      )
    } else if (step === 2) {
      // Withdraw whoever was taken off the lists, then (re)send the lists: it is safe to repeat.
      const wanted = new Set([...students, ...lecturers])
      for (const invitation of saved.invitations) {
        if (invitation.status === 'pending' && !wanted.has(invitation.email)) {
          await teamService.withdrawInvitation(code, invitation.id)
        }
      }
      if (wanted.size) {
        await teamService.invite(code, { students, lecturers, leader_email: leader })
      }
      remember(await teamService.getTeam(code))
    }
  }

  const finish = async () => {
    const done = await teamService.activateTeam(code)
    // The team list must say "not pending" before the team's pages open, or they send the person
    // straight back here. Storing the opened team then ends this page: TeamSetupPage sends a team
    // that is no longer pending on to its members page.
    await queryClient.invalidateQueries({ queryKey: teamKeys.mine })
    queryClient.invalidateQueries({ queryKey: teamKeys.invitations })
    queryClient.setQueryData(teamKeys.detail(done.code), done)
    const sent = students.length + lecturers.length
    showToast.success(`${done.name} created${sent ? `, ${sent} invitation${sent === 1 ? '' : 's'} sent` : ''}`)
  }

  const fail = (error) => {
    if (error.code === 'team_code_taken') {
      setErrors({ code: error.message })
      setStep(0)
    } else if (error.code === 'unknown_term') {
      setErrors({ term: error.message })
      setStep(0)
    } else {
      showToast.error(error.message)
    }
  }

  const next = async () => {
    if (step < STEPS.length - 1 && !validate()) return
    setBusy(true)
    try {
      if (step === STEPS.length - 1) await finish()
      else {
        await save()
        setStep((current) => current + 1)
      }
    } catch (error) {
      fail(error)
    } finally {
      setBusy(false)
    }
  }

  const discard = async () => {
    setBusy(true)
    try {
      await teamService.discardTeam(code)
      queryClient.removeQueries({ queryKey: teamKeys.detail(code) })
      queryClient.invalidateQueries({ queryKey: teamKeys.mine })
      showToast.success('Team discarded')
      navigate('/teams', { replace: true })
    } catch (error) {
      showToast.error(error.message)
      setBusy(false)
    }
  }

  const last = step === STEPS.length - 1

  return (
    <div className="mx-auto grid w-full max-w-2xl gap-6">
      <PageHeader
        title="Create team"
        description={code ? 'Saved as you go. You can leave and carry on later.' : undefined}
        actions={code && <Badge tone="warning">Pending</Badge>}
      />
      <Stepper steps={STEPS} current={step} />

      <Card className="gap-6 p-5 sm:p-6">
        {step === 0 && (
          <div className="grid gap-4">
            <FormField label="Team name" error={errors.name}>
              {(props) => <Input {...props} value={values.name} onChange={setField('name')} autoFocus />}
            </FormField>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                label="Team code"
                optional
                error={errors.code}
                hint={code ? 'The code cannot change.' : 'Used in links. Made from the name if empty.'}
              >
                {(props) => (
                  <Input
                    {...props}
                    value={values.code}
                    onChange={setField('code')}
                    placeholder="J26-SE-363"
                    disabled={Boolean(code)}
                  />
                )}
              </FormField>
              <FormField label="Term" error={errors.term} hint="A student can be in one team per term.">
                {(props) => (
                  <TermCombobox
                    {...props}
                    terms={terms.data ?? []}
                    value={values.term}
                    onChange={(term) => {
                      setValues((current) => ({ ...current, term }))
                      setErrors((current) => ({ ...current, term: undefined }))
                    }}
                    onCreate={addTerm}
                    creating={createTerm.isPending}
                  />
                )}
              </FormField>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="grid gap-4">
            <FormField label="Project title" error={errors.title}>
              {(props) => <Input {...props} value={values.title} onChange={setField('title')} autoFocus />}
            </FormField>
            <FormField label="Project description" optional>
              {(props) => (
                <Textarea {...props} rows={4} value={values.description} onChange={setField('description')} />
              )}
            </FormField>
          </div>
        )}

        {step === 2 && (
          <div className="grid gap-6">
            <EmailListEditor
              label="Students"
              hint="Type or paste emails and press space after each. The crown marks the team leader."
              emails={students}
              onChange={setStudents}
              leader={leader}
              onLeaderChange={setChosenLeader}
              optional
            />
            <EmailListEditor
              label="Other lecturers"
              hint="Lecturers evaluate the team. They do not take part in development."
              emails={lecturers}
              onChange={setLecturers}
              optional
            />
            {peopleError && (
              <p role="alert" className="text-sm text-destructive">
                {peopleError}
              </p>
            )}
          </div>
        )}

        {step === 3 && (
          <div className="grid gap-4">
            <Summary
              rows={[
                ['Team', `${values.name}${code ? ` (${code})` : ''}`],
                ['Term', values.term],
                ['Project', values.title],
                ['Students', students.length ? `${students.length} to invite` : 'None yet'],
                ['Leader', leader],
                ['Other lecturers', lecturers.length ? lecturers.join(', ') : ''],
              ]}
            />
            <p className="text-sm text-muted-foreground">
              Invitations are emailed when you create the team. You can invite more people later.
            </p>
          </div>
        )}

        <div className="flex items-center justify-between gap-2">
          <Button
            variant="ghost"
            onClick={() => (step === 0 ? navigate('/home') : setStep((current) => current - 1))}
            disabled={busy}
          >
            {step === 0 ? (code ? 'Close' : 'Cancel') : 'Back'}
          </Button>
          <div className="flex items-center gap-2">
            {code && (
              <Button variant="ghost" className="text-destructive" onClick={() => setDiscarding(true)} disabled={busy}>
                Discard
              </Button>
            )}
            <Button onClick={next} loading={busy && !discarding}>
              {last ? 'Create team' : 'Continue'}
            </Button>
          </div>
        </div>
      </Card>

      <AlertDialog open={discarding} onOpenChange={setDiscarding}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Discard this team?</AlertDialogTitle>
            <AlertDialogDescription>
              What you saved so far is deleted. Nobody has been invited yet.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep it</AlertDialogCancel>
            <AlertDialogAction
              loading={busy}
              onClick={(event) => {
                event.preventDefault() // stay open, with the ring, until the answer comes
                discard()
              }}
            >
              Discard
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

TeamSetupWizard.propTypes = { team: PropTypes.object }
