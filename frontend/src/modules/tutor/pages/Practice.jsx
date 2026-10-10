import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import EmptyState from '../../../shared/components/EmptyState.jsx'
import PageHeader from '../../../shared/components/PageHeader.jsx'
import { useTeamPath } from '../../../shared/hooks/useTeamPath.js'
import { CONCEPTS, TASKS } from '../data/tutorWorkspace.js'
import SampleBanner from '../components/SampleBanner.jsx'
import { tutorWorkspaceService } from '../services/tutorWorkspaceService.js'

export default function Practice() {
  const { exerciseId } = useParams()
  const [searchParams] = useSearchParams()
  const conceptFilter = searchParams.get('concept')
  const team = useTeamPath()
  const navigate = useNavigate()
  const [workspace, setWorkspace] = useState(null)
  const [exercise, setExercise] = useState(null)
  const [answer, setAnswer] = useState('')
  const [result, setResult] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [loadedKey, setLoadedKey] = useState(null)
  const requestKey = `${exerciseId || 'list'}:${reloadKey}`
  const ready = loadedKey === requestKey

  useEffect(() => {
    let live = true
    const request = exerciseId
      ? tutorWorkspaceService.getExercise(exerciseId)
      : tutorWorkspaceService.getProjectContext()
    request
      .then((data) => {
        if (!live) return
        if (exerciseId) {
          setExercise(data)
          setResult(data.lastResult)
          setAnswer('')
        } else {
          setWorkspace(data)
        }
        setError(null)
        setLoadedKey(requestKey)
      })
      .catch((err) => {
        if (!live) return
        setError(err.message || 'The sample exercises could not be loaded.')
        setLoadedKey(requestKey)
      })
    return () => {
      live = false
    }
  }, [exerciseId, reloadKey, requestKey])

  const submit = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const response = await tutorWorkspaceService.submitExercise(exerciseId, answer)
      setResult(response.result)
      setExercise((prev) => ({ ...prev, status: response.result.status, lastResult: response.result }))
    } catch (err) {
      setError(err.message || 'The sample check could not be saved.')
    } finally {
      setSubmitting(false)
    }
  }

  if (exerciseId) {
    const concept = exercise ? CONCEPTS[exercise.conceptId] : null
    const task = exercise ? TASKS.find((item) => item.id === exercise.taskId) : null
    return (
      <div className="space-y-6">
        <PageHeader
          breadcrumb={['AI Tutor', 'Practice Exercises']}
          title={exercise?.title || 'Exercise'}
          description="Submit an answer for a sample check. Code is not executed."
          actions={
            <Button asChild variant="outline" size="sm">
              <Link to={team('/tutor/practice')}>All exercises</Link>
            </Button>
          }
        />
        <SampleBanner />
        {!ready && !error && <p className="text-sm text-muted-foreground">Loading the exercise…</p>}
        {error && !exercise && (
          <EmptyState title="Exercise unavailable" description={error} actionLabel="Back" onAction={() => navigate(team('/tutor/practice'))} />
        )}
        {ready && exercise && (
          <Card className="space-y-4 p-5">
            <div className="flex flex-wrap gap-2 text-xs text-muted-foreground">
              <span>{exercise.type}</span>
              <span>· {concept?.label}</span>
              <span>· {task?.title}</span>
              <span>· {exercise.difficulty}</span>
              <span>· {exercise.minutes} min</span>
            </div>
            <p className="text-sm font-medium">Objective</p>
            <ul className="list-disc pl-5 text-sm text-muted-foreground">
              {exercise.objectives.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <p className="text-sm leading-relaxed">{exercise.prompt}</p>
            {exercise.starter && (
              <pre className="overflow-x-auto rounded-lg border border-border bg-muted/40 p-3 font-mono text-xs">
                <code>{exercise.starter}</code>
              </pre>
            )}
            {exercise.promptNote && <p className="text-xs text-muted-foreground">{exercise.promptNote}</p>}
            {exercise.type === 'multiple-choice' ? (
              <fieldset className="space-y-2">
                <legend className="sr-only">Answer</legend>
                {exercise.choices.map((choice) => (
                  <label key={choice.id} className="flex cursor-pointer items-start gap-2 rounded-lg border border-border px-3 py-2 text-sm">
                    <input
                      type="radio"
                      name="exercise-choice"
                      value={choice.id}
                      checked={answer === choice.id}
                      onChange={() => setAnswer(choice.id)}
                      className="mt-1"
                    />
                    <span>{choice.label}</span>
                  </label>
                ))}
              </fieldset>
            ) : (
              <textarea
                value={answer}
                onChange={(event) => setAnswer(event.target.value)}
                rows={6}
                aria-label="Your answer"
                className="w-full rounded-lg border border-input bg-background px-3 py-2 font-mono text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder="Write your answer. It stays in this browser session."
              />
            )}
            <div className="flex flex-wrap gap-2">
              <Button type="button" onClick={submit} disabled={submitting || !String(answer).trim()}>
                {submitting ? 'Checking…' : 'Submit answer'}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setAnswer('')
                  setResult(null)
                }}
              >
                Clear and retry
              </Button>
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            {result && (
              <div className="rounded-lg border border-border bg-muted/30 p-4 text-sm">
                <p className="font-medium">{result.matched ? 'Sample check matched' : 'Sample check did not match'}</p>
                <p className="mt-1 text-muted-foreground">{result.feedback}</p>
                <p className="mt-2 text-xs text-muted-foreground">Status: {result.status}. Evaluated by the sample check.</p>
                {result.matched && (
                  <Button asChild className="mt-3" size="sm">
                    <Link to={team('/tutor/guidance')}>See the updated recommendation</Link>
                  </Button>
                )}
              </div>
            )}
          </Card>
        )}
      </div>
    )
  }

  const exercises = (workspace?.exercises || []).filter((item) => !conceptFilter || item.conceptId === conceptFilter)
  const recommended = exercises.filter((item) => item.recommended)
  const others = exercises.filter((item) => !item.recommended)

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={['AI Tutor', 'Practice Exercises']}
        title="Practice exercises"
        description="Targeted practice from the sample learning set. A submission is evidence of an attempt, not a new competency percentage."
      />
      <SampleBanner />
      {!ready && !error && <p className="text-sm text-muted-foreground">Loading exercises…</p>}
      {error && <EmptyState title="Exercises unavailable" description={error} actionLabel="Try again" onAction={() => setReloadKey((value) => value + 1)} />}
      {ready && workspace && exercises.length === 0 && (
        <EmptyState title="No exercises for this concept" description="The sample set has no exercise linked to the selected concept." />
      )}
      {ready && workspace && exercises.length > 0 && (
        <div className="space-y-6">
          <ExerciseGroup title="Recommended" items={recommended} team={team} />
          <ExerciseGroup title="Also available" items={others} team={team} />
        </div>
      )}
    </div>
  )
}

function ExerciseGroup({ title, items, team }) {
  if (!items.length) return null
  return (
    <section className="space-y-3">
      <h2 className="text-sm font-semibold">{title}</h2>
      <div className="grid gap-3 md:grid-cols-2">
        {items.map((exercise) => {
          const concept = CONCEPTS[exercise.conceptId]
          const task = TASKS.find((item) => item.id === exercise.taskId)
          return (
            <Card key={exercise.id} className="flex flex-col justify-between gap-3 p-4">
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold">{exercise.title}</h3>
                  <span className="shrink-0 rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground">
                    {exercise.status}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {concept?.label} · {task?.title}
                </p>
                <p className="text-xs text-muted-foreground">
                  {exercise.difficulty} · {exercise.minutes} min · {exercise.type}
                </p>
                <p className="text-sm text-muted-foreground">{exercise.objectives[0]}</p>
              </div>
              <Button asChild size="sm" className="self-start">
                <Link to={team(`/tutor/practice/${exercise.id}`)}>Open exercise</Link>
              </Button>
            </Card>
          )
        })}
      </div>
    </section>
  )
}
