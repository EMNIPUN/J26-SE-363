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

export default function Assessments() {
  const { assessmentId } = useParams()
  const [searchParams] = useSearchParams()
  const conceptFilter = searchParams.get('concept')
  const team = useTeamPath()
  const navigate = useNavigate()
  const [workspace, setWorkspace] = useState(null)
  const [assessment, setAssessment] = useState(null)
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState({})
  const [result, setResult] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [loadedKey, setLoadedKey] = useState(null)
  const requestKey = `${assessmentId || 'list'}:${reloadKey}`
  const ready = loadedKey === requestKey

  useEffect(() => {
    let live = true
    const request = assessmentId
      ? tutorWorkspaceService.getAssessment(assessmentId)
      : tutorWorkspaceService.getProjectContext()
    request
      .then((data) => {
        if (!live) return
        if (assessmentId) {
          setAssessment(data)
          setResult(data.lastResult)
          setIndex(0)
          setAnswers({})
        } else {
          setWorkspace(data)
        }
        setError(null)
        setLoadedKey(requestKey)
      })
      .catch((err) => {
        if (!live) return
        setError(err.message || 'The sample assessments could not be loaded.')
        setLoadedKey(requestKey)
      })
    return () => {
      live = false
    }
  }, [assessmentId, reloadKey, requestKey])

  const submit = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const response = await tutorWorkspaceService.submitAssessment(assessmentId, answers)
      setResult(response.result)
    } catch (err) {
      setError(err.message || 'The attempt could not be stored.')
    } finally {
      setSubmitting(false)
    }
  }

  if (assessmentId) {
    const questions = assessment?.questions || []
    const question = questions[index]
    const unanswered = questions.filter((item) => answers[item.id] == null)
    return (
      <div className="space-y-6">
        <PageHeader
          breadcrumb={['AI Tutor', 'Assessments']}
          title={assessment?.title || 'Assessment'}
          description="The score is a quiz result. It does not change the competency estimate."
          actions={
            <Button asChild variant="outline" size="sm">
              <Link to={team('/tutor/assessments')}>All assessments</Link>
            </Button>
          }
        />
        <SampleBanner />
        {!ready && !error && <p className="text-sm text-muted-foreground">Loading the assessment…</p>}
        {error && (
          <EmptyState title="Assessment unavailable" description={error} actionLabel="Back" onAction={() => navigate(team('/tutor/assessments'))} />
        )}
        {ready && assessment && !result && question && (
          <Card className="space-y-4 p-5">
            <p className="text-xs text-muted-foreground">
              {assessment.kind} · {assessment.minutes} min suggested · Question {index + 1} of {questions.length}
              {' · '}
              {CONCEPTS[question.conceptId]?.label}
            </p>
            <h2 className="text-base font-semibold">{question.prompt}</h2>
            <fieldset className="space-y-2">
              <legend className="sr-only">Answer</legend>
              {question.choices.map((choice, choiceIndex) => (
                <label key={choice} className="flex cursor-pointer items-start gap-2 rounded-lg border border-border px-3 py-2 text-sm">
                  <input
                    type="radio"
                    name={question.id}
                    checked={answers[question.id] === choiceIndex}
                    onChange={() => setAnswers((prev) => ({ ...prev, [question.id]: choiceIndex }))}
                    className="mt-1"
                  />
                  <span>{choice}</span>
                </label>
              ))}
            </fieldset>
            <div className="flex flex-wrap gap-2">
              <Button type="button" variant="outline" disabled={index === 0} onClick={() => setIndex((value) => value - 1)}>
                Previous
              </Button>
              {index < questions.length - 1 ? (
                <Button type="button" onClick={() => setIndex((value) => value + 1)}>
                  Next
                </Button>
              ) : (
                <Button type="button" onClick={submit} disabled={submitting || unanswered.length > 0}>
                  {submitting ? 'Submitting…' : 'Submit attempt'}
                </Button>
              )}
            </div>
            {unanswered.length > 0 && index === questions.length - 1 && (
              <p className="text-xs text-muted-foreground">Answer every question before submitting.</p>
            )}
            {error && <p className="text-sm text-destructive">{error}</p>}
          </Card>
        )}
        {ready && result && (
          <Card className="space-y-4 p-5">
            <h2 className="text-base font-semibold">Result recorded</h2>
            <dl className="grid gap-3 sm:grid-cols-3">
              <div>
                <dt className="text-xs text-muted-foreground">Quiz score</dt>
                <dd className="font-mono text-sm font-semibold">{result.scoreText}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Competency estimate</dt>
                <dd className="text-sm font-medium">{result.competencyEstimate}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Confidence</dt>
                <dd className="text-sm font-medium">{result.confidence}</dd>
              </div>
            </dl>
            <ul className="space-y-3">
              {result.reviews.map((review) => (
                <li key={review.questionId} className="rounded-lg border border-border px-3 py-2 text-sm">
                  <p className="font-medium">
                    {CONCEPTS[review.conceptId]?.label}: {review.correct ? 'Matched the keyed answer' : 'Did not match the keyed answer'}
                  </p>
                  <p className="mt-1 text-muted-foreground">{review.explanation}</p>
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap gap-2">
              <Button asChild size="sm">
                <Link to={team('/tutor/guidance')}>View recommendation</Link>
              </Button>
              <Button asChild variant="outline" size="sm">
                <Link to={team('/tutor/progress')}>View progress</Link>
              </Button>
            </div>
          </Card>
        )}
      </div>
    )
  }

  const assessments = (workspace?.assessments || []).filter(
    (item) => !conceptFilter || item.conceptIds.includes(conceptFilter),
  )

  return (
    <div className="space-y-6">
      <PageHeader
        breadcrumb={['AI Tutor', 'Assessments']}
        title="Assessments"
        description="Diagnostics, concept quizzes, and reassessments. A score stays a score until the tutor service returns a new estimate."
      />
      <SampleBanner />
      {!ready && !error && <p className="text-sm text-muted-foreground">Loading assessments…</p>}
      {error && (
        <EmptyState title="Assessments unavailable" description={error} actionLabel="Try again" onAction={() => setReloadKey((value) => value + 1)} />
      )}
      {ready && workspace && assessments.length === 0 && (
        <EmptyState title="No assessment for this concept" description="The sample set has no quiz linked to the selected concept." />
      )}
      {ready && workspace && (
        <div className="grid gap-3 lg:grid-cols-2">
          {assessments.map((item) => {
            const task = TASKS.find((taskItem) => taskItem.id === item.taskId)
            const attempts = workspace.attempts.filter((attempt) => attempt.assessmentId === item.id)
            return (
              <Card key={item.id} className="space-y-3 p-4">
                <div className="flex items-start justify-between gap-2">
                  <h2 className="text-sm font-semibold">{item.title}</h2>
                  <span className="text-xs text-muted-foreground">{item.status}</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {item.kind} · {item.questions.length} questions · {item.minutes} min
                </p>
                <p className="text-sm text-muted-foreground">{item.objectives[0]}</p>
                <p className="text-xs text-muted-foreground">
                  Concepts: {item.conceptIds.map((id) => CONCEPTS[id]?.label).join(', ')}
                </p>
                <p className="text-xs text-muted-foreground">Task: {task?.title}</p>
                {attempts.length > 0 && (
                  <ul className="text-xs text-muted-foreground">
                    {attempts.map((attempt) => (
                      <li key={attempt.id}>
                        {attempt.when}: {attempt.scoreText}. {attempt.note}
                      </li>
                    ))}
                  </ul>
                )}
                <Button asChild size="sm">
                  <Link to={team(`/tutor/assessments/${item.id}`)}>
                    {item.status === 'Available' ? 'Start assessment' : 'Review or retake'}
                  </Link>
                </Button>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
