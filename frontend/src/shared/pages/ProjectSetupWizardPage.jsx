import { useState, useMemo, useEffect } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import BatchCombobox from '../components/roster/BatchCombobox'
import { useBatches, useCreateProject } from '../hooks/useCohorts'
import { useBulkImportTeams } from '../hooks/useTeamManagement'
import { useWizard } from '../context/WizardContext.jsx'
import { useScope } from '../context/useScope.js'
import {
  Check,
  ChevronRight,
  ChevronLeft,
  BookOpen,
  FileText,
  Flag,
  Users,
  CheckCircle2,
  AlertCircle,
  Plus,
  Trash2,
  Layers,
  Sparkles,
  Info,
  ArrowLeft,
  Rocket,
  ShieldAlert,
} from 'lucide-react'
import { toast } from 'sonner'

const TEMPLATES = {
  se: `1. Software Requirements Specification (SRS)
   - Scope: Decomposed functional and non-functional requirements with acceptance criteria.
   - Format: PDF Document & Markdown.
   - Weightage: 20%

2. Software Architecture & Design Document (SAD)
   - Scope: High-level architectural diagrams (C4 model), component interactions, and DB schema.
   - Format: PDF & UML Diagrams.
   - Weightage: 20%

3. Production Source Code & Cloud Deployment
   - Scope: Working prototype with automated test suite, clean Git history, and CI/CD.
   - Format: GitHub Repository.
   - Weightage: 40%

4. Final Technical Report & Defense
   - Scope: Comprehensive project thesis, individual contribution audit, and live demonstration.
   - Format: Report & Viva Voce.
   - Weightage: 20%`,

  thesis: `1. Research Proposal & Literature Review
   - Scope: Problem domain synthesis, gap identification, and methodology justification.
   - Format: Academic Proposal Document.
   - Weightage: 25%

2. System Design & Algorithmic Modeling
   - Scope: Mathematical model, baseline comparisons, and architectural blueprint.
   - Format: Technical Report.
   - Weightage: 25%

3. Experimental Validation & Benchmark Results
   - Scope: Reproducible empirical tests, performance metrics, and ablation analysis.
   - Format: Code Repository & Data Notebooks.
   - Weightage: 30%

4. Final Research Thesis & Oral Defense
   - Scope: Complete academic manuscript and examination panel defense.
   - Format: Thesis PDF & Oral Defense.
   - Weightage: 20%`,
}

const DEFAULT_MILESTONES = [
  {
    id: 'ms-1',
    title: 'Milestone 1: SRS Quality Gate',
    sprint: 'Sprint 1',
    due_week: 'Week 4',
    target_gate: 'SRS Quality Gate ≥ 80%',
    description: 'Requirements ambiguity check and baseline architectural arbitration.',
  },
  {
    id: 'ms-2',
    title: 'Milestone 2: Mid-Sprint Evaluation',
    sprint: 'Sprint 2',
    due_week: 'Week 8',
    target_gate: 'Active Commits & 80% Standup Attendance',
    description: 'Progress evaluation against decomposed user story estimates.',
  },
  {
    id: 'ms-3',
    title: 'Milestone 3: Security & Code Quality Gate',
    sprint: 'Sprint 3',
    due_week: 'Week 11',
    target_gate: 'Zero Critical Vulnerabilities (AEGIS Scan)',
    description: 'Automated vulnerability audit and code remediation review.',
  },
  {
    id: 'ms-4',
    title: 'Milestone 4: Final Product Defense',
    sprint: 'Sprint 4',
    due_week: 'Week 14',
    target_gate: 'Comprehensive Evaluation ≥ 85%',
    description: 'Live demonstration, thesis submission, and individual contribution grading.',
  },
]

