import { useState, useEffect } from 'react'
import PropTypes from 'prop-types'
import MentorLogo from './MentorLogo.jsx'
import { Sparkles } from 'lucide-react'

const TARGET_WORD = ['M', 'E', 'N', 'T', 'O', 'R']
const GLYPHS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

function FlippingMentor({ isComplete, isStatic = false }) {
  const [lockedIndex, setLockedIndex] = useState(0)
  const [currentChars, setCurrentChars] = useState(() =>
    TARGET_WORD.map(() => GLYPHS[Math.floor(Math.random() * GLYPHS.length)])
  )

  useEffect(() => {
    if (isComplete || isStatic) return

    const startDelay = 220
    const stepDuration = 160
    const startTime = Date.now()

    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime
      const nextLocked = Math.min(
        TARGET_WORD.length,
        Math.max(0, Math.floor((elapsed - startDelay) / stepDuration) + 1)
      )

      setLockedIndex(nextLocked)

      setCurrentChars(() =>
        TARGET_WORD.map((targetChar, idx) => {
          if (idx < nextLocked) return targetChar
          return GLYPHS[Math.floor(Math.random() * GLYPHS.length)]
        })
      )

      if (nextLocked >= TARGET_WORD.length) {
        clearInterval(interval)
      }
    }, 40)

    return () => clearInterval(interval)
  }, [isComplete, isStatic])

  const effectiveLockedIndex = isComplete || isStatic ? TARGET_WORD.length : lockedIndex
  const effectiveChars = isComplete || isStatic ? TARGET_WORD : currentChars

  return (
    <div className="inline-flex items-center justify-center tracking-[0.16em] sm:tracking-[0.22em] select-none pl-[0.16em] sm:pl-[0.22em]">
      {TARGET_WORD.map((finalChar, idx) => {
        const isLocked = idx < effectiveLockedIndex
        const char = isLocked ? finalChar : (effectiveChars[idx] || finalChar)

        return (
          <span
            key={idx}
            className="inline-flex items-center justify-center w-[0.82em] sm:w-[0.88em] text-center"
          >
            <span
              key={`${idx}-${isLocked ? 'locked' : 'flipping'}`}
              className={`inline-block select-none transition-colors duration-150 ${
                isLocked
                  ? isStatic
                    ? 'text-foreground font-black'
                    : 'text-foreground font-black animate-letter-flip'
                  : 'text-primary/70 font-mono font-bold animate-letter-tumbling'
              }`}
            >
              {char}
            </span>
          </span>
        )
      })}
    </div>
  )
}

FlippingMentor.propTypes = {
  isComplete: PropTypes.bool.isRequired,
  isStatic: PropTypes.bool,
}

