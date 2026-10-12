import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ClipboardCheck, MessageCircle, Route } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import EmptyState from '../../../shared/components/EmptyState.jsx'
import PageHeader from '../../../shared/components/PageHeader.jsx'
import { useTeamPath } from '../../../shared/hooks/useTeamPath.js'
import { CONCEPTS, MATERIALS } from '../data/tutorWorkspace.js'
import CompetencyIndicator, { StatusBadge } from '../components/CompetencyIndicator.jsx'
import RecommendedNextActionCard from '../components/RecommendedNextActionCard.jsx'
import SampleBanner from '../components/SampleBanner.jsx'
import { tutorWorkspaceService } from '../services/tutorWorkspaceService.js'

const STEP_CLASS = {
  done: 'border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200',
  current: 'border-primary/40 bg-primary/5 text-foreground',
  ready: 'border-border bg-card text-foreground',
  upcoming: 'border-border bg-muted/30 text-muted-foreground',
}

export default function SprintGuidance() {
  const team = useTeamPath()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [workspace, setWorkspace] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [taskId, setTaskId] = useState('task-jwt')
  const [conceptId, setConceptId] = useState('concept-token')
  const [materialId, setMaterialId] = useState(null)

  const load = () => {
    setLoading(true)
    setError(null)
    setReloadKey((value) => value + 1)
  }

  useEffect(() => {
    let live = true
    tutorWorkspaceService
      .getRecommendation()
      .then((data) => {
        if (!live) return
        setWorkspace(data)
        setError(null)
        setLoading(false)
      })
      .catch((err) => {
        if (!live) return
        setError(err.message || 'The sample tutor workspace could not be loaded.')
        setLoading(false)
      })
    return () => {
      live = false
    }
  }, [reloadKey])

  const task = workspace?.tasks.find((item) => item.id === taskId)
  const conceptIds = task?.conceptIds || []
  const concept = CONCEPTS[conceptId]
  const estimate = workspace?.estimates.find((item) => item.conceptId === conceptId)
  const material = MATERIALS[materialId]

  const selectTask = (nextId) => {
    const next = workspace.tasks.find((item) => item.id === nextId)
    setTaskId(nextId)
    setMaterialId(null)
    if (next && !next.conceptIds.includes(conceptId)) setConceptId(next.conceptIds[0])
  }

  const ask = (prompt) => {
    navigate(team(`/tutor/chat?prompt=${encodeURIComponent(prompt)}`))
  }

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={['AI Tutor', 'Sprint Guidance']}
        title="Sprint guidance"
        description="The sample project task, the knowledge it asks for, and the next action returned by the sample decision table."
      />
      <SampleBanner />

      {loading && <p className="text-sm text-muted-foreground">Loading the sample workspace…</p>}
      {error && (
        <EmptyState
          title="Workspace unavailable"
          description={error}
          actionLabel="Try again"
          onAction={load}
        />
      )}

      {workspace && task && (
        <>
          <RecommendedNextActionCard
            recommendation={workspace.recommendation}
            onStartPractice={() => navigate(team(`/tutor/practice/${workspace.recommendation.practiceId}`))}
            onViewMaterial={() => setMaterialId(workspace.recommendation.materialId)}
          />

          <div className="grid gap-4 lg:grid-cols-5">
            <Card className="space-y-4 p-5 lg:col-span-2">
              <div>
                <p className="text-xs font-medium text-muted-foreground">Project</p>
                <h2 className="text-base font-semibold">{workspace.project.name}</h2>
                <p className="text-sm text-muted-foreground">{workspace.project.sprintName}</p>
              </div>
              <div className="space-y-2">
                <p className="text-xs font-medium text-foreground">Sprint tasks</p>
                {workspace.tasks.map((item) => (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => selectTask(item.id)}
                    aria-pressed={item.id === taskId}
                    className={`w-full rounded-lg border px-3 py-2 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                      item.id === taskId ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted'
                    }`}
                  >
                    <span className="block text-sm font-medium">{item.title}</span>
                    <span className="text-xs text-muted-foreground">{item.status}</span>
                  </button>
                ))}
              </div>
            </Card>

            <Card className="space-y-3 p-5 lg:col-span-3">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <h2 className="text-base font-semibold">{task.title}</h2>
                <span className="text-xs text-muted-foreground">{task.status}</span>
              </div>
              <p className="text-sm leading-relaxed text-muted-foreground">{task.description}</p>
              {typeof task.progress === 'number' && (
                <p className="text-xs text-muted-foreground">Sample task progress on file: {task.progress}%</p>
              )}
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <p className="text-xs font-medium">Requirements</p>
                  <ul className="mt-1 list-disc space-y-1 pl-4 text-sm text-muted-foreground">
                    {task.requirements.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <p className="text-xs font-medium">Acceptance criteria</p>
                  <ul className="mt-1 list-disc space-y-1 pl-4 text-sm text-muted-foreground">
                    {task.acceptance.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              </div>
              <Button asChild variant="outline" size="sm">
                <Link to={team('/planning/sprint-management')}>View sprint board</Link>
              </Button>
            </Card>
          </div>

          <div className="grid gap-4 lg:grid-cols-5">
            <Card className="p-5 lg:col-span-2">
              <h2 className="text-sm font-semibold">Required knowledge</h2>
              <ul className="mt-3 space-y-2">
                {conceptIds.map((id) => {
                  const item = CONCEPTS[id]
                  const itemEstimate = workspace.estimates.find((entry) => entry.conceptId === id)
                  return (
                    <li key={id}>
                      <button
                        type="button"
                        onClick={() => {
                          setConceptId(id)
                          setMaterialId(null)
                        }}
                        aria-pressed={id === conceptId}
                        className={`flex w-full items-center justify-between gap-2 rounded-lg border px-3 py-2 text-left outline-none focus-visible:ring-2 focus-visible:ring-ring ${
                          id === conceptId ? 'border-primary bg-primary/5' : 'border-border hover:bg-muted'
                        }`}
                      >
                        <span className="text-sm font-medium">{item.label}</span>
                        <StatusBadge status={itemEstimate?.status || item.status} />
                      </button>
                    </li>
                  )
                })}
              </ul>
            </Card>

            {concept && (
              <Card className="space-y-4 p-5 lg:col-span-3">
                <div>
                  <h2 className="text-base font-semibold">{concept.label}</h2>
                  <p className="mt-1 text-sm text-muted-foreground">{concept.description}</p>
                  <p className="mt-2 text-xs text-muted-foreground">
                    Prerequisites: {concept.prerequisites.length ? concept.prerequisites.join(', ') : 'None listed'}
                  </p>
                </div>
                <CompetencyIndicator estimate={estimate} />
                <div className="flex flex-wrap gap-2">
                  <Button type="button" size="sm" variant="outline" onClick={() => setMaterialId(concept.resourceIds[0])}>
                    Open learning material
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => navigate(team(`/tutor/practice?concept=${concept.id}`))}
                  >
                    Start practice
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => navigate(team(`/tutor/assessments?concept=${concept.id}`))}
                  >
                    <ClipboardCheck className="h-4 w-4" />
                    Take assessment
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="outline"
                    onClick={() => ask(`Explain ${concept.label} simply, in the context of ${task.title}.`)}
                  >
                    <MessageCircle className="h-4 w-4" />
                    Ask the tutor
                  </Button>
                </div>
                {material && (
                  <div className="rounded-lg border border-border bg-muted/30 p-4">
                    <p className="text-sm font-medium">{material.title}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      About {material.minutes} minutes. The sample set names this reading. The full text is not stored here.
                    </p>
                    <Button type="button" size="sm" variant="ghost" className="mt-2 px-0" onClick={() => setMaterialId(null)}>
                      Close material
                    </Button>
                  </div>
                )}
              </Card>
            )}
          </div>

          <Card className="p-5">
            <div className="flex items-center gap-2">
              <Route className="h-4 w-4 text-primary" aria-hidden="true" />
              <h2 className="text-sm font-semibold">Learning steps for this recommendation</h2>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              This sequence comes from the sample decision table for phase “{workspace.recommendation.phase}”. It is not an adaptive algorithm running in the browser.
            </p>
            <ol className="mt-4 space-y-2">
              {workspace.roadmap.map((step, index) => (
                <li
                  key={step.id}
                  className={`flex items-center justify-between gap-3 rounded-lg border px-3 py-2 text-sm ${STEP_CLASS[step.state]}`}
                >
                  <span>
                    {index + 1}. {step.label}
                  </span>
                  <span className="text-xs capitalize">{step.state}</span>
                </li>
              ))}
            </ol>
          </Card>
        </>
      )}
    </div>
  )
}
