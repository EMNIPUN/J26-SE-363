import { useState, useEffect } from 'react'
import MentorLogo from './MentorLogo.jsx'
import { Sparkles } from 'lucide-react'

const TARGET_WORD = ['M', 'E', 'N', 'T', 'O', 'R']
const GLYPHS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

function FlippingMentor({ isComplete }) {
  const [lockedIndex, setLockedIndex] = useState(0)
  const [currentChars, setCurrentChars] = useState(() =>
    TARGET_WORD.map(() => GLYPHS[Math.floor(Math.random() * GLYPHS.length)])
  )

  useEffect(() => {
    if (isComplete) return

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
  }, [isComplete])

  const effectiveLockedIndex = isComplete ? TARGET_WORD.length : lockedIndex
  const effectiveChars = isComplete ? TARGET_WORD : currentChars

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
                  ? 'text-foreground font-black animate-letter-flip'
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

export default function SplashScreen({ onComplete }) {
  // Animation lifecycle:
  // 1. 'buffering' (0ms - 1350ms) : Logo border beam buffers; letters flip & sequentially lock into MENTOR
  // 2. 'ready'     (1350ms - 1850ms): All letters locked, buffering locks into solid glow, AI badge sparkles
  // 3. 'exiting'   (1850ms - 2200ms): Fluid dissolve into dashboard
  const [phase, setPhase] = useState('buffering')
  const [visible, setVisible] = useState(() => {
    if (typeof window === 'undefined') return false
    return !window.matchMedia('(prefers-reduced-motion: reduce)').matches
  })

  useEffect(() => {
    if (!visible) {
      if (onComplete) onComplete()
      return
    }

    const t1 = setTimeout(() => setPhase('ready'), 1350)
    const t2 = setTimeout(() => setPhase('exiting'), 1850)
    const t3 = setTimeout(() => {
      setVisible(false)
      if (onComplete) onComplete()
    }, 2200)

    const handleKeyDown = () => {
      setVisible(false)
      if (onComplete) onComplete()
    }
    window.addEventListener('keydown', handleKeyDown, { once: true })

    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [visible, onComplete])

  if (!visible) return null

  const isReady = phase === 'ready' || phase === 'exiting'

  return (
    <div
      onClick={() => {
        setVisible(false)
        if (onComplete) onComplete()
      }}
      className={`fixed inset-0 z-[9999] flex flex-col items-center justify-center bg-background text-foreground select-none cursor-pointer transition-all duration-350 ease-[cubic-bezier(0.16,1,0.3,1)] ${
        phase === 'exiting' ? 'opacity-0 scale-105 pointer-events-none' : 'opacity-100'
      }`}
      aria-label="MENTOR AI Splash Screen - Click anywhere to skip"
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
                    isReady ? 'bg-blue-500' : 'bg-primary'
                  }`}
                />
                <span
                  className={`relative inline-flex rounded-full h-3.5 w-3.5 ${
                    isReady ? 'bg-blue-500' : 'bg-primary'
                  }`}
                />
              </span>
            </div>
          </div>
        </div>

        {/* ANIMATED "MENTOR" WITH "AI" */}
        <div className="flex items-center justify-center gap-2.5 sm:gap-3.5">
          <h1 className="text-4xl sm:text-5xl font-black text-foreground">
            <FlippingMentor isComplete={isReady} />
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
