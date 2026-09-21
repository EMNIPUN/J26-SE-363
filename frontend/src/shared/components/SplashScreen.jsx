import { useState, useEffect } from 'react'
import MentorLogo from './MentorLogo.jsx'

const WORD_TOKENS = [
  { key: 'm', letter: 'M', rest: 'ulti-agent', isCore: true },
  { key: 'e', letter: 'E', rest: 'ngineering', isCore: true },
  { key: 'n', letter: 'N', rest: 'etwork', isCore: true },
  { key: 'for', letter: '', rest: 'for', isConnector: true },
  { key: 't', letter: 'T', rest: 'ask', isCore: true },
  { key: 'o', letter: 'O', rest: 'rchestration', isCore: true },
  { key: 'and', letter: '', rest: '&', isConnector: true },
  { key: 'r', letter: 'R', rest: 'eview', isCore: true },
]

export default function SplashScreen({ onComplete }) {
  // Animation phases:
  // 'expanded'  -> full "Multi-agent Engineering Network for Task Orchestration & Review" with generous spacing
  // 'shortening'-> suffixes fold inward
  // 'revealed'  -> acronym "MENTOR" settles with neural logo pulse and subtitle
  // 'exiting'   -> fade out overlay
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

    // Hold expanded title so user can read full name clearly (950ms)
    const t1 = setTimeout(() => {
      setPhase('shortening')
    }, 950)

    // Letters unite into MENTOR (1600ms)
    const t2 = setTimeout(() => {
      setPhase('revealed')
    }, 1600)

    // Fade out splash screen (2200ms)
    const t3 = setTimeout(() => {
      setPhase('exiting')
    }, 2200)

    // Complete and unmount (2550ms)
    const t4 = setTimeout(() => {
      setVisible(false)
      if (onComplete) onComplete()
    }, 2550)

    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)
      clearTimeout(t4)
    }
  }, [visible, onComplete])

  if (!visible) return null

  const isShortened = phase === 'shortening' || phase === 'revealed' || phase === 'exiting'

  return (
    <div
      onClick={() => {
        setVisible(false)
        if (onComplete) onComplete()
      }}
      className={`fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-background text-foreground select-none transition-all duration-350 ease-[cubic-bezier(0.16,1,0.3,1)] ${
        phase === 'exiting' ? 'opacity-0 scale-105 pointer-events-none' : 'opacity-100'
      }`}
    >
      <div className="flex flex-col items-center justify-center max-w-4xl px-6 text-center">
        {/* Animated Brand Logo */}
        <div
          className={`transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] mb-6 ${
            phase === 'expanded' ? 'scale-90 opacity-90' : 'scale-110 opacity-100'
          }`}
        >
          <div className="relative flex items-center justify-center p-3.5 rounded-2xl bg-card border border-border shadow-2xl">
            <MentorLogo size={56} />
            {phase === 'revealed' && (
              <span className="absolute -top-1 -right-1 flex h-3.5 w-3.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
                <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-primary" />
              </span>
            )}
          </div>
        </div>

        {/* Dynamic Expanding & Shortening Name with Pristine Typography & Word Spacing */}
        <div className="flex flex-wrap items-center justify-center text-xl sm:text-2xl md:text-3xl lg:text-4xl font-extrabold tracking-normal leading-tight">
          {WORD_TOKENS.map((token) => {
            if (token.isConnector) {
              return (
                <span
                  key={token.key}
                  className={`inline-block text-muted-foreground font-medium text-base sm:text-xl transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] ${
                    isShortened
                      ? 'max-w-0 opacity-0 scale-75 -mx-0 overflow-hidden'
                      : 'max-w-[48px] opacity-75 mx-2 sm:mx-3 scale-100'
                  }`}
                >
                  {token.rest}
                </span>
              )
            }

            return (
              <span
                key={token.key}
                className={`inline-flex items-baseline whitespace-nowrap transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] ${
                  isShortened ? 'mx-0.5 sm:mx-1' : 'mx-2 sm:mx-3'
                }`}
              >
                {/* Capital Acronym Initial (M, E, N, T, O, R) */}
                <span
                  className={`font-black text-2xl sm:text-3xl md:text-4xl lg:text-5xl transition-colors duration-300 ${
                    isShortened
                      ? 'text-foreground'
                      : 'text-primary'
                  }`}
                >
                  {token.letter}
                </span>

                {/* Suffix Letters (ulti-agent, ngineering, etc.) */}
                <span
                  className={`overflow-hidden inline-block align-baseline whitespace-nowrap font-bold text-foreground/90 transition-all duration-600 ease-[cubic-bezier(0.16,1,0.3,1)] ${
                    isShortened
                      ? 'max-w-0 opacity-0 -translate-x-3'
                      : 'max-w-[200px] opacity-90 translate-x-0 pl-0.5'
                  }`}
                >
                  {token.rest}
                </span>
              </span>
            )
          })}
        </div>

        {/* Subtitle & Engine Status (Fades in smoothly once acronym unites) */}
        <div
          className={`transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] mt-4 ${
            phase === 'revealed' || phase === 'exiting'
              ? 'opacity-100 translate-y-0'
              : 'opacity-0 translate-y-3 pointer-events-none'
          }`}
        >
          <p className="text-xs sm:text-sm text-muted-foreground font-medium tracking-wide">
            Multi-Agent Engineering Network for Task Orchestration &amp; Review
          </p>
          <div className="flex items-center justify-center gap-1.5 mt-2.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-[11px] text-muted-foreground/80 font-mono">
              AI Orchestration Core Active
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