const SAMPLE_ROSTER = [
  {
    team_code: 'J26-SE-363',
    name: 'SELVIA Platform',
    leader_email: 'it210001@my.sliit.lk',
    leader_student_id: 'IT210001',
    leader_name: 'Sadeesha N.',
    member_emails: [
      'it210002@my.sliit.lk',
      'it210003@my.sliit.lk',
      'it210004@my.sliit.lk',
    ],
  },
  {
    team_code: 'G02-SE-304',
    name: 'CloudScale Engine',
    leader_email: 'it210045@my.sliit.lk',
    leader_student_id: 'IT210045',
    leader_name: 'Kavindu P.',
    member_emails: [
      'it210046@my.sliit.lk',
      'it210047@my.sliit.lk',
    ],
  },
  {
    team_code: 'G03-SE-304',
    name: 'AuthGate Sentinel',
    leader_email: 'it210090@my.sliit.lk',
    leader_student_id: 'IT210090',
    leader_name: 'Anuki D.',
    member_emails: [
      'it210091@my.sliit.lk',
      'it210001@my.sliit.lk', // Demo duplicate student to illustrate academic rule
    ],
  },
]

export default function ProjectSetupWizardPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { teamId } = useParams()
  const { selectedGroup } = useScope()

  // Match the active team code directly from current URL path (/teams/:teamCode/...)
  const teamMatch = location.pathname.match(/^\/teams\/([^/]+)/)
  const activeTeamCode = teamMatch ? teamMatch[1] : (teamId || selectedGroup?.code || 'J26-SE-363')
  const dashboardPath = `/teams/${activeTeamCode}/app`

  const wizard = useWizard()
  const currentStep = wizard?.currentStep || 1
  const setCurrentStep = wizard?.goToStep || (() => {})

  // Step 1: Course & Project
  const { data: batches = [] } = useBatches()
  const [batchId, setBatchId] = useState('')
  const [moduleName, setModuleName] = useState('IT3030 - Software Architecture')
  const [projectName, setProjectName] = useState('Enterprise Cloud Microservices')
  const [defaultRepoUrl, setDefaultRepoUrl] = useState('')

  // Step 2: Course Deliverables Text
  const [deliverablesText, setDeliverablesText] = useState(TEMPLATES.se)

  // Step 3: Sprint Milestones
  const [milestones, setMilestones] = useState(DEFAULT_MILESTONES)
  const [milestoneNotes, setMilestoneNotes] = useState('')

  // Step 4: Teams Roster
  const [rosterRaw, setRosterRaw] = useState(JSON.stringify(SAMPLE_ROSTER, null, 2))
  const [rosterParseError, setRosterParseError] = useState(null)

  // Step 5: Submission & Result
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [setupResult, setSetupResult] = useState(null)

  // Mutations
  const createProjectMutation = useCreateProject()
  const bulkImportMutation = useBulkImportTeams()

  // Auto-select first active batch if none selected
  const activeBatchId = useMemo(() => {
    if (batchId) return batchId
    if (batches.length > 0) return batches[0].id
    return 'batch-2026-y4s1'
  }, [batchId, batches])

  // Parse and validate roster
  const parsedTeamsData = useMemo(() => {
    try {
      const parsed = JSON.parse(rosterRaw)
      if (Array.isArray(parsed)) return parsed
      return null
    } catch {
      return null
    }
  }, [rosterRaw])

  // Sync metadata with WizardContext for sidebar display
  useEffect(() => {
    if (wizard?.setWizardMeta) {
      wizard.setWizardMeta({
        batchId: activeBatchId,
        moduleName,
        projectTitle: projectName,
        parsedTeamsCount: parsedTeamsData?.length || 0,
        parsedStudentsCount: parsedTeamsData?.reduce(
          (acc, t) => acc + 1 + (t.member_emails?.length || 0),
          0
        ) || 0,
      })
    }
  }, [wizard, activeBatchId, moduleName, projectName, parsedTeamsData])

  // Client-side Academic Constraint Analysis
  const rosterConflictAnalysis = useMemo(() => {
    if (!parsedTeamsData) return { duplicates: [], totalStudents: 0 }

    const studentMap = new Map()
    let total = 0

    parsedTeamsData.forEach((team) => {
      const allEmails = [
        team.leader_email,
        ...(Array.isArray(team.member_emails) ? team.member_emails : []),
      ].filter(Boolean)

      allEmails.forEach((email) => {
        total++
        const normalized = email.toLowerCase().trim()
        if (!studentMap.has(normalized)) {
          studentMap.set(normalized, [])
        }
        studentMap.get(normalized).push(team.team_code)
      })
    })

    const duplicates = []
    studentMap.forEach((teamCodes, email) => {
      if (teamCodes.length > 1) {
        duplicates.push({ email, teams: teamCodes })
      }
    })

    return { duplicates, totalStudents: total }
  }, [parsedTeamsData])

  // Navigation handlers
  const handleNextFromStep1 = (e) => {
    if (e) e.preventDefault()
    if (!moduleName.trim()) {
      toast.error('Course module name is required.')
      return
    }
    setCurrentStep(2)
  }

  const handleNextFromStep2 = () => {
    setCurrentStep(3)
  }

  const handleAddMilestone = () => {
    const nextIdx = milestones.length + 1
    setMilestones([
      ...milestones,
      {
        id: `ms-${Date.now()}`,
        title: `Milestone ${nextIdx}: Delivery Checkpoint`,
        sprint: `Sprint ${nextIdx}`,
        due_week: `Week ${nextIdx * 3}`,
        target_gate: 'Code Review & Test Pass',
        description: 'Scheduled sprint delivery review.',
      },
    ])
  }

  const handleUpdateMilestone = (id, field, value) => {
    setMilestones(
      milestones.map((m) => (m.id === id ? { ...m, [field]: value } : m))
    )
  }

  const handleRemoveMilestone = (id) => {
    if (milestones.length <= 1) {
      toast.error('At least one milestone is required.')
      return
    }
    setMilestones(milestones.filter((m) => m.id !== id))
  }

  const handleNextFromStep4 = () => {
    setRosterParseError(null)
    try {
      const parsed = JSON.parse(rosterRaw)
      if (!Array.isArray(parsed) || parsed.length === 0) {
        setRosterParseError('Roster must be a non-empty array of team objects.')
        return
      }
      for (const t of parsed) {
        if (!t.team_code || !t.name || !t.leader_email) {
          setRosterParseError('Each team must have a team_code, name, and leader_email.')
          return
        }
      }
      setCurrentStep(5)
    } catch (err) {
      setRosterParseError(`Invalid JSON format: ${err.message}`)
    }
  }

  // Atomic Provisioning
  const handleCompleteSetup = async () => {
    setIsSubmitting(true)
    setSetupResult(null)

    try {
      const milestonesSummary = milestones
        .map((m) => `• ${m.title} (${m.sprint}, ${m.due_week}) — Gate: ${m.target_gate}`)
        .join('\n')

      const combinedDescription = [
        deliverablesText.trim() ? `Course Deliverables & Assessment Brief:\n${deliverablesText.trim()}` : '',
        milestoneNotes.trim() ? `Milestone Supervision Notes:\n${milestoneNotes.trim()}` : '',
        'Sprint Milestones & Delivery Gates:\n' + milestonesSummary,
      ].filter(Boolean).join('\n\n')

      // 1. Create the Course Project
      const projectPayload = {
        batch_id: activeBatchId,
        module_name: moduleName.trim(),
        name: projectName.trim() || moduleName.trim(),
        default_repo_url: defaultRepoUrl.trim() || null,
        description: combinedDescription || null,
      }
      const createdProject = await createProjectMutation.mutateAsync(projectPayload)

      // 2. Bulk-import the Teams with the new project_id
      const teamsPayload = {
        batch_id: activeBatchId,
        project_id: createdProject.id,
        teams: parsedTeamsData,
      }
      const bulkResult = await bulkImportMutation.mutateAsync(teamsPayload)

      setSetupResult({
        project: createdProject,
        bulk: bulkResult,
      })

      toast.success('Course project and team roster successfully provisioned!')
    } catch (err) {
      toast.error(err.message || 'Setup process encountered an error.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleReturnToDashboard = () => {
    if (wizard?.goToStep) wizard.goToStep(1)
    navigate(dashboardPath)
  }

  return (
    <div className="max-w-5xl mx-auto pb-24 space-y-6">
      {/* Top Breadcrumb & Page Heading */}
      <div className="border-b border-border pb-5">
        <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground mb-2">
          <Link
            to={dashboardPath}
            onClick={() => wizard?.goToStep && wizard.goToStep(1)}
            className="hover:text-foreground transition-colors cursor-pointer"
          >
            Instructor Portal
          </Link>
          <span>/</span>
          <span>Projects</span>
          <span>/</span>
          <span className="text-foreground font-semibold">New Project & Roster</span>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              {currentStep === 1 && 'Course & Project Details'}
              {currentStep === 2 && 'Course Deliverables & Weightage'}
              {currentStep === 3 && 'Sprint Milestones & Quality Gates'}
              {currentStep === 4 && 'Student & Team Allocations'}
              {currentStep === 5 && 'Pre-Flight Review & Launch'}
            </h1>
            <p className="text-xs text-muted-foreground mt-1">
              {currentStep === 1 && 'Select an academic cohort batch and configure course repository baselines.'}
              {currentStep === 2 && 'Define submission deliverables, guidelines, and evaluation weightages.'}
              {currentStep === 3 && 'Schedule sprint deadlines, progress gates, and supervisor checkpoints.'}
              {currentStep === 4 && 'Import team rosters via JSON/CSV with automatic membership conflict validation.'}
              {currentStep === 5 && 'Verify configurations before atomic project and team provisioning.'}
            </p>
          </div>

          <Badge variant="outline" className="h-6 text-[11px] font-mono self-start sm:self-auto">
            Step {currentStep} of 5
          </Badge>
        </div>
      </div>

      {/* ======================================================================= */}
      {/* STEP 1: COURSE & PROJECT                                                */}
      {/* ======================================================================= */}
      {currentStep === 1 && (
        <form onSubmit={handleNextFromStep1} className="space-y-6 animate-fade-rise">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-2 md:col-span-2">
              <label className="text-xs font-semibold text-foreground flex items-center justify-between">
                <span>Academic Batch / Cohort <span className="text-destructive">*</span></span>
                <span className="text-[11px] font-normal text-muted-foreground">Search or create batch</span>
              </label>
              <BatchCombobox
                value={activeBatchId}
                onChange={setBatchId}
                className="w-full"
              />
              <p className="text-[11px] text-muted-foreground">
                All projects, student rosters, and assessments will be isolated to this batch.
              </p>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-foreground">
                Module Code & Name <span className="text-destructive">*</span>
              </label>
              <Input
                value={moduleName}
                onChange={(e) => setModuleName(e.target.value)}
                placeholder="e.g. IT3030 - Software Architecture"
                className="h-10 text-xs font-mono"
                required
              />
              <p className="text-[11px] text-muted-foreground">SLIIT Academic curriculum module code.</p>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-foreground">
                Project Title / Theme
              </label>
              <Input
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
                placeholder="e.g. Enterprise Cloud Microservices"
                className="h-10 text-xs"
              />
              <p className="text-[11px] text-muted-foreground">Project headline displayed across student dashboards.</p>
            </div>

            <div className="space-y-2 md:col-span-2">
              <label className="text-xs font-semibold text-foreground">
                Default Starter Repository URL
              </label>
              <Input
                value={defaultRepoUrl}
                onChange={(e) => setDefaultRepoUrl(e.target.value)}
                placeholder="https://github.com/sliit-org/starter-template.git"
                className="h-10 text-xs font-mono"
              />
              <p className="text-[11px] text-muted-foreground">Optional template repository for automated team forks.</p>
            </div>
          </div>
        </form>
      )}

      {/* ======================================================================= */}
      {/* STEP 2: COURSE DELIVERABLES                                             */}
      {/* ======================================================================= */}
      {currentStep === 2 && (
        <div className="space-y-4 animate-fade-rise">
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg border border-border bg-card">
            <div className="flex items-center gap-2 text-xs font-medium text-foreground">
              <Sparkles className="h-4 w-4 text-muted-foreground" />
              <span>Deliverables Templates</span>
            </div>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setDeliverablesText(TEMPLATES.se)}
                className="h-8 text-xs cursor-pointer"
              >
                Software Engineering
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setDeliverablesText(TEMPLATES.thesis)}
                className="h-8 text-xs cursor-pointer"
              >
                Research Thesis
              </Button>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setDeliverablesText('')}
                className="h-8 text-xs text-muted-foreground hover:text-destructive cursor-pointer"
              >
                Clear
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-semibold text-foreground">
              Submission Guidelines & Weightage Breakdown (Markdown supported)
            </label>
            <Textarea
              value={deliverablesText}
              onChange={(e) => setDeliverablesText(e.target.value)}
              placeholder="Detail expected submissions, formatting guidelines, and grading weight..."
              className="font-mono text-xs min-h-[360px] p-4 leading-relaxed bg-background"
            />
            <p className="text-[11px] text-muted-foreground">
              Formatted markdown will be rendered directly on student assignment briefs.
            </p>
          </div>
        </div>
      )}

      {/* ======================================================================= */}
      {/* STEP 3: SPRINT MILESTONES                                               */}
      {/* ======================================================================= */}
      {currentStep === 3 && (
        <div className="space-y-5 animate-fade-rise">
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              Configure sprint checkpoints and target quality gate thresholds for teams.
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleAddMilestone}
              className="h-8 text-xs gap-1.5 cursor-pointer"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Add Checkpoint</span>
            </Button>
          </div>

          <div className="space-y-3">
            {milestones.map((m, index) => (
              <div
                key={m.id}
                className="p-4 rounded-lg border border-border bg-card shadow-2xs space-y-3"
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="flex h-5 w-5 items-center justify-center rounded bg-muted text-[10px] font-mono font-bold text-foreground">
                      {index + 1}
                    </span>
                    <Input
                      value={m.title}
                      onChange={(e) => handleUpdateMilestone(m.id, 'title', e.target.value)}
                      className="h-8 font-semibold text-xs border-transparent hover:border-border focus:border-border px-2 w-72"
                    />
                  </div>

                  <div className="flex items-center gap-2">
                    <Input
                      value={m.sprint}
                      onChange={(e) => handleUpdateMilestone(m.id, 'sprint', e.target.value)}
                      className="h-8 text-xs w-24 text-center font-mono"
                    />
                    <Input
                      value={m.due_week}
                      onChange={(e) => handleUpdateMilestone(m.id, 'due_week', e.target.value)}
                      className="h-8 text-xs w-24 text-center font-mono"
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemoveMilestone(m.id)}
                      className="h-8 w-8 text-muted-foreground hover:text-destructive cursor-pointer"
                      title="Remove milestone"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                  <div>
                    <label className="text-[11px] font-mono text-muted-foreground block mb-1">
                      Quality Gate Target
                    </label>
                    <Input
                      value={m.target_gate}
                      onChange={(e) => handleUpdateMilestone(m.id, 'target_gate', e.target.value)}
                      className="h-8 text-xs font-mono"
                      placeholder="e.g. Code Review ≥ 80%"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] font-mono text-muted-foreground block mb-1">
                      Description / Checkpoint Objective
                    </label>
                    <Input
                      value={m.description}
                      onChange={(e) => handleUpdateMilestone(m.id, 'description', e.target.value)}
                      className="h-8 text-xs"
                      placeholder="Objectives and evaluation criteria"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="space-y-2 pt-2">
            <label className="text-xs font-semibold text-foreground">
              Supervision & Defense Notes (Optional)
            </label>
            <Input
              value={milestoneNotes}
              onChange={(e) => setMilestoneNotes(e.target.value)}
              placeholder="e.g. Panel evaluations conducted on-campus in Lab 402."
              className="h-9 text-xs"
            />
          </div>
        </div>
      )}

      {/* ======================================================================= */}
      {/* STEP 4: TEAM ROSTER                                                     */}
      {/* ======================================================================= */}
      {currentStep === 4 && (
        <div className="space-y-4 animate-fade-rise">
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 rounded-lg border border-border bg-card">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-foreground">Roster Format: JSON Array</span>
              <span className="text-xs text-muted-foreground font-mono">
                ({parsedTeamsData?.length || 0} teams detected)
              </span>
            </div>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => setRosterRaw(JSON.stringify(SAMPLE_ROSTER, null, 2))}
              className="h-8 text-xs cursor-pointer"
            >
              Load Demo Roster
            </Button>
          </div>

          {rosterParseError && (
            <div className="p-3 rounded-md bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{rosterParseError}</span>
            </div>
          )}

          {rosterConflictAnalysis.duplicates.length > 0 && (
            <div className="p-3.5 rounded-lg bg-muted/40 border border-border space-y-2">
              <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                <ShieldAlert className="h-4 w-4 text-amber-500 shrink-0" />
                <span>Academic Single-Team Constraint Notice</span>
              </div>
              <p className="text-[11px] text-muted-foreground">
                SLIIT academic guidelines mandate that a student can only belong to one team within the same cohort batch.
                The following students appear across multiple teams and will trigger backend conflict resolution:
              </p>
              <div className="space-y-1">
                {rosterConflictAnalysis.duplicates.map((dup) => (
                  <div key={dup.email} className="text-xs font-mono text-foreground flex items-center gap-2">
                    <span className="font-semibold">{dup.email}</span>
                    <span className="text-muted-foreground text-[11px]">in teams: {dup.teams.join(', ')}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="space-y-2">
            <label className="text-xs font-semibold text-foreground">
              Team & Student Allocations (JSON)
            </label>
            <Textarea
              value={rosterRaw}
              onChange={(e) => setRosterRaw(e.target.value)}
              className="font-mono text-xs min-h-[300px] p-4 bg-background"
            />
          </div>
        </div>
      )}

      {/* ======================================================================= */}
      {/* STEP 5: REVIEW & LAUNCH                                                 */}
      {/* ======================================================================= */}
      {currentStep === 5 && (
        <div className="space-y-6 animate-fade-rise">
          {setupResult ? (
            <div className="p-8 rounded-xl border border-border bg-card text-center space-y-4 shadow-sm">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-foreground text-background mx-auto">
                <Check className="h-6 w-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-bold text-foreground">Course Setup Completed</h3>
                <p className="text-xs text-muted-foreground">
                  The project has been established and team rosters provisioned successfully.
                </p>
              </div>

              <div className="max-w-md mx-auto p-4 rounded-lg bg-muted/30 border border-border text-left font-mono text-xs space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Project ID:</span>
                  <span className="font-semibold">{setupResult.project?.id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Teams Created:</span>
                  <span className="font-semibold">{setupResult.bulk?.created_count ?? parsedTeamsData?.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Batch Scope:</span>
                  <span className="font-semibold">{activeBatchId}</span>
                </div>
              </div>

              <Button
                asChild
                className="mt-4 gap-2 cursor-pointer"
              >
                <Link
                  to={dashboardPath}
                  onClick={() => wizard?.goToStep && wizard.goToStep(1)}
                >
                  <span>Return to Dashboard</span>
                  <ChevronRight className="h-4 w-4" />
                </Link>
              </Button>
            </div>
          ) : (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="p-4 rounded-lg border border-border bg-card space-y-2">
                  <span className="text-[11px] font-mono uppercase text-muted-foreground">1. Course Project</span>
                  <p className="text-sm font-semibold text-foreground">{projectName || moduleName}</p>
                  <p className="text-xs text-muted-foreground font-mono">{moduleName}</p>
                  <p className="text-xs text-muted-foreground font-mono">Cohort Batch: {activeBatchId}</p>
                </div>

                <div className="p-4 rounded-lg border border-border bg-card space-y-2">
                  <span className="text-[11px] font-mono uppercase text-muted-foreground">2. Roster Statistics</span>
                  <p className="text-sm font-semibold text-foreground">
                    {parsedTeamsData?.length || 0} Teams Configured
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {rosterConflictAnalysis.totalStudents} total student allocations
                  </p>
                  <p className="text-xs text-muted-foreground font-mono">
                    {milestones.length} Sprint milestones defined
                  </p>
                </div>
              </div>

              <div className="p-4 rounded-lg border border-border bg-card space-y-3">
                <span className="text-[11px] font-mono uppercase text-muted-foreground">Pre-Flight Checklist</span>
                <div className="space-y-2 text-xs">
                  <div className="flex items-center gap-2 text-foreground">
                    <CheckCircle2 className="h-4 w-4 text-foreground" />
                    <span>Cohort batch isolation confirmed for <strong className="font-mono">{activeBatchId}</strong></span>
                  </div>
                  <div className="flex items-center gap-2 text-foreground">
                    <CheckCircle2 className="h-4 w-4 text-foreground" />
                    <span>Evaluation deliverables and grading weightages registered</span>
                  </div>
                  <div className="flex items-center gap-2 text-foreground">
                    <CheckCircle2 className="h-4 w-4 text-foreground" />
                    <span>Milestone quality gates and review checkpoints ready</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ======================================================================= */}
      {/* PERSISTENT BOTTOM DOCK CONTROLS                                         */}
      {/* ======================================================================= */}
      {!setupResult && (
        <div className="fixed bottom-0 right-0 left-0 lg:left-64 border-t border-border bg-background/95 backdrop-blur-xs p-4 z-20 flex items-center justify-between">
          <Button
            asChild
            variant="ghost"
            size="sm"
            className="text-xs text-muted-foreground hover:text-foreground cursor-pointer"
          >
            <Link
              to={dashboardPath}
              onClick={() => wizard?.goToStep && wizard.goToStep(1)}
            >
              Cancel & Exit
            </Link>
          </Button>

          <div className="flex items-center gap-3">
            {currentStep > 1 && (
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setCurrentStep(currentStep - 1)}
                className="gap-1.5 text-xs cursor-pointer"
              >
                <ChevronLeft className="h-3.5 w-3.5" />
                <span>Back</span>
              </Button>
            )}

            {currentStep === 1 && (
              <Button
                type="button"
                size="sm"
                onClick={handleNextFromStep1}
                className="gap-1.5 text-xs cursor-pointer"
              >
                <span>Continue to Deliverables</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            )}

            {currentStep === 2 && (
              <Button
                type="button"
                size="sm"
                onClick={handleNextFromStep2}
                className="gap-1.5 text-xs cursor-pointer"
              >
                <span>Continue to Milestones</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            )}

            {currentStep === 3 && (
              <Button
                type="button"
                size="sm"
                onClick={() => setCurrentStep(4)}
                className="gap-1.5 text-xs cursor-pointer"
              >
                <span>Continue to Team Roster</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            )}

            {currentStep === 4 && (
              <Button
                type="button"
                size="sm"
                onClick={handleNextFromStep4}
                className="gap-1.5 text-xs cursor-pointer"
              >
                <span>Review & Finalize</span>
                <ChevronRight className="h-3.5 w-3.5" />
              </Button>
            )}

            {currentStep === 5 && (
              <Button
                type="button"
                size="sm"
                disabled={isSubmitting}
                onClick={handleCompleteSetup}
                className="gap-1.5 text-xs cursor-pointer"
              >
                <Rocket className="h-3.5 w-3.5" />
                <span>{isSubmitting ? 'Provisioning Course...' : 'Launch Project & Roster'}</span>
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
