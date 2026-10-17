import { Link, useLocation } from 'react-router-dom'
import {
  ArrowLeft,
  CheckCircle2,
  FolderGit2,
  FileSpreadsheet,
  Layers,
  Users2,
  ShieldCheck,
  GraduationCap,
} from 'lucide-react'
import { useWizard } from '../../context/WizardContext.jsx'
import { useScope } from '../../context/useScope.js'

const STEP_ICONS = {
  1: FolderGit2,
  2: FileSpreadsheet,
  3: Layers,
  4: Users2,
  5: ShieldCheck,
}

export default function WizardSidebar({ onNavigate }) {
  const location = useLocation()
  const { selectedGroup } = useScope()

  // Match the active team code directly from current URL path (/teams/:teamCode/...)
  const teamMatch = location.pathname.match(/^\/teams\/([^/]+)/)
  const activeTeamCode = teamMatch ? teamMatch[1] : (selectedGroup?.code || 'J26-SE-363')
  const dashboardPath = `/teams/${activeTeamCode}/app`

  const wizard = useWizard()

  const currentStep = wizard?.currentStep || 1
  const highestStepReached = wizard?.highestStepReached || 1
  const steps = wizard?.steps || []
  const wizardMeta = wizard?.wizardMeta || {}

  const handleExit = () => {
    if (onNavigate) onNavigate()
    if (wizard?.goToStep) wizard.goToStep(1)
  }

  const handleStepClick = (stepNum) => {
    if (stepNum <= highestStepReached && wizard?.goToStep) {
      wizard.goToStep(stepNum)
      if (onNavigate) onNavigate()
    }
  }

  const completionPct = Math.round((currentStep / 5) * 100)

  return (
    <div className="flex flex-col h-full bg-sidebar text-sidebar-foreground select-none">
      {/* Top Header: Exit and Mode */}
      <div className="p-4 border-b border-sidebar-border space-y-3">
        <Link
          to={dashboardPath}
          onClick={handleExit}
          className="flex items-center gap-2 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors group cursor-pointer"
        >
          <ArrowLeft className="h-3.5 w-3.5 transition-transform group-hover:-translate-x-0.5" />
          <span>Exit to Dashboard</span>
        </Link>

        <div>
          <div className="flex items-center gap-1.5">
            <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-mono tracking-wider font-semibold uppercase bg-muted text-muted-foreground border border-border">
              Setup Wizard
            </span>
          </div>
          <h2 className="text-sm font-semibold tracking-tight text-foreground mt-1.5 truncate">
            {wizardMeta.projectTitle || 'New Project & Roster'}
          </h2>
          <p className="text-[11px] text-muted-foreground truncate">
            {wizardMeta.batchId ? `Batch: ${wizardMeta.batchId}` : 'SLIIT Academic Project'}
          </p>
        </div>
      </div>

      {/* Stepper Navigation */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        <p className="px-3 text-[10px] font-mono uppercase tracking-wider text-muted-foreground/70 mb-2">
          Provisioning Steps
        </p>

        {steps.map((s) => {
          const Icon = STEP_ICONS[s.stepNumber] || FolderGit2
          const isActive = currentStep === s.stepNumber
          const isDone = currentStep > s.stepNumber
          const isClickable = s.stepNumber <= highestStepReached

          return (
            <button
              key={s.id}
              type="button"
              disabled={!isClickable}
              onClick={() => handleStepClick(s.stepNumber)}
              className={`w-full flex items-start gap-3 p-3 rounded-lg text-left transition-all duration-150 ${
                isActive
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium shadow-2xs border border-sidebar-border'
                  : isClickable
                  ? 'hover:bg-sidebar-accent/50 text-sidebar-foreground cursor-pointer'
                  : 'opacity-40 cursor-not-allowed text-muted-foreground'
              }`}
            >
              {/* Step indicator circle / icon */}
              <div
                className={`mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-xs font-mono transition-colors ${
                  isDone
                    ? 'bg-foreground text-background font-semibold'
                    : isActive
                    ? 'border-2 border-foreground text-foreground font-bold'
                    : 'border border-border text-muted-foreground'
                }`}
              >
                {isDone ? <CheckCircle2 className="h-4 w-4" /> : s.stepNumber}
              </div>

              {/* Step details */}
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-1">
                  <span className="text-xs font-medium truncate">{s.title}</span>
                  {isActive && (
                    <span className="h-1.5 w-1.5 rounded-full bg-foreground shrink-0" />
                  )}
                </div>
                <p className="text-[11px] text-muted-foreground truncate mt-0.5">
                  {s.subtitle}
                </p>
              </div>
            </button>
          )
        })}
      </div>

      {/* Progress & Policy Footer */}
      <div className="p-4 border-t border-sidebar-border bg-sidebar/50 space-y-3">
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-[11px] font-mono text-muted-foreground">
            <span>Progress</span>
            <span className="font-semibold text-foreground">{completionPct}%</span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
            <div
              className="h-full bg-foreground transition-all duration-300 ease-out rounded-full"
              style={{ width: `${completionPct}%` }}
            />
          </div>
        </div>

        <div className="p-2.5 rounded-md bg-muted/30 border border-border/60 text-[11px] text-muted-foreground space-y-1">
          <div className="flex items-center gap-1.5 text-foreground font-medium text-[11px]">
            <GraduationCap className="h-3.5 w-3.5 text-muted-foreground shrink-0" />
            <span>SLIIT Academic Scope</span>
          </div>
          <p className="leading-snug text-[10px] text-muted-foreground">
            Teams and students are scoped per batch with unique membership enforcement.
          </p>
        </div>
      </div>
    </div>
  )
}
