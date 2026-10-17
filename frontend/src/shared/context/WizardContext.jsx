import { createContext, useContext, useState, useMemo } from 'react'

const WizardContext = createContext(null)

export const WIZARD_STEPS = [
  { id: 1, stepNumber: 1, title: 'Course & Project', subtitle: 'Batch, module, repo' },
  { id: 2, stepNumber: 2, title: 'Deliverables', subtitle: 'Submissions & weightage' },
  { id: 3, stepNumber: 3, title: 'Sprint Milestones', subtitle: 'Timelines & quality gates' },
  { id: 4, stepNumber: 4, title: 'Team Roster', subtitle: 'CSV / JSON student roster' },
  { id: 5, stepNumber: 5, title: 'Review & Launch', subtitle: 'Pre-flight check & deploy' },
]

export function WizardProvider({ children }) {
  const [currentStep, setCurrentStep] = useState(1)
  const [highestStepReached, setHighestStepReached] = useState(1)
  const [wizardMeta, setWizardMeta] = useState({
    batchId: '',
    moduleName: 'IT3030 - Software Architecture',
    projectTitle: '',
    parsedTeamsCount: 0,
    parsedStudentsCount: 0,
  })
  const [isSubmitting, setIsSubmitting] = useState(false)

  const goToStep = (step) => {
    if (step >= 1 && step <= 5) {
      setCurrentStep(step)
      setHighestStepReached((prev) => Math.max(prev, step))
    }
  }

  const nextStep = () => {
    goToStep(Math.min(5, currentStep + 1))
  }

  const prevStep = () => {
    goToStep(Math.max(1, currentStep - 1))
  }

  const value = useMemo(
    () => ({
      currentStep,
      highestStepReached,
      steps: WIZARD_STEPS,
      wizardMeta,
      setWizardMeta,
      isSubmitting,
      setIsSubmitting,
      goToStep,
      nextStep,
      prevStep,
    }),
    [currentStep, highestStepReached, wizardMeta, isSubmitting]
  )

  return <WizardContext.Provider value={value}>{children}</WizardContext.Provider>
}

export function useWizard() {
  const ctx = useContext(WizardContext)
  return ctx
}
