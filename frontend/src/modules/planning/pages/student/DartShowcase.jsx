import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Search,
  Tag,
  MessageCircleQuestion,
  MessageCircleReply,
  Scale,
  Gavel,
  ArrowRight,
  ArrowDown,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Sparkles,
  Brain,
  Eye,
  Layers,
  Zap,
  ShieldCheck,
  ChevronDown,
  BarChart3,
  GitCompareArrows,
} from 'lucide-react'
import Card from '../../../../shared/components/Card.jsx'
import Badge from '../../../../shared/components/Badge.jsx'
import PageHeader from '../../../../shared/components/PageHeader.jsx'
import { Button } from '@/components/ui/button'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { useTeamPath } from '@/shared/hooks/useTeamPath.js'
import { useDartCases } from '../../hooks/useDart.js'
import { mapDartCases } from '../../adapters/dart.js'
import { ARBITRATION_CATEGORY_TONE } from '../../utils.js'

const PROTOCOL_STEPS = [
  {
    key: 'gather',
    label: 'Gather',
    icon: Search,
    color: 'text-blue-600 dark:text-blue-400',
    bg: 'bg-blue-500/10 border-blue-500/20',
    title: 'Gather Reasoning Traces',
    description:
      'DART collects structured diagnostic reasoning from every agent that evaluated this requirement — not just scores, but the WHY behind each assessment: evidence cited, criteria applied, uncertainty flags, and confidence levels.',
    novelty: 'Unlike voting, DART preserves each agent\'s full reasoning chain.',
  },
  {
    key: 'categorize',
    label: 'Categorize',
    icon: Tag,
    color: 'text-amber-600 dark:text-amber-400',
    bg: 'bg-amber-500/10 border-amber-500/20',
    title: 'Categorize Diagnostic Hypothesis',
    description:
      'The gathered traces are analyzed to classify the ROOT CAUSE of uncertainty into one of four domain-specific categories: Compound Obligation, Ambiguous Requirement, Structural Conflict, or Novel Pattern.',
    novelty: 'Domain-specific categorization enables targeted intervention, not generic retry.',
  },
  {
    key: 'consult',
    label: 'Consult',
    icon: MessageCircleQuestion,
    color: 'text-purple-600 dark:text-purple-400',
    bg: 'bg-purple-500/10 border-purple-500/20',
    title: 'Formulate Targeted Consultation',
    description:
      'Based on the diagnosis, DART formulates a TARGETED question — not the same question again. For COMPOUND issues: "Can these obligations be independently tested?" For AMBIGUOUS: "Which interpretation does the evidence support?"',
    novelty: 'THE KEY NOVELTY — a targeted question, not a re-vote. This is what makes DART publishable.',
  },
  {
    key: 'respond',
    label: 'Respond',
    icon: MessageCircleReply,
    color: 'text-emerald-600 dark:text-emerald-400',
    bg: 'bg-emerald-500/10 border-emerald-500/20',
    title: 'Evidence-Based Response',
    description:
      'The consulted agent responds with evidence retrieved from domain-specific knowledge bases — IEEE 830 standards, requirement exemplars, and decomposition patterns — grounding the response in authoritative sources.',
    novelty: 'RAG-augmented consultation ensures responses are evidence-based, not hallucinated.',
  },
  {
    key: 'resolve',
    label: 'Resolve',
    icon: Scale,
    color: 'text-rose-600 dark:text-rose-400',
    bg: 'bg-rose-500/10 border-rose-500/20',
    title: 'Determine Resolution Action',
    description:
      'DART selects one of four resolution actions: RESOLVE (diagnosis converges), RETRIEVE (expand evidence), REFINE (re-analyze with new aspect), or ESCALATE (unresolvable — route to instructor). Each includes actionable student feedback.',
    novelty: 'Convergence rules prevent infinite loops: max 2 iterations, circuit breaker at 5 activations.',
  },
]

