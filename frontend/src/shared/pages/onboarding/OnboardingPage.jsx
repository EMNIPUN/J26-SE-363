import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '../../auth/useAuth.js'
import { accountService } from '../../services/accountService.js'
import { isGithubUsername } from '../../utils/emails.js'
import SelviaLogo from '../../components/SelviaLogo.jsx'
import Stepper from '../../components/Stepper.jsx'
import ThemeToggle from '../../components/ThemeToggle.jsx'
import OnboardingAside from './OnboardingAside.jsx'
import { AccountTypeStep, DetailsStep, ReviewStep } from './steps.jsx'

const STEPS = [
  { label: 'Account type', hint: 'Student or lecturer' },
  { label: 'Your details', hint: 'A few basics about you' },
  { label: 'Review', hint: 'Confirm and finish' },
]
const TITLES = ['How will you use SELVIA?', 'Tell us about yourself', 'Review and agree']

function validateDetails(accountType, values) {
  const errors = {}
  if (!values.displayName.trim()) errors.displayName = 'Enter your name.'
  if (accountType === 'student') {
    if (!values.githubUsername.trim()) errors.githubUsername = 'Enter your GitHub username.'
    else if (!isGithubUsername(values.githubUsername)) {
      errors.githubUsername = 'That is not a valid GitHub username.'
    }
  }
  return errors
}

// Server answers that belong to a field on the details step.
const FIELD_ERRORS = {
  github_username_taken: 'githubUsername',
  student_number_taken: 'studentNumber',
}

export default function OnboardingPage() {
  const { account, user, setAccount, refreshAccount, logout } = useAuth()
  const [step, setStep] = useState(0)
  const [accountType, setAccountType] = useState('')
  const [values, setValues] = useState({
    displayName: account?.name ?? '',
    institution: '',
    githubUsername: '',
    studentNumber: '',
    department: '',
    title: '',
  })
  const [errors, setErrors] = useState({})
  const [accepted, setAccepted] = useState(false)
  const [submitError, setSubmitError] = useState('')

  const finish = useMutation({
    mutationFn: accountService.completeOnboarding,
    // Once the account is onboarded, RequireAccount moves the person on to where they were going.
    onSuccess: setAccount,
    onError: (error) => {
      const field = FIELD_ERRORS[error.code]
      if (field) {
        setErrors({ [field]: error.message })
        setStep(1)
      } else if (error.code === 'consent_outdated') {
        refreshAccount()
        setSubmitError(error.message)
      } else {
        setSubmitError(error.message)
      }
    },
  })

  const setValue = (name, value) => {
    setValues((current) => ({ ...current, [name]: value }))
    setErrors((current) => ({ ...current, [name]: undefined }))
  }

  const next = () => {
    if (step === 1) {
      const found = validateDetails(accountType, values)
      setErrors(found)
      if (Object.keys(found).length) return
    }
    setStep((current) => current + 1)
  }

  const submit = () => {
    setSubmitError('')
    finish.mutate({
      account_type: accountType,
      display_name: values.displayName,
      institution: values.institution,
      ...(accountType === 'student'
        ? { github_username: values.githubUsername, student_number: values.studentNumber }
        : { department: values.department, title: values.title }),
      accept_terms: accepted,
      consent_version: account?.current_consent_version,
    })
  }

  const canContinue = step === 0 ? Boolean(accountType) : true

  return (
    <div className="grid min-h-screen bg-background text-foreground lg:grid-cols-[5fr_6fr]">
      <OnboardingAside steps={STEPS} current={step} />

      <div className="flex min-h-screen flex-col">
        <header className="flex h-14 items-center justify-between px-4 sm:px-6">
          <SelviaLogo size={28} showText showTagline={false} className="lg:invisible" />
          <div className="flex items-center gap-1">
            <ThemeToggle />
            <Button variant="ghost" size="sm" onClick={logout}>
              Sign out
            </Button>
          </div>
        </header>

        <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center gap-6 px-4 py-8">
          <div className="grid gap-1">
            <p className="text-sm text-muted-foreground">
              Step {step + 1} of {STEPS.length}
              {user?.name ? ` · Welcome, ${user.name.split(' ')[0]}` : ''}
            </p>
            <h1 className="text-2xl font-semibold tracking-tight">{TITLES[step]}</h1>
          </div>

          <div className="lg:hidden">
            <Stepper steps={STEPS.map((item) => item.label)} current={step} />
          </div>

          {step === 0 && <AccountTypeStep value={accountType} onChange={setAccountType} />}
          {step === 1 && (
            <DetailsStep
              accountType={accountType}
              values={values}
              errors={errors}
              onChange={setValue}
            />
          )}
          {step === 2 && (
            <ReviewStep
              accountType={accountType}
              values={values}
              accepted={accepted}
              onAcceptedChange={setAccepted}
              error={submitError}
            />
          )}

          <div className="flex items-center justify-between">
            <Button
              variant="ghost"
              onClick={() => setStep((current) => current - 1)}
              disabled={step === 0 || finish.isPending}
              className={step === 0 ? 'invisible' : undefined}
            >
              Back
            </Button>
            {step < STEPS.length - 1 ? (
              <Button onClick={next} disabled={!canContinue}>
                Continue
              </Button>
            ) : (
              <Button onClick={submit} disabled={!accepted || finish.isPending}>
                {finish.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
                Finish setup
              </Button>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}