export default function SplashScreen({ isBuffering = false, onComplete }) {
  // Check if user already saw the full tumbling intro animation in this session
  const [hasSeenIntro] = useState(() => {
    if (typeof window === 'undefined') return true
    try {
      return Boolean(sessionStorage.getItem('mentor_splash_seen'))
    } catch {
      return false
    }
  })

  // Reduced motion preference
  const prefersReducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches

  // If already seen intro or reduced motion, skip character tumbling
  const isStatic = hasSeenIntro || prefersReducedMotion

  // Visible whenever isBuffering is true, or during the initial intro animation
  const [visible, setVisible] = useState(() => {
    if (typeof window === 'undefined') return false
    if (isStatic && !isBuffering) return false
    return true
  })

  // phase: 'buffering' | 'ready' | 'exiting'
  const [phase, setPhase] = useState(() => (isStatic ? 'ready' : 'buffering'))
  const [introFinished, setIntroFinished] = useState(isStatic)

  // Handle intro animation timing for first load
  useEffect(() => {
    if (isStatic) {
      setIntroFinished(true)
      return
    }

    const t1 = setTimeout(() => setPhase('ready'), 1350)
    const t2 = setTimeout(() => {
      try {
        sessionStorage.setItem('mentor_splash_seen', 'true')
      } catch {
        // ignore storage errors
      }
      setIntroFinished(true)
    }, 1850)

    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
    }
  }, [isStatic])

  // Dismiss splash screen once intro finished AND not buffering
  useEffect(() => {
    if (!visible) return

    if (introFinished && !isBuffering) {
      setPhase('exiting')
      const tExit = setTimeout(() => {
        setVisible(false)
        if (onComplete) onComplete()
      }, 350)
      return () => clearTimeout(tExit)
    }
  }, [introFinished, isBuffering, visible, onComplete])

  // Safety fallback: ensure splash screen dissolves eventually (max 8s) even on stuck network
  useEffect(() => {
    if (!visible) return
    const fallbackTimer = setTimeout(() => {
      setPhase('exiting')
      setTimeout(() => {
        setVisible(false)
        if (onComplete) onComplete()
      }, 350)
    }, 8000)
    return () => clearTimeout(fallbackTimer)
  }, [visible, onComplete])

  // Allow manual skip on click or keydown if not actively buffering
  useEffect(() => {
    if (!visible) return

    const handleKeyDown = () => {
      if (isBuffering) return
      try {
        sessionStorage.setItem('mentor_splash_seen', 'true')
      } catch {
        // ignore storage errors
      }
      setPhase('exiting')
      setTimeout(() => {
        setVisible(false)
        if (onComplete) onComplete()
      }, 350)
    }

    window.addEventListener('keydown', handleKeyDown, { once: true })
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [visible, isBuffering, onComplete])

  if (!visible) return null

  const isReady = phase === 'ready' || phase === 'exiting'

  return (
    <div
      onClick={() => {
        if (isBuffering) return
        try {
          sessionStorage.setItem('mentor_splash_seen', 'true')
        } catch {
          // ignore storage errors
        }
        setPhase('exiting')
        setTimeout(() => {
          setVisible(false)
          if (onComplete) onComplete()
        }, 350)
      }}
      className={`fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-background text-foreground select-none cursor-pointer transition-all duration-350 ease-[cubic-bezier(0.16,1,0.3,1)] ${
        phase === 'exiting' ? 'opacity-0 scale-105 pointer-events-none' : 'opacity-100'
      }`}
      aria-label="MENTOR AI Splash Screen"
    >
      {/* Ambient background glow */}
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,var(--primary)/0.07_0%,transparent_65%)] pointer-events-none" />

      <div className="relative z-10 flex flex-col items-center justify-center max-w-md px-6 text-center">
        {/* LOGO CONTAINER WITH ACTIVE BUFFERING BORDER */}
        <div className="relative mb-7 flex items-center justify-center">
          {/* Subtle outer radar ring pulse */}
          <div className="absolute -inset-4 rounded-3xl border border-primary/20 animate-ping [animation-duration:3s] pointer-events-none opacity-30" />

          {/* Dashed orbital buffering ring */}
          <div className="absolute -inset-2.5 rounded-2xl border border-dashed border-primary/25 animate-[spin_10s_linear_infinite] pointer-events-none" />

          {/* Border Beam Buffering Container */}
          <div className="relative p-[2px] rounded-2xl overflow-hidden shadow-2xl">
            {/* High-speed rotating conic gradient simulating border buffering */}
            <div
              className={`absolute -inset-[150%] pointer-events-none transition-opacity duration-500 ${
                isReady
                  ? 'opacity-0'
                  : 'opacity-100 animate-[spin_2s_linear_infinite]'
              }`}
              style={{
                background:
                  'conic-gradient(from 0deg at 50% 50%, transparent 0deg, transparent 240deg, var(--foreground) 320deg, transparent 360deg)',
              }}
            />

            {/* When ready, solid luminous border */}
            <div
              className={`absolute inset-0 rounded-2xl transition-opacity duration-500 border-2 ${
                isReady
                  ? 'border-blue-500/80 opacity-100 shadow-[0_0_16px_rgba(59,130,246,0.35)]'
                  : 'opacity-0'
              }`}
            />

            {/* Inner Card Frame */}
            <div className="relative z-10 p-5 rounded-[14px] bg-card/95 backdrop-blur-xl border border-border/60 flex items-center justify-center">
              <MentorLogo size={58} />

              {/* Status indicator pip on logo */}
              <span className="absolute -top-1 -right-1 flex h-3.5 w-3.5">
                <span
                  className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                    isBuffering ? 'bg-primary' : isReady ? 'bg-blue-500' : 'bg-primary'
                  }`}
                />
                <span
                  className={`relative inline-flex rounded-full h-3.5 w-3.5 ${
                    isBuffering ? 'bg-primary' : isReady ? 'bg-blue-500' : 'bg-primary'
                  }`}
                />
              </span>
            </div>
          </div>
        </div>

        {/* ANIMATED "MENTOR" WITH "AI" */}
        <div className="flex items-center justify-center gap-2.5 sm:gap-3.5">
          <h1 className="text-4xl sm:text-5xl font-black text-foreground">
            <FlippingMentor isComplete={isReady} isStatic={isStatic} />
          </h1>

          {/* Animated AI Badge */}
          <div
            className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border font-black text-xs sm:text-sm tracking-wider uppercase shadow-xs transition-all duration-500 ${
              isReady
                ? 'bg-primary/15 border-primary/40 text-primary scale-105 opacity-100'
                : 'bg-primary/10 border-primary/20 text-primary opacity-60'
            }`}
          >
            <Sparkles className={`w-3.5 h-3.5 ${isReady ? 'animate-pulse text-primary' : 'text-primary'}`} />
            <span>AI</span>
          </div>
        </div>
      </div>
    </div>
  )
}

SplashScreen.propTypes = {
  isBuffering: PropTypes.bool,
  onComplete: PropTypes.func,
}