const COMPARISON_ROWS = [
  {
    dimension: 'Operates on',
    voting: 'Final outputs (scores/labels)',
    dart: 'Reasoning traces (evidence + criteria + confidence)',
    advantage: 'Preserves diagnostic context',
  },
  {
    dimension: 'On disagreement',
    voting: 'Re-asks the same question',
    dart: 'Asks a targeted question based on diagnosed category',
    advantage: 'Avoids redundant computation',
  },
  {
    dimension: 'Resolution',
    voting: 'Majority wins',
    dart: 'Evidence-weighted arbitration with domain retrieval',
    advantage: 'Grounded in authoritative sources',
  },
  {
    dimension: 'Feedback to student',
    voting: '"Score: 65%" (opaque)',
    dart: '"Define \'customer request\', replace \'good UX\' with measurable criteria"',
    advantage: 'Actionable, specific guidance',
  },
  {
    dimension: 'Convergence',
    voting: 'No guarantee',
    dart: 'Max 2 iterations, circuit breaker, forced escalation',
    advantage: 'Bounded execution time',
  },
  {
    dimension: 'Instructor role',
    voting: 'None — fully automated',
    dart: 'ESCALATE routes unresolvable cases for human review',
    advantage: 'Human-in-the-loop for edge cases',
  },
]

const CATEGORY_INFO = [
  {
    key: 'compound',
    label: 'COMPOUND',
    tone: 'warning',
    icon: Layers,
    example: '"The system shall handle user registration and send email notifications and log audit events."',
    question: 'Can these obligations be independently implemented and tested?',
    description: 'Multiple independent obligations detected in a single requirement.',
  },
  {
    key: 'ambiguous',
    label: 'AMBIGUOUS',
    tone: 'primary',
    icon: Eye,
    example: '"The system should provide a good user experience when handling customer requests."',
    question: 'Which interpretation does the evidence support? What specific terms need defining?',
    description: 'Vague terms or multiple valid interpretations found.',
  },
  {
    key: 'structural',
    label: 'STRUCTURAL',
    tone: 'danger',
    icon: GitCompareArrows,
    example: '"Response time shall be under 100ms" vs "All requests must be encrypted end-to-end"',
    question: 'Does this conflict with requirement X? Explain the constraint.',
    description: 'Conflicts with other requirements or architectural constraints.',
  },
  {
    key: 'novel',
    label: 'NOVEL',
    tone: 'neutral',
    icon: Sparkles,
    example: '"The system shall use quantum-resistant encryption for all stored biometric data."',
    question: 'What is the closest known pattern and how far does this deviate?',
    description: 'No matching pattern found in the knowledge base.',
  },
]

