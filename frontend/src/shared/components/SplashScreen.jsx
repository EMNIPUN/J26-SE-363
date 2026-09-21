import { useState, useEffect } from 'react'
import MentorLogo from './MentorLogo.jsx'
import { Sparkles } from 'lucide-react'

export default function SplashScreen({ onComplete }) {
  // Animation lifecycle:
  // 1. 'buffering' (0ms - 1350ms) : Logo border beam actively buffers; MENTOR + AI badge shine
  // 2. 'ready'     (1350ms - 1850ms): Buffering locks into solid active glow
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
                  ? 'border-emerald-500/80 opacity-100 shadow-[0_0_16px_rgba(16,185,129,0.35)]'
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
                    isReady ? 'bg-emerald-500' : 'bg-primary'
                  }`}
                />
                <span
                  className={`relative inline-flex rounded-full h-3.5 w-3.5 ${
                    isReady ? 'bg-emerald-500' : 'bg-primary'
                  }`}
                />
              </span>
            </div>
          </div>
        </div>

        {/* ANIMATED "MENTOR" WITH "AI" */}
        <div className="flex items-center justify-center gap-2.5 sm:gap-3.5">
          <h1 className="text-4xl sm:text-5xl font-black tracking-[0.22em] text-foreground pl-[0.22em] transition-all duration-700">
            MENTOR
          </h1>

          {/* Glowing Animated AI Badge */}
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-primary/10 border border-primary/30 text-primary font-black text-xs sm:text-sm tracking-wider uppercase shadow-xs transition-all duration-500 hover:scale-105">
            <Sparkles className="w-3.5 h-3.5 animate-pulse text-primary" />
            <span>AI</span>
          </div>
        </div>
      </div>
    </div>
  )
}
