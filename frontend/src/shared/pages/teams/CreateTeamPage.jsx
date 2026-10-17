import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { useAuth } from '../../auth/useAuth.js'
import { useCreateTeam } from '../../hooks/useTeams.js'
import { showToast } from '../../utils/toast.jsx'
import FormField from '../../components/FormField.jsx'
import PageHeader from '../../components/PageHeader.jsx'
import Stepper from '../../components/Stepper.jsx'
import EmailListEditor from './EmailListEditor.jsx'

const STEPS = ['Team', 'People', 'Review']
const CODE = /^[A-Za-z0-9][A-Za-z0-9._-]{1,62}$/
const thisYear = new Date().getFullYear()

function validateTeam(team) {
  const errors = {}
  if (!team.name.trim()) errors.name = 'Enter a team name.'
  if (team.code.trim() && !CODE.test(team.code.trim())) {
    errors.code = 'Use letters, digits, dots, dashes or underscores.'
  }
  if (!team.term.trim()) errors.term = 'Enter the term, for example 2026-S1.'
  if (!team.projectTitle.trim()) errors.projectTitle = 'Enter the project title.'
  return errors
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

export default function CreateTeamPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const create = useCreateTeam()

  const [step, setStep] = useState(0)
  const [team, setTeam] = useState({ name: '', code: '', term: '', projectTitle: '', projectDescription: '' })
  const [errors, setErrors] = useState({})
  const [students, setStudents] = useState([])
  const [chosenLeader, setChosenLeader] = useState(null)
  const [lecturers, setLecturers] = useState([])
  const [peopleError, setPeopleError] = useState('')

  // If nobody is picked, the first student on the list leads (the Core API does the same).
  const leader = students.includes(chosenLeader) ? chosenLeader : (students[0] ?? null)

  const setField = (name) => (event) => {
    setTeam((current) => ({ ...current, [name]: event.target.value }))
    setErrors((current) => ({ ...current, [name]: undefined }))
  }

  const checkPeople = () => {
    const own = (user.email || '').toLowerCase()
    const both = students.filter((email) => lecturers.includes(email))
    if (both.length) return `${both[0]} is in both lists.`
    if (own && [...students, ...lecturers].includes(own)) return 'You are added as the lecturer automatically.'
    return ''
  }

  const next = () => {
    if (step === 0) {
      const found = validateTeam(team)
      setErrors(found)
      if (Object.keys(found).length) return
    }
    if (step === 1) {
      const problem = checkPeople()
      setPeopleError(problem)
      if (problem) return
    }
    setStep((current) => current + 1)
  }

  const submit = async () => {
    try {
      const result = await create.mutateAsync({
        name: team.name,
        code: team.code || null,
        term: team.term,
        project_title: team.projectTitle,
        project_description: team.projectDescription || null,
        students,
        lecturers,
        leader_email: leader,
      })
      const sent = result.invitations.filter((i) => i.outcome === 'invited').length
      showToast.success(`${result.team.name} created${sent ? `, ${sent} invitation${sent === 1 ? '' : 's'} sent` : ''}`)
      navigate(`/teams/${result.team.code}/members`)
    } catch (error) {
      if (error.code === 'team_code_taken') {
        setErrors({ code: error.message })
        setStep(0)
      }
      // other errors were already shown by the hook
    }
  }

  return (
    <div className="mx-auto grid w-full max-w-2xl gap-6">
      <PageHeader title="Create team" />
      <Stepper steps={STEPS} current={step} />

      <Card className="gap-6 p-5 sm:p-6">
        {step === 0 && (
          <div className="grid gap-4">
            <FormField label="Team name" error={errors.name}>
              {(props) => <Input {...props} value={team.name} onChange={setField('name')} autoFocus />}
            </FormField>
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField
                label="Team code"
                optional
                error={errors.code}
                hint="Used in links. Made from the name if empty."
              >
                {(props) => (
                  <Input {...props} value={team.code} onChange={setField('code')} placeholder="J26-SE-363" />
                )}
              </FormField>
              <FormField label="Term" error={errors.term} hint="A student can be in one team per term.">
                {(props) => (
                  <>
                    <Input
                      {...props}
                      list="term-options"
                      value={team.term}
                      onChange={setField('term')}
                      placeholder={`${thisYear}-S1`}
                    />
                    <datalist id="term-options">
                      <option value={`${thisYear}-S1`} />
                      <option value={`${thisYear}-S2`} />
                      <option value={`${thisYear + 1}-S1`} />
                    </datalist>
                  </>
                )}
              </FormField>
            </div>
            <FormField label="Project title" error={errors.projectTitle}>
              {(props) => <Input {...props} value={team.projectTitle} onChange={setField('projectTitle')} />}
            </FormField>
            <FormField label="Project description" optional>
              {(props) => (
                <Textarea
                  {...props}
                  rows={3}
                  value={team.projectDescription}
                  onChange={setField('projectDescription')}
                />
              )}
            </FormField>
          </div>
        )}

        {step === 1 && (
          <div className="grid gap-6">
            <EmailListEditor
              label="Students"
              hint="Paste emails, separated by lines or commas. They get an invitation to accept."
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

        {step === 2 && (
          <div className="grid gap-4">
            <Summary
              rows={[
                ['Team', `${team.name}${team.code ? ` (${team.code.toUpperCase()})` : ''}`],
                ['Term', team.term],
                ['Project', team.projectTitle],
                ['Students', students.length ? `${students.length} invited` : 'None yet'],
                ['Leader', leader],
                ['Other lecturers', lecturers.length ? lecturers.join(', ') : ''],
              ]}
            />
            <p className="text-sm text-muted-foreground">
              Invitations are sent when you create the team. You can invite more people later.
            </p>
          </div>
        )}

        <div className="flex items-center justify-between">
          <Button
            variant="ghost"
            onClick={() => (step === 0 ? navigate('/home') : setStep((current) => current - 1))}
            disabled={create.isPending}
          >
            {step === 0 ? 'Cancel' : 'Back'}
          </Button>
          {step < STEPS.length - 1 ? (
            <Button onClick={next}>Continue</Button>
          ) : (
            <Button onClick={submit} disabled={create.isPending}>
              {create.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
              Create team
            </Button>
          )}
        </div>
      </Card>
    </div>
  )
}