function AnimatedProtocolFlow() {
  const [activeStep, setActiveStep] = useState(0)
  const [isAutoPlaying, setIsAutoPlaying] = useState(true)

  useEffect(() => {
    if (!isAutoPlaying) return
    const timer = setInterval(() => {
      setActiveStep((prev) => (prev + 1) % PROTOCOL_STEPS.length)
    }, 4000)
    return () => clearInterval(timer)
  }, [isAutoPlaying])

  const step = PROTOCOL_STEPS[activeStep]
  const Icon = step.icon

  return (
    <Card className="p-0 overflow-hidden">
      <div className="p-5 border-b border-border">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-base font-bold text-foreground flex items-center gap-2">
            <Brain className="h-4.5 w-4.5 text-primary" />
            Five-Step DART Protocol
          </h3>
          <Button
            size="sm"
            variant="outline"
            className="text-xs"
            onClick={() => setIsAutoPlaying((v) => !v)}
          >
            {isAutoPlaying ? 'Pause' : 'Auto-play'}
          </Button>
        </div>

        <div className="flex items-center gap-1 sm:gap-2">
          {PROTOCOL_STEPS.map((s, i) => {
            const StepIcon = s.icon
            const isActive = i === activeStep
            const isPast = i < activeStep

            return (
              <div key={s.key} className="flex items-center gap-1 sm:gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setActiveStep(i)
                    setIsAutoPlaying(false)
                  }}
                  className={`flex items-center gap-1.5 px-2.5 py-2 rounded-lg border transition-all duration-300 cursor-pointer ${
                    isActive
                      ? `${s.bg} border-current ${s.color} shadow-sm scale-105`
                      : isPast
                        ? 'bg-muted/40 border-border text-muted-foreground'
                        : 'bg-card border-border/50 text-muted-foreground/60'
                  }`}
                >
                  <StepIcon className={`h-4 w-4 ${isActive ? '' : ''}`} />
                  <span className="text-xs font-semibold hidden sm:inline">{s.label}</span>
                </button>
                {i < PROTOCOL_STEPS.length - 1 && (
                  <ArrowRight
                    className={`h-3.5 w-3.5 shrink-0 transition-colors ${
                      isPast ? 'text-primary' : 'text-muted-foreground/30'
                    }`}
                  />
                )}
              </div>
            )
          })}
        </div>
      </div>

      <div className="p-5 min-h-[200px] transition-all duration-500">
        <div className="flex items-start gap-4">
          <div className={`p-3 rounded-xl ${step.bg} border shrink-0`}>
            <Icon className={`h-6 w-6 ${step.color}`} />
          </div>
          <div className="space-y-2 min-w-0">
            <div className="flex items-center gap-2">
              <h4 className="text-lg font-bold text-foreground">
                Step {activeStep + 1}: {step.title}
              </h4>
              <Badge tone="primary" className="text-[10px]">
                {step.key.toUpperCase()}
              </Badge>
            </div>
            <p className="text-sm text-foreground/80 leading-relaxed">{step.description}</p>
            <div className="flex items-start gap-2 p-3 rounded-lg bg-primary/5 border border-primary/10 mt-3">
              <Zap className="h-4 w-4 text-primary shrink-0 mt-0.5" />
              <p className="text-xs font-medium text-primary leading-relaxed">
                <span className="font-bold">Research Novelty:</span> {step.novelty}
              </p>
            </div>
          </div>
        </div>
      </div>
    </Card>
  )
}

