import { useState, useEffect } from 'react'
import MentorLogo from './MentorLogo.jsx'

const WORD_TOKENS = [
  { key: 'm', letter: 'M', rest: 'ulti-agent' },
  { key: 'e', letter: 'E', rest: 'ngineering' },
  { key: 'n', letter: 'N', rest: 'etwork' },
  { key: 'for', isConnector: true, text: 'for' },
  { key: 't', letter: 'T', rest: 'ask' },
  { key: 'o', letter: 'O', rest: 'rchestration' },
  { key: 'and', isConnector: true, text: '&' },
  { key: 'r', letter: 'R', rest: 'eview' },
]

export default function SplashScreen({ onComplete }) {
  // Animation lifecycle:
  // 1. 'expanded'   (0ms - 950ms)   : Full single-line title with highlighted initial letters (same size as rest)
  // 2. 'gathering'  (950ms - 1700ms): Suffixes dissolve while initial letters travel inward & grow into bold MENTOR
  // 3. 'revealed'   (1700ms - 2350ms): Settled large MENTOR wordmark with neural logo ping & subtitle
  // 4. 'exiting'    (2350ms - 2700ms): Soft fade/scale dissolve into app
  const [phase, setPhase] = useState('expanded')
  const [visible, setVisible] = useState(() => {
    if (typeof window === 'undefined') return false
    return !window.matchMedia('(prefers-reduced-motion: reduce)').matches
  })

  useEffect(() => {
    if (!visible) {
      if (onComplete) onComplete()
      return
    }

    const t1 = setTimeout(() => setPhase('gathering'), 950)
    const t2 = setTimeout(() => setPhase('revealed'), 1700)
    const t3 = setTimeout(() => setPhase('exiting'), 2350)
    const t4 = setTimeout(() => {
      setVisible(false)
      if (onComplete) onComplete()
    }, 2700)

    const handleKeyDown = () => {
      setVisible(false)
      if (onComplete) onComplete()
    }
    window.addEventListener('keydown', handleKeyDown, { once: true })

    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)
      clearTimeout(t4)
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [visible, onComplete])

  if (!visible) return null

  const isGathered = phase === 'gathering' || phase === 'revealed' || phase === 'exiting'
  const isRevealed = phase === 'revealed' || phase === 'exiting'

  return (
    <div
      onClick={() => {
        setVisible(false)
        if (onComplete) onComplete()
      }}
      className={`fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-background text-foreground select-none cursor-pointer transition-all duration-350 ease-[cubic-bezier(0.16,1,0.3,1)] ${
        phase === 'exiting' ? 'opacity-0 scale-105 pointer-events-none' : 'opacity-100'
      }`}
      aria-label="MENTOR Splash Screen - Click anywhere to skip"
    >
      {/* Subtle ambient gradient spotlight */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,var(--primary)/0.08_0%,transparent_65%)] pointer-events-none" />

      <div className="relative z-10 flex flex-col items-center justify-center w-full max-w-5xl px-3 sm:px-6 text-center">
        {/* Mentor Neural Logo Mark */}
        <div
          className={`transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] mb-6 sm:mb-8 ${
            phase === 'expanded' ? 'scale-90 opacity-90' : 'scale-105 opacity-100'
          }`}
        >
          <div className="relative flex items-center justify-center p-3.5 sm:p-4 rounded-2xl bg-card/90 backdrop-blur-md border border-border shadow-2xl">
            <MentorLogo size={52} />
            {isRevealed && (
              <span className="absolute -top-1 -right-1 flex h-3.5 w-3.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75" />
                <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-emerald-500" />
              </span>
            )}
          </div>
        </div>

        {/* Central Single-Line Dynamic Stage */}
        <div className="relative flex items-center justify-center w-full min-h-[70px] sm:min-h-[95px] md:min-h-[110px] overflow-visible">
          <div className="flex items-center justify-center whitespace-nowrap flex-nowrap overflow-visible select-none text-[clamp(0.68rem,1.75vw,1.35rem)] tracking-tight">
            {WORD_TOKENS.map((token) => {
              if (token.isConnector) {
                return (
                  <span
                    key={token.key}
                    className={`overflow-hidden inline-block align-baseline whitespace-nowrap text-muted-foreground/75 font-normal transition-all duration-600 ease-[cubic-bezier(0.16,1,0.3,1)] ${
                      isGathered
                        ? 'max-w-0 opacity-0 scale-0 -mx-1 pointer-events-none'
                        : 'max-w-[60px] opacity-80 scale-100 mx-1 sm:mx-1.5 md:mx-2'
                    }`}
                  >
                    {token.text}
                  </span>
                )
              }

              return (
                <span
                  key={token.key}
                  className={`inline-flex items-center whitespace-nowrap transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] ${
                    isGathered
                      ? 'mx-1.5 sm:mx-3 md:mx-4.5'
                      : 'mr-1.5 sm:mr-2.5 md:mr-3.5'
                  }`}
                >
                  {/* The Acronym Initial Letter (M, E, N, T, O, R) */}
                  <span
                    className={`inline-block font-black origin-center transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)] ${
                      isGathered
                        ? 'scale-[1.85] sm:scale-[2.4] md:scale-[2.9] text-foreground drop-shadow-sm'
                        : 'scale-100 text-primary'
                    }`}
                  >
                    {token.letter}
                  </span>

                  {/* Suffix Letters (same size, collapses smoothly to 0 width) */}
                  <span
                    className={`overflow-hidden inline-block align-baseline whitespace-nowrap font-medium text-foreground/85 transition-all duration-600 ease-[cubic-bezier(0.16,1,0.3,1)] ${
                      isGathered
                        ? 'max-w-0 opacity-0 -translate-x-2 pointer-events-none'
                        : 'max-w-[400px] opacity-100 translate-x-0'
                    }`}
                  >
                    {token.rest}
                  </span>
                </span>
              )
            })}
          </div>
        </div>

        {/* Subtitle & Engine Status (Fades in once letters assemble into MENTOR) */}
        <div
          className={`transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] mt-5 sm:mt-7 ${
            isRevealed
              ? 'opacity-100 translate-y-0'
              : 'opacity-0 translate-y-2 pointer-events-none'
          }`}
        >
          <p className="text-xs sm:text-sm text-muted-foreground font-medium tracking-wide">
            Multi-Agent Engineering Network for Task Orchestration &amp; Review
          </p>
          <div className="inline-flex items-center justify-center gap-2 mt-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[11px] text-emerald-600 dark:text-emerald-400 font-mono font-medium">
              AI Orchestration Core Active
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
