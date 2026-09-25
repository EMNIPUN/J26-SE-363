import PropTypes from 'prop-types'
import { CheckCircle2, MessageSquare, Award, Bot, UserCheck } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

/**
 * CodeComprehensionLog: GenAI Automated Oral Viva & Comprehension Evaluation
 *
 * Displays transcript of AI-generated technical questions based on student's actual commits/PRs,
 * the student's explanations, and the evaluated author authenticity score.
 */
export default function CodeComprehensionLog({
  comprehension = {
    status: 'Verified',
    score: 94,
    verdict: 'High Confidence: Genuine Author',
    transcript: [],
  },
}) {
  const { score = 94, verdict = 'Verified', transcript = [] } = comprehension

  return (
    <div className="rounded-xl border border-border bg-card p-4 sm:p-5 shadow-xs space-y-4">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-500/10 text-violet-500">
            <Award className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground">
              GenAI Code Comprehension & Viva Evaluation
            </h3>
            <p className="text-[11px] text-muted-foreground">
              Automated oral verification preventing AI ghost-writing & plagiarism
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className="bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 text-xs px-2.5 py-1 font-semibold"
          >
            <CheckCircle2 className="h-3 w-3 mr-1" />
            {verdict}
          </Badge>
          <span className="text-xs font-mono font-bold bg-muted px-2.5 py-1 rounded-md text-foreground">
            {score}/100
          </span>
        </div>
      </div>

      {/* Oral Interview Question & Answer Cards */}
      <div className="space-y-3">
        {transcript.length === 0 ? (
          <div className="py-8 text-center text-xs text-muted-foreground">
            No comprehension interview transcripts recorded for this sprint yet.
          </div>
        ) : (
          transcript.map((item, idx) => (
            <div
              key={`transcript-${idx}`}
              className="p-3.5 rounded-lg border border-border/80 bg-background/50 space-y-2.5"
            >
              {/* Question */}
              <div className="flex items-start gap-2.5 text-xs">
                <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary mt-0.5">
                  <Bot className="h-3 w-3" />
                </div>
                <div>
                  <span className="font-semibold text-foreground">
                    Oral Question {idx + 1}:{' '}
                  </span>
                  <span className="text-muted-foreground">{item.question}</span>
                </div>
              </div>

              {/* Student Answer */}
              <div className="flex items-start gap-2.5 text-xs pl-7">
                <div className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground mt-0.5">
                  <UserCheck className="h-3 w-3" />
                </div>
                <div className="p-2.5 rounded-md bg-muted/30 border border-border/50 text-foreground w-full font-sans leading-relaxed">
                  {item.answer}
                </div>
              </div>

              {/* AI Evaluation */}
              <div className="flex items-center justify-between pl-7 text-[11px] pt-1 text-muted-foreground">
                <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
                  <MessageSquare className="h-3 w-3" />
                  <span>{item.evaluation}</span>
                </div>
                <Badge variant="secondary" className="text-[10px] font-mono">
                  Confidence: {item.aiConfidence}%
                </Badge>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

CodeComprehensionLog.propTypes = {
  comprehension: PropTypes.shape({
    status: PropTypes.string,
    score: PropTypes.number,
    verdict: PropTypes.string,
    transcript: PropTypes.arrayOf(
      PropTypes.shape({
        question: PropTypes.string,
        answer: PropTypes.string,
        aiConfidence: PropTypes.number,
        evaluation: PropTypes.string,
      }),
    ),
  }),
}