function InputOutputFlow() {
  return (
    <Card className="p-5">
      <h3 className="text-base font-bold text-foreground mb-4 flex items-center gap-2">
        <ArrowRight className="h-4.5 w-4.5 text-primary" />
        DART Input → Process → Output
      </h3>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Input */}
        <div className="p-4 rounded-xl border-2 border-dashed border-amber-500/40 bg-amber-500/5 space-y-3">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-700 dark:text-amber-400 text-[10px] font-bold uppercase tracking-wider">
              Input
            </span>
            <AlertTriangle className="h-4 w-4 text-amber-500" />
          </div>

          <div className="space-y-2">
            <div className="p-2.5 rounded-lg bg-card border border-border">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1">
                Low-Confidence Requirement
              </p>
              <p className="text-xs text-foreground italic leading-relaxed">
                "The system should provide a good user experience when handling customer requests efficiently."
              </p>
              <div className="flex items-center gap-2 mt-2">
                <Badge tone="danger" className="text-[10px]">Confidence: 42%</Badge>
                <Badge tone="warning" className="text-[10px]">Below 60% Gate</Badge>
              </div>
            </div>

            <div className="p-2.5 rounded-lg bg-card border border-border">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1">
                Agent Reasoning Traces
              </p>
              <div className="space-y-1.5">
                <div className="flex justify-between text-[11px]">
                  <span className="text-foreground font-medium">Clarity Agent</span>
                  <span className="text-amber-600">38% conf.</span>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="text-foreground font-medium">Completeness Agent</span>
                  <span className="text-amber-600">45% conf.</span>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="text-foreground font-medium">Consistency Agent</span>
                  <span className="text-emerald-600">72% conf.</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Process Arrow */}
        <div className="flex flex-col items-center justify-center gap-3">
          <div className="hidden lg:flex flex-col items-center gap-2 w-full">
            <div className="flex items-center gap-1.5 w-full">
              <div className="flex-1 h-px bg-gradient-to-r from-amber-500/50 to-primary/50" />
              <Gavel className="h-5 w-5 text-primary" />
              <div className="flex-1 h-px bg-gradient-to-r from-primary/50 to-emerald-500/50" />
            </div>
            <div className="p-3 rounded-xl bg-primary/10 border border-primary/20 text-center w-full">
              <p className="text-xs font-bold text-primary uppercase tracking-wider">DART Protocol</p>
              <p className="text-[10px] text-primary/70 mt-0.5">5-Step Diagnostic Arbitration</p>
              <div className="flex items-center justify-center gap-1 mt-2">
                {PROTOCOL_STEPS.map((s, i) => {
                  const SI = s.icon
                  return (
                    <div key={s.key} className="flex items-center gap-1">
                      <SI className={`h-3 w-3 ${s.color}`} />
                      {i < PROTOCOL_STEPS.length - 1 && <span className="text-muted-foreground/40 text-[8px]">→</span>}
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
          <div className="flex lg:hidden items-center justify-center py-2">
            <ArrowDown className="h-6 w-6 text-primary animate-bounce" />
          </div>
        </div>

        {/* Output */}
        <div className="p-4 rounded-xl border-2 border-dashed border-emerald-500/40 bg-emerald-500/5 space-y-3">
          <div className="flex items-center gap-2">
            <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 text-[10px] font-bold uppercase tracking-wider">
              Output
            </span>
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          </div>

          <div className="space-y-2">
            <div className="p-2.5 rounded-lg bg-card border border-border">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1">
                Diagnostic Hypothesis
              </p>
              <Badge tone="primary" className="text-[10px] mb-1.5">AMBIGUOUS</Badge>
              <p className="text-xs text-foreground leading-relaxed">
                Vague terms "good user experience" and "efficiently" lack measurable criteria. Multiple interpretations detected.
              </p>
            </div>

            <div className="p-2.5 rounded-lg bg-card border border-border">
              <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1">
                Targeted Consultation Question
              </p>
              <p className="text-xs text-primary italic leading-relaxed">
                "Which interpretation does the evidence support? Define 'customer request' — is it a support ticket, API call, or UI action?"
              </p>
            </div>

            <div className="p-2.5 rounded-lg bg-card border border-emerald-500/30">
              <p className="text-[10px] font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-1">
                Actionable Feedback
              </p>
              <p className="text-xs text-foreground leading-relaxed">
                Replace "good user experience" with measurable criteria (e.g., "response time &lt; 2s, error rate &lt; 0.1%"). Define "customer request" as a specific entity. Split into separate requirements for UX and performance.
              </p>
              <div className="flex items-center gap-2 mt-2">
                <Badge tone="success" className="text-[10px]">RESOLVE</Badge>
                <span className="text-[10px] text-muted-foreground">78% agreement</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  )
}

function ComparisonTable() {
  return (
    <Card className="p-5">
      <h3 className="text-base font-bold text-foreground mb-1 flex items-center gap-2">
        <BarChart3 className="h-4.5 w-4.5 text-primary" />
        DART vs. Naive Majority Voting
      </h3>
      <p className="text-xs text-muted-foreground mb-4">
        Why reasoning-trace-level arbitration outperforms output-level voting in multi-agent systems
      </p>

      <div className="overflow-x-auto -mx-5 px-5">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="border-b border-border">
              <th className="py-2.5 px-3 text-left font-bold text-muted-foreground uppercase tracking-wider w-[140px]">
                Dimension
              </th>
              <th className="py-2.5 px-3 text-left font-bold text-destructive/70 uppercase tracking-wider">
                <div className="flex items-center gap-1.5">
                  <XCircle className="h-3.5 w-3.5" /> Majority Voting
                </div>
              </th>
              <th className="py-2.5 px-3 text-left font-bold text-primary uppercase tracking-wider">
                <div className="flex items-center gap-1.5">
                  <Gavel className="h-3.5 w-3.5" /> DART Protocol
                </div>
              </th>
              <th className="py-2.5 px-3 text-left font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider w-[180px]">
                <div className="flex items-center gap-1.5">
                  <Zap className="h-3.5 w-3.5" /> Advantage
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            {COMPARISON_ROWS.map((row, i) => (
              <tr
                key={row.dimension}
                className={`border-b border-border/50 ${i % 2 === 0 ? 'bg-muted/20' : ''}`}
              >
                <td className="py-3 px-3 font-semibold text-foreground">{row.dimension}</td>
                <td className="py-3 px-3 text-muted-foreground">{row.voting}</td>
                <td className="py-3 px-3 text-foreground font-medium">{row.dart}</td>
                <td className="py-3 px-3">
                  <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 text-[10px] font-semibold">
                    {row.advantage}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}

function CategoryShowcase() {
  const [expanded, setExpanded] = useState(null)

  return (
    <Card className="p-5">
      <h3 className="text-base font-bold text-foreground mb-1 flex items-center gap-2">
        <Tag className="h-4.5 w-4.5 text-primary" />
        Four Diagnostic Categories
      </h3>
      <p className="text-xs text-muted-foreground mb-4">
        Each category triggers a different targeted consultation question — not a generic retry
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {CATEGORY_INFO.map((cat) => {
          const CatIcon = cat.icon
          const isOpen = expanded === cat.key

          return (
            <button
              key={cat.key}
              type="button"
              onClick={() => setExpanded(isOpen ? null : cat.key)}
              className={`text-left p-4 rounded-xl border transition-all cursor-pointer ${
                isOpen ? 'border-primary/40 bg-primary/5 shadow-sm' : 'border-border hover:border-primary/20 hover:bg-muted/30'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <CatIcon className={`h-4 w-4 ${isOpen ? 'text-primary' : 'text-muted-foreground'}`} />
                  <Badge tone={cat.tone}>{cat.label}</Badge>
                </div>
                <ChevronDown
                  className={`h-4 w-4 text-muted-foreground transition-transform ${isOpen ? 'rotate-180' : ''}`}
                />
              </div>

              <p className="text-xs text-foreground mb-2">{cat.description}</p>

              {isOpen && (
                <div className="space-y-2 mt-3 animate-fade-rise">
                  <div className="p-2.5 rounded-lg bg-card border border-border">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-muted-foreground mb-1">
                      Example Requirement
                    </p>
                    <p className="text-xs text-foreground italic leading-relaxed">{cat.example}</p>
                  </div>
                  <div className="p-2.5 rounded-lg bg-primary/5 border border-primary/10">
                    <p className="text-[10px] font-bold uppercase tracking-wider text-primary mb-1">
                      Targeted Question (Not a Re-vote)
                    </p>
                    <p className="text-xs text-primary font-medium italic leading-relaxed">
                      "{cat.question}"
                    </p>
                  </div>
                </div>
              )}
            </button>
          )
        })}
      </div>
    </Card>
  )
}

function LiveCasesPanel() {
  const { data: dartData, isLoading } = useDartCases()
  const cases = mapDartCases(dartData?.cases || [])
  const team = useTeamPath()

  const openCount = cases.filter((c) => c.status === 'open').length
  const resolvedCount = cases.filter((c) => c.status === 'resolved').length

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-base font-bold text-foreground flex items-center gap-2">
            <ShieldCheck className="h-4.5 w-4.5 text-primary" />
            Live DART Cases
          </h3>
          <p className="text-xs text-muted-foreground">Real arbitration cases from your project — pulled live from the backend</p>
        </div>
        <div className="flex items-center gap-2">
          <Badge tone={openCount > 0 ? 'warning' : 'success'}>{openCount} Open</Badge>
          <Badge tone="neutral">{resolvedCount} Resolved</Badge>
        </div>
      </div>

      {isLoading ? (
        <div className="py-8 text-center">
          <p className="text-sm text-muted-foreground animate-pulse">Loading live DART cases...</p>
        </div>
      ) : cases.length === 0 ? (
        <div className="py-8 text-center space-y-3">
          <CheckCircle2 className="h-10 w-10 text-emerald-500 mx-auto" />
          <div>
            <p className="text-sm font-semibold text-foreground">No DART cases yet</p>
            <p className="text-xs text-muted-foreground mt-1">
              Submit a vague or low-quality requirement in the Quality Gate to trigger DART automatically.
            </p>
          </div>
          <Link
            to={team('/planning/requirements/srs-quality')}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-primary hover:underline"
          >
            Go to Quality Gate <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {cases.slice(0, 5).map((c) => (
            <div key={c.id} className="p-3.5 rounded-xl border border-border bg-muted/20 space-y-2.5">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-muted-foreground">{c.caseRef}</span>
                  <Badge tone={ARBITRATION_CATEGORY_TONE[c.category]}>{c.categoryLabel}</Badge>
                  <Badge tone={c.status === 'open' ? 'warning' : 'success'}>{c.statusLabel}</Badge>
                </div>
                <span className="text-[10px] text-muted-foreground">{c.confidenceAgreement}% agreement</span>
              </div>

              <p className="text-sm font-medium text-foreground">{c.title}</p>

              {c.consultation?.question && (
                <div className="p-2.5 rounded-lg bg-purple-500/10 border border-purple-500/20">
                  <p className="text-[10px] font-bold text-purple-600 dark:text-purple-400 uppercase tracking-wider mb-0.5">
                    Targeted Question
                  </p>
                  <p className="text-xs text-foreground italic">"{c.consultation.question}"</p>
                </div>
              )}

              {c.resolution?.actionableFeedback && (
                <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                  <p className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider mb-0.5">
                    Actionable Feedback
                  </p>
                  <p className="text-xs text-foreground leading-relaxed">{c.resolution.actionableFeedback}</p>
                </div>
              )}

              <div className="flex items-center gap-1.5 pt-1">
                {PROTOCOL_STEPS.map((s, i) => {
                  const SI = s.icon
                  return (
                    <div key={s.key} className="flex items-center gap-1">
                      <div className={`p-1 rounded ${s.bg} border`}>
                        <SI className={`h-3 w-3 ${s.color}`} />
                      </div>
                      {i < PROTOCOL_STEPS.length - 1 && (
                        <span className="text-muted-foreground/30 text-[8px]">→</span>
                      )}
                    </div>
                  )
                })}
                <span className="text-[10px] text-muted-foreground ml-auto">{c.stage} stage</span>
              </div>
            </div>
          ))}

          {cases.length > 5 && (
            <p className="text-xs text-muted-foreground text-center pt-1">
              + {cases.length - 5} more cases
            </p>
          )}
        </div>
      )}
    </Card>
  )
}

function BenefitsGrid() {
  const benefits = [
    {
      icon: Brain,
      title: 'Reasoning-Level Diagnosis',
      description: 'Operates on agent reasoning traces, not just output scores — preserving the full diagnostic context for targeted intervention.',
    },
    {
      icon: MessageCircleQuestion,
      title: 'Targeted Consultation',
      description: 'Formulates category-specific questions instead of re-asking the same question — the core novelty that avoids redundant computation.',
    },
    {
      icon: Sparkles,
      title: 'Actionable Student Feedback',
      description: 'Produces specific, evidence-based guidance ("replace vague term X with measurable criteria Y") instead of opaque scores.',
    },
    {
      icon: ShieldCheck,
      title: 'Bounded Convergence',
      description: 'Max 2 arbitration iterations, circuit breaker at 5 activations, configurable timeout — guaranteed termination.',
    },
    {
      icon: Scale,
      title: 'Human-in-the-Loop Escalation',
      description: 'NOVEL and unresolvable cases route to the instructor via ArbitrationOversight — DART never silently overwrites student work.',
    },
    {
      icon: Layers,
      title: 'Domain-Specific RAG',
      description: 'Consultation responses are augmented with IEEE 830 standards, requirement exemplars, and decomposition patterns from ChromaDB.',
    },
  ]

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {benefits.map((b) => {
        const BIcon = b.icon
        return (
          <Card key={b.title} className="p-4 card-hover-lift">
            <div className="flex items-center gap-2 mb-2">
              <div className="p-1.5 rounded-lg bg-primary/10">
                <BIcon className="h-4 w-4 text-primary" />
              </div>
              <h4 className="text-sm font-bold text-foreground">{b.title}</h4>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">{b.description}</p>
          </Card>
        )
      })}
    </div>
  )
}

export default function DartShowcase() {
  const [activeTab, setActiveTab] = useState('protocol')

  return (
    <div className="space-y-6 pb-12">
      <PageHeader
        title="DART — Diagnostic Arbitration using Reasoning Traces"
        breadcrumb={['Planning', 'DART Showcase']}
        description="Primary research novelty: a five-step diagnostic arbitration protocol that operates at the reasoning-trace level, not output-level voting."
      />

      {/* Hero / Thesis Statement */}
      <Card className="p-5 sm:p-6 border-primary/20 bg-gradient-to-br from-primary/5 via-card to-card">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
          <div className="space-y-3 max-w-2xl">
            <div className="flex items-center gap-2">
              <Gavel className="h-6 w-6 text-primary" />
              <h2 className="text-xl font-bold text-foreground tracking-tight">
                What is DART?
              </h2>
            </div>
            <p className="text-sm text-foreground/80 leading-relaxed">
              Existing multi-agent approaches resolve disagreements through <strong className="text-destructive">majority voting on final outputs</strong> — discarding the reasoning that led to each answer. DART instead collects <strong className="text-primary">structured reasoning traces</strong> from every agent, <strong className="text-primary">diagnoses the root cause</strong> of uncertainty, and sends a <strong className="text-primary">targeted consultation question</strong> — not the same question again.
            </p>
            <p className="text-sm text-foreground/80 leading-relaxed">
              This reasoning-trace-level arbitration produces <strong className="text-primary">actionable, specific feedback</strong> for students instead of opaque scores, while guaranteeing convergence through bounded iterations and instructor escalation.
            </p>
          </div>

          <div className="flex flex-col items-center gap-3 shrink-0">
            <div className="relative flex items-center justify-center" style={{ width: 110, height: 110 }}>
              <svg className="w-full h-full -rotate-90" viewBox="0 0 110 110">
                <circle cx="55" cy="55" r="46" className="stroke-muted" strokeWidth="8" fill="transparent" />
                <circle
                  cx="55" cy="55" r="46"
                  className="stroke-primary"
                  strokeWidth="8"
                  strokeDasharray={2 * Math.PI * 46}
                  strokeDashoffset={(2 * Math.PI * 46) * 0.2}
                  strokeLinecap="round"
                  fill="transparent"
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <Gavel className="h-5 w-5 text-primary mb-0.5" />
                <span className="text-[10px] font-bold text-primary uppercase tracking-wider">DART</span>
              </div>
            </div>
            <span className="text-xs font-semibold text-muted-foreground">5-Step Protocol</span>
          </div>
        </div>
      </Card>

      {/* Tabbed Content */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList className="h-10 bg-muted/60 p-1">
          <TabsTrigger value="protocol" className="text-xs gap-1.5">
            <Brain className="h-3.5 w-3.5" /> Protocol Flow
          </TabsTrigger>
          <TabsTrigger value="io" className="text-xs gap-1.5">
            <ArrowRight className="h-3.5 w-3.5" /> Input / Output
          </TabsTrigger>
          <TabsTrigger value="comparison" className="text-xs gap-1.5">
            <BarChart3 className="h-3.5 w-3.5" /> vs. Voting
          </TabsTrigger>
          <TabsTrigger value="categories" className="text-xs gap-1.5">
            <Tag className="h-3.5 w-3.5" /> Categories
          </TabsTrigger>
          <TabsTrigger value="live" className="text-xs gap-1.5">
            <Zap className="h-3.5 w-3.5" /> Live Cases
          </TabsTrigger>
        </TabsList>

        <TabsContent value="protocol" className="space-y-6">
          <AnimatedProtocolFlow />
          <BenefitsGrid />
        </TabsContent>

        <TabsContent value="io">
          <InputOutputFlow />
        </TabsContent>

        <TabsContent value="comparison">
          <ComparisonTable />
        </TabsContent>

        <TabsContent value="categories">
          <CategoryShowcase />
        </TabsContent>

        <TabsContent value="live">
          <LiveCasesPanel />
        </TabsContent>
      </Tabs>
    </div>
  )
}
